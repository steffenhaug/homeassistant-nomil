# NOMIL waste collection → Home Assistant

Nordfjord Miljøverk (NOMIL) has no public calendar export. Their **NoMil
Tømmeplan** app talks to an undocumented backend from Norconsult Digital.
This repo documents that API and gives you two ways to get your bin schedule
into Home Assistant (or any calendar).

Covers the NOMIL municipalities: **Bremanger, Kinn, Stad, Gloppen, Stryn.**

## The API

Base URL: `https://tommeplan.nomil.no:9000/api/`

Authentication is a fixed app identity, not a personal login. The values below
are baked into the app and are identical for every NOMIL user:

- `applikasjonsId`: `380b0118-95ba-4c57-b53c-2f79c3922d65`
- `oppdragsgiverId` (client): `100`

**1. Log in** to get a session token (returned as a response *header*):

```sh
curl -sD - -o /dev/null -X POST https://tommeplan.nomil.no:9000/api/login \
  -H 'Content-Type: application/json' \
  -d '{"applikasjonsId":"380b0118-95ba-4c57-b53c-2f79c3922d65","oppdragsgiverId":"100"}'
# -> response header:  Token: <guid>
```

**2. Find your property** (`eiendom`). Search is "starts-with" on the address:

```sh
curl -s -G https://tommeplan.nomil.no:9000/api/eiendommer \
  --data-urlencode 'adresse=Sjøgata 103' -H 'Token: <token>'
# -> [{"id":"<guid>","kommune":"Stad","adresse":"Sjøgata 103", ...}]
```

**3. Get the pickups** for that property id over a date range:

```sh
curl -s -G https://tommeplan.nomil.no:9000/api/tomminger \
  --data-urlencode 'eiendomId=<guid>' \
  --data-urlencode 'datoFra=2026-09-01' \
  --data-urlencode 'datoTil=2027-03-01' -H 'Token: <token>'
# -> [{"dato":"2026-09-22T00:00:00","fraksjon":"Papir og Plastemballasje", ...}, ...]
```

The API returns already-expanded, concrete pickup dates — no recurrence rules to
compute. Each entry has `dato`, `fraksjon` (waste type), `fraksjonId`,
`symbolId`.

Other read-only endpoints the app uses (all need the `Token` header):
`oppdragsgiver?oppdragsgiverId=100`, `stasjoner` (recycling stations),
`videolinker`, `meldinger/kategorier?meldingOpphavId=7`,
`eiendommer/hentestedGeolokasjon?breddegrad={lat}&lengdegrad={lon}`.

## Option A — Home Assistant integration (recommended)

Uses the community [`waste_collection_schedule`](https://github.com/mampfes/hacs_waste_collection_schedule)
framework, which gives you a calendar entity plus "days until next pickup"
sensors.

1. Install **Waste Collection Schedule** via HACS (or manually).
2. Copy [`custom_components/waste_collection_schedule/waste_collection_schedule/source/nomil_no.py`](custom_components/waste_collection_schedule/waste_collection_schedule/source/nomil_no.py)
   into the same `source/` folder of your installed framework.
   (Once merged upstream this step goes away.)
3. Add to `configuration.yaml`:

```yaml
waste_collection_schedule:
  sources:
    - name: nomil_no
      args:
        address: "Sjøgata 103"
        kommune: "Stad"      # optional, disambiguates duplicate street names
      calendar_title: "Renovasjon"
```

You can also pin an exact property instead of an address:

```yaml
      args:
        id: "368ad825-6fc6-4bc5-aa6e-de88b59c00c6"
```

Then add a `sensor` using the framework's `waste_collection_schedule` platform,
or use the auto-created calendar entity. See the framework docs for sensor
options.

## Option B — Standalone iCal feed (no HACS)

[`nomil_ics.py`](nomil_ics.py) is a zero-dependency Python script (standard
library only) that writes a `.ics` file with one all-day event per collection
day and a day-before reminder.

```sh
# Find your property id:
python3 nomil_ics.py --search "Sjøgata 103"

# Generate the calendar (by address, or by --id):
python3 nomil_ics.py --address "Sjøgata 103" --kommune Stad --out nomil.ics
```

Run it on a schedule (cron / systemd timer) to keep the file fresh, serve the
`.ics` over HTTP, and subscribe from Home Assistant's
[Remote Calendar](https://www.home-assistant.io/integrations/remote_calendar/)
integration, or from Google/Apple/Outlook calendars.

## Files

| File | What |
|---|---|
| `custom_components/.../source/nomil_no.py` | Home Assistant source for the waste_collection_schedule framework |
| `nomil_ics.py` | Standalone `.ics` generator (stdlib only) |
| `doc/nomil.md` | Longer notes on the API and how it was found |

## Notes & caveats

- This is an undocumented, private API; NOMIL could change or block it at any
  time. Be a good citizen: poll infrequently (once or twice a day is plenty).
- The app id and client id are shared, not secret credentials — no personal
  data or login is involved, and you only read your own address's public
  pickup schedule.
- Not affiliated with or endorsed by NOMIL or Norconsult.
