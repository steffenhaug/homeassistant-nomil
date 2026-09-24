"""Constants for the NOMIL integration."""

from __future__ import annotations

DOMAIN = "nomil"

# app + tenant ids are baked into NOMIL's app, same for everyone, not secrets
API_BASE = "https://tommeplan.nomil.no:9000/api/"
APPLIKASJONS_ID = "380b0118-95ba-4c57-b53c-2f79c3922d65"
OPPDRAGSGIVER_ID = "100"

# UA that identifies this as an unofficial client, not the real app
USER_AGENT = "nomil-ha/1.0 (unofficial NoMil Tommeplan client for Home Assistant)"

# NOMIL only plans ~6 months out, so looking further is pointless. (Also the
# API 500s when datoFra..datoTil spans more than 365 days.)
DEFAULT_LOOKAHEAD_DAYS = 180
DEFAULT_LOOKBACK_DAYS = 7

# poll twice a day, don't hammer their server
UPDATE_INTERVAL_HOURS = 12

CONF_EIENDOM_ID = "eiendom_id"
CONF_ADDRESS = "address"

DEFAULT_ICON = "mdi:recycle"

# waste type -> icon
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
