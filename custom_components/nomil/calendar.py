"""Calendar of upcoming NOMIL pickups."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DEFAULT_ICON, DOMAIN
from .coordinator import NomilCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the calendar entity."""
    coordinator: NomilCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([NomilCalendar(coordinator, entry)])


def _parse_date(dato: str | None) -> date | None:
    if not dato:
        return None
    try:
        return date.fromisoformat(dato[:10])
    except ValueError:
        return None


def build_events(pickups: list[dict]) -> list[CalendarEvent]:
    """Group same-day waste types into one all-day event, sorted by date."""
    by_day: dict[date, list[str]] = {}
    for item in pickups:
        day = _parse_date(item.get("dato"))
        if day is None:
            continue
        fraction = (item.get("fraksjon") or "Avfall").strip()
        names = by_day.setdefault(day, [])
        if fraction not in names:
            names.append(fraction)
    events: list[CalendarEvent] = []
    for day in sorted(by_day):
        events.append(
            CalendarEvent(
                start=day,
                end=day + timedelta(days=1),
                summary=", ".join(sorted(by_day[day])),
            )
        )
    return events


class NomilCalendar(CoordinatorEntity[NomilCoordinator], CalendarEntity):
    """Upcoming pickups for one property."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_icon = DEFAULT_ICON

    def __init__(self, coordinator: NomilCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.unique_id}_calendar"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id or entry.entry_id)},
            name=entry.title,
            manufacturer="NOMIL",
            model="Tømmekalender",
        )

    @property
    def event(self) -> CalendarEvent | None:
        """Current or next pickup, from cached data."""
        today = dt_util.now().date()
        for ev in build_events(self.coordinator.data or []):
            if ev.end > today:  # end is exclusive (day after pickup)
                return ev
        return None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Events in a range, from cached data (no API call)."""
        start = start_date.date() if isinstance(start_date, datetime) else start_date
        end = end_date.date() if isinstance(end_date, datetime) else end_date
        return [
            ev
            for ev in build_events(self.coordinator.data or [])
            if ev.start < end and ev.end > start
        ]
