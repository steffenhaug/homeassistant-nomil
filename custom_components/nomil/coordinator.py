"""Data update coordinator for the NOMIL integration."""

from __future__ import annotations

import logging
from datetime import date, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import NomilApiClient, NomilApiError
from .const import (
    DEFAULT_LOOKAHEAD_DAYS,
    DEFAULT_LOOKBACK_DAYS,
    DOMAIN,
    UPDATE_INTERVAL_HOURS,
)

_LOGGER = logging.getLogger(__name__)


class NomilCoordinator(DataUpdateCoordinator[list[dict]]):
    """Fetch the pickup schedule for one property on a slow poll."""

    def __init__(
        self, hass: HomeAssistant, client: NomilApiClient, eiendom_id: str
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=UPDATE_INTERVAL_HOURS),
        )
        self._client = client
        self._eiendom_id = eiendom_id

    async def _async_update_data(self) -> list[dict]:
        today = date.today()
        try:
            return await self._client.get_pickups(
                self._eiendom_id,
                today - timedelta(days=DEFAULT_LOOKBACK_DAYS),
                today + timedelta(days=DEFAULT_LOOKAHEAD_DAYS),
            )
        except NomilApiError as err:
            # On failure the coordinator keeps the previous data, so the
            # calendar/sensors do not blank out on a transient hiccup.
            raise UpdateFailed(str(err)) from err
