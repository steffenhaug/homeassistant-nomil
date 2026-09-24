"""Diagnostics for NOMIL."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_EIENDOM_ID, DOMAIN
from .coordinator import NomilCoordinator

# property id and the address (entry title) point at a home, so hide them
TO_REDACT = {CONF_EIENDOM_ID, "title"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Dump entry + current schedule for debugging."""
    coordinator: NomilCoordinator = hass.data[DOMAIN][entry.entry_id]
    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "last_update_success": coordinator.last_update_success,
        "pickup_count": len(coordinator.data or []),
        "pickups": coordinator.data or [],
    }
