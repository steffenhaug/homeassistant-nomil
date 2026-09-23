# homeassistant-nomil

Bin collection dates from NOMIL (Nordfjord Miljøverk) in Home Assistant.
Covers Bremanger, Kinn, Stad, Gloppen, Stryn.

**This is slop. Use at your own risk.** I reverse-engineered NOMIL's app with Claude and
poked at its undocumented API.

## Install

HACS → custom repositories → add `https://github.com/steffenhaug/homeassistant-nomil`
(category: Integration) → install → restart → add **NOMIL** from Settings →
Devices & Services. Or just copy `custom_components/nomil` into your config folder.

Setup asks for your address (or the property UUID). You get a calendar entity and
a few sensors.

## Not HACS?

`nomil_ics.py` dumps an `.ics` you can subscribe to. `python3 nomil_ics.py --help`.

## How it works

See [`doc/nomil.md`](doc/nomil.md). Polls twice a day, nothing more.
