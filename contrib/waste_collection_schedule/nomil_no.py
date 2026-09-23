import datetime
from html import unescape

import requests
from waste_collection_schedule import Collection  # type: ignore[attr-defined]
from waste_collection_schedule.exceptions import (
    SourceArgumentNotFoundWithSuggestions,
    SourceArgumentRequired,
)

TITLE = "NOMIL (Nordfjord Miljøverk)"
DESCRIPTION = (
    "Source for NOMIL / Nordfjord Miljøverk IKS waste collection, "
    "covering Bremanger, Kinn, Stad, Gloppen and Stryn (Norway)."
)
URL = "https://www.nomil.no/"
COUNTRY = "no"

TEST_CASES = {
    "Address in Stad": {"address": "Sjøgata 103"},
    "Address + kommune": {"address": "Eidsgata 1", "kommune": "Stad"},
    "Property id directly": {"id": "368ad825-6fc6-4bc5-aa6e-de88b59c00c6"},
}

# The NOMIL "Tømmeplan" app talks to this Norconsult Digital backend. The
# application id and oppdragsgiver (client) id are baked into the app and are
# the same for every NOMIL user; they are not personal credentials.
API_BASE = "https://tommeplan.nomil.no:9000/api/"
APPLIKASJONS_ID = "380b0118-95ba-4c57-b53c-2f79c3922d65"
OPPDRAGSGIVER_ID = "100"

# Honest, self-identifying User-Agent: clearly marked unofficial so it is not
# impersonating the real app. Add a contact (repo URL) if you publish one.
USER_AGENT = "nomil-ha/1.0 (unofficial NoMil Tommeplan client for Home Assistant)"

# Fraction name (as returned by the API) -> Material Design Icon.
ICON_MAP = {
    "Restavfall": "mdi:trash-can",
    "Våtorganisk avfall": "mdi:leaf",
    "Matavfall": "mdi:food-apple",
    "Papir og Plastemballasje": "mdi:recycle",
    "Papir": "mdi:package-variant",
    "Papp og papir": "mdi:package-variant",
    "Plastemballasje": "mdi:recycle-variant",
    "Glass og metallemballasje": "mdi:bottle-soda",
    "Glass- og metallemballasje": "mdi:bottle-soda",
    "Hageavfall": "mdi:flower",
    "Juletre": "mdi:pine-tree",
}


class Source:
    def __init__(self, address: str | None = None, kommune: str | None = None,
                 id: str | None = None):
        self._address = address.strip() if address else None
        self._kommune = kommune.strip().lower() if kommune else None
        self._id = id.strip() if id else None
        if not self._address and not self._id:
            raise SourceArgumentRequired(
                "address",
                "Provide either an 'address' (e.g. 'Sjøgata 103') or a "
                "property 'id' (the eiendom GUID).",
            )

    def _session(self) -> requests.Session:
        s = requests.Session()
        s.headers.update({"User-Agent": USER_AGENT})
        r = s.post(
            API_BASE + "login",
            json={
                "applikasjonsId": APPLIKASJONS_ID,
                "oppdragsgiverId": OPPDRAGSGIVER_ID,
            },
            timeout=30,
        )
        r.raise_for_status()
        token = r.headers.get("Token")
        if not token:
            raise RuntimeError("NOMIL login did not return a Token header")
        s.headers.update({"Token": token})
        return s

    def _resolve_id(self, s: requests.Session) -> str:
        r = s.get(API_BASE + "eiendommer",
                  params={"adresse": self._address}, timeout=30)
        r.raise_for_status()
        props = r.json()
        if self._kommune:
            props = [p for p in props
                     if (p.get("kommune") or "").lower() == self._kommune]
        # Prefer an exact (case-insensitive) address match when the user gave a
        # house number; otherwise fall back to the first hit.
        wanted = self._address.lower()
        exact = [p for p in props
                 if (p.get("adresse") or "").lower() == wanted]
        chosen = exact or props
        if not chosen:
            suggestions = self._suggest(s)
            raise SourceArgumentNotFoundWithSuggestions(
                "address", self._address, suggestions)
        return chosen[0]["id"]

    def _suggest(self, s: requests.Session) -> list[str]:
        # Search on just the street part to offer nearby matches.
        street = self._address.rsplit(" ", 1)[0] if self._address else ""
        if not street:
            return []
        try:
            r = s.get(API_BASE + "eiendommer",
                      params={"adresse": street}, timeout=30)
            r.raise_for_status()
            return sorted({p.get("adresse", "") for p in r.json() if p.get("adresse")})
        except Exception:
            return []

    def fetch(self) -> list[Collection]:
        s = self._session()
        eiendom_id = self._id or self._resolve_id(s)

        today = datetime.date.today()
        r = s.get(
            API_BASE + "tomminger",
            params={
                "eiendomId": eiendom_id,
                "datoFra": (today - datetime.timedelta(days=14)).isoformat(),
                "datoTil": (today + datetime.timedelta(days=180)).isoformat(),
            },
            timeout=30,
        )
        r.raise_for_status()

        entries: list[Collection] = []
        for item in r.json():
            raw = item.get("dato", "")[:10]
            if not raw:
                continue
            date = datetime.date.fromisoformat(raw)
            fraction = unescape(item.get("fraksjon", "") or "Avfall").strip()
            entries.append(
                Collection(
                    date=date,
                    t=fraction,
                    icon=ICON_MAP.get(fraction, "mdi:trash-can"),
                )
            )
        return entries
