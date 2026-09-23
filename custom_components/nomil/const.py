"""Constants for the NOMIL waste collection integration."""

from __future__ import annotations

DOMAIN = "nomil"

# Norconsult Digital backend used by the "NoMil Tømmeplan" app. The application
# id and oppdragsgiver (client/tenant) id are compiled into the app and are the
# same for every NOMIL user; they are identifiers, not personal credentials.
API_BASE = "https://tommeplan.nomil.no:9000/api/"
APPLIKASJONS_ID = "380b0118-95ba-4c57-b53c-2f79c3922d65"
OPPDRAGSGIVER_ID = "100"

# Honest, self-identifying User-Agent; clearly marked unofficial so it does not
# impersonate the real app.
USER_AGENT = "nomil-ha/1.0 (unofficial NoMil Tommeplan client for Home Assistant)"

# How far forward/back the coordinator asks the API for pickups.
DEFAULT_LOOKAHEAD_DAYS = 120
DEFAULT_LOOKBACK_DAYS = 7

# Poll interval. The API is undocumented; be a courteous client.
UPDATE_INTERVAL_HOURS = 12

CONF_EIENDOM_ID = "eiendom_id"
CONF_ADDRESS = "address"

DEFAULT_ICON = "mdi:trash-can"

# Waste-fraction name (as returned by the API) -> Material Design Icon.
ICON_MAP: dict[str, str] = {
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
