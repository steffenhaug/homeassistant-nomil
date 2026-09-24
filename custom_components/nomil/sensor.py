"""Sensors: next pickup overall, and next date per waste type."""

from __future__ import annotations

from datetime import date

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DEFAULT_ICON, DOMAIN, ICON_MAP
from .coordinator import NomilCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensors."""
    coordinator: NomilCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = [NomilNextSensor(coordinator, entry)]
    fractions = sorted(
        {
            (item.get("fraksjon") or "").strip()
            for item in (coordinator.data or [])
            if item.get("fraksjon")
        }
    )
    entities.extend(
        NomilFractionSensor(coordinator, entry, fraction) for fraction in fractions
    )
    async_add_entities(entities)


def _parse_date(dato: str | None) -> date | None:
    if not dato:
        return None
    try:
        return date.fromisoformat(dato[:10])
    except ValueError:
        return None


def _sorted_days(pickups: list[dict], fraction: str | None = None) -> list[date]:
    days = {
        d
        for item in pickups
        if (d := _parse_date(item.get("dato"))) is not None
        and (fraction is None or (item.get("fraksjon") or "").strip() == fraction)
    }
    return sorted(days)


class _NomilBaseSensor(CoordinatorEntity[NomilCoordinator], SensorEntity):
    """Shared device wiring."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.DATE

    def __init__(self, coordinator: NomilCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id or entry.entry_id)},
            name=entry.title,
            manufacturer="NOMIL",
            model="Tømmekalender",
        )

    @property
    def available(self) -> bool:
        """Stay available on a failed refresh; keep the last schedule."""
        return self.coordinator.data is not None


class NomilNextSensor(_NomilBaseSensor):
    """Date of the next pickup of any kind."""

    _attr_icon = DEFAULT_ICON
    _attr_translation_key = "next_collection"

    def __init__(self, coordinator: NomilCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.unique_id}_next"

    @property
    def native_value(self) -> date | None:
        today = dt_util.now().date()
        for day in _sorted_days(self.coordinator.data or []):
            if day >= today:
                return day
        return None

    @property
    def extra_state_attributes(self) -> dict[str, list[str]]:
        day = self.native_value
        if day is None:
            return {"fractions": []}
        fractions = sorted(
            {
                (item.get("fraksjon") or "").strip()
                for item in (self.coordinator.data or [])
                if _parse_date(item.get("dato")) == day
            }
        )
        return {"fractions": fractions}


class NomilFractionSensor(_NomilBaseSensor):
    """Date of the next pickup for one waste type."""

    def __init__(
        self, coordinator: NomilCoordinator, entry: ConfigEntry, fraction: str
    ) -> None:
        super().__init__(coordinator, entry)
        self._fraction = fraction
        self._attr_name = fraction
        self._attr_icon = ICON_MAP.get(fraction, DEFAULT_ICON)
        self._attr_unique_id = f"{entry.unique_id}_{fraction}"

    @property
    def native_value(self) -> date | None:
        today = dt_util.now().date()
        for day in _sorted_days(self.coordinator.data or [], self._fraction):
            if day >= today:
                return day
        return None
