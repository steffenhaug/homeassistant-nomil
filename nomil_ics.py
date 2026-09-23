#!/usr/bin/env python3
"""Generate an iCalendar (.ics) feed of NOMIL waste collection dates.

NOMIL (Nordfjord Miljøverk IKS) has no public calendar export. Its "Tømmeplan"
app talks to a Norconsult Digital backend; this script uses that same API.

Examples
--------
  # Find your property id from an address:
  python3 nomil_ics.py --search "Sjøgata 103"

  # Write an .ics for an address (auto-resolves the property):
  python3 nomil_ics.py --address "Sjøgata 103" --out nomil.ics

  # Or for a known property id:
  python3 nomil_ics.py --id 368ad825-6fc6-4bc5-aa6e-de88b59c00c6 --out nomil.ics

No third-party dependencies (standard library only).
"""
import argparse
import datetime
import json
import sys
import urllib.parse
import urllib.request
from html import unescape

API_BASE = "https://tommeplan.nomil.no:9000/api/"
APPLIKASJONS_ID = "380b0118-95ba-4c57-b53c-2f79c3922d65"
OPPDRAGSGIVER_ID = "100"
# Honest, self-identifying User-Agent. Clearly marked unofficial so it is not
# impersonating the real app. Add a contact if you like, e.g.
#   "nomil-ha/1.0 (unofficial NoMil Tommeplan client; +https://github.com/you/nomil)"
USER_AGENT = "nomil-ha/1.0 (unofficial NoMil Tommeplan client for Home Assistant)"


def login() -> str:
    body = json.dumps(
        {"applikasjonsId": APPLIKASJONS_ID, "oppdragsgiverId": OPPDRAGSGIVER_ID}
    ).encode()
    req = urllib.request.Request(
        API_BASE + "login",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        token = resp.headers.get("Token")
    if not token:
        sys.exit("Login failed: no Token header returned.")
    return token


def api_get(token: str, path: str, **params) -> list:
    url = API_BASE + path + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url, headers={"Token": token, "User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def search(token: str, address: str) -> list:
    return api_get(token, "eiendommer", adresse=address)


def resolve_id(token: str, address: str, kommune: str | None) -> str:
    props = search(token, address)
    if kommune:
        props = [p for p in props if (p.get("kommune") or "").lower() == kommune.lower()]
    exact = [p for p in props if (p.get("adresse") or "").lower() == address.lower()]
    chosen = exact or props
    if not chosen:
        sys.exit(f"No property found for address {address!r}.")
    if len(chosen) > 1:
        sys.stderr.write(
            "Multiple properties matched; using the first. Candidates:\n"
        )
        for p in chosen:
            sys.stderr.write(f"  {p['id']}  {p.get('adresse','')}, {p.get('kommune','')}\n")
    return chosen[0]["id"]


def fetch_pickups(token: str, eiendom_id: str, days_back: int, days_ahead: int) -> list:
    today = datetime.date.today()
    return api_get(
        token,
        "tomminger",
        eiendomId=eiendom_id,
        datoFra=(today - datetime.timedelta(days=days_back)).isoformat(),
        datoTil=(today + datetime.timedelta(days=days_ahead)).isoformat(),
    )


def build_ics(pickups: list, cal_name: str) -> str:
    # Group fractions collected on the same day into one all-day event.
    by_day: dict[str, list[str]] = {}
    for item in pickups:
        day = (item.get("dato") or "")[:10]
        if not day:
            continue
        frac = unescape((item.get("fraksjon") or "Avfall").strip())
        by_day.setdefault(day, [])
        if frac not in by_day[day]:
            by_day[day].append(frac)

    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    def esc(text: str) -> str:
        return text.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//nomil-ics//NO",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{esc(cal_name)}",
    ]
    for day in sorted(by_day):
        d = day.replace("-", "")
        nxt = (datetime.date.fromisoformat(day) + datetime.timedelta(days=1)).strftime("%Y%m%d")
        fractions = ", ".join(sorted(by_day[day]))
        lines += [
            "BEGIN:VEVENT",
            f"UID:{d}-nomil@tommeplan.nomil.no",
            f"DTSTAMP:{stamp}",
            f"DTSTART;VALUE=DATE:{d}",
            f"DTEND;VALUE=DATE:{nxt}",
            f"SUMMARY:{esc(fractions)}",
            "TRANSP:TRANSPARENT",
            "BEGIN:VALARM",
            "TRIGGER:-P1D",
            "ACTION:DISPLAY",
            f"DESCRIPTION:{esc(fractions)}",
            "END:VALARM",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--address", help="Street address, e.g. 'Sjøgata 103'")
    g.add_argument("--id", help="Property (eiendom) GUID")
    g.add_argument("--search", metavar="ADDRESS",
                   help="List matching properties and their ids, then exit")
    ap.add_argument("--kommune", help="Disambiguate by municipality, e.g. 'Stad'")
    ap.add_argument("--out", default="-", help="Output .ics path (default: stdout)")
    ap.add_argument("--name", default="NOMIL tømmekalender", help="Calendar name")
    ap.add_argument("--days-back", type=int, default=14)
    ap.add_argument("--days-ahead", type=int, default=180)
    args = ap.parse_args()

    token = login()

    if args.search:
        for p in search(token, args.search):
            print(f"{p['id']}  {p.get('adresse','')}, {p.get('kommune','')}")
        return

    eiendom_id = args.id or resolve_id(token, args.address, args.kommune)
    pickups = fetch_pickups(token, eiendom_id, args.days_back, args.days_ahead)
    ics = build_ics(pickups, args.name)

    if args.out == "-":
        sys.stdout.write(ics)
    else:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(ics)
        sys.stderr.write(f"Wrote {len(pickups)} pickups to {args.out}\n")


if __name__ == "__main__":
    main()
