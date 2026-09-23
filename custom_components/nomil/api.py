"""Async client for the NOMIL (Norconsult Tømmeplan) backend."""

from __future__ import annotations

import logging
from datetime import date

import aiohttp

from .const import (
    API_BASE,
    APPLIKASJONS_ID,
    OPPDRAGSGIVER_ID,
    USER_AGENT,
)

_LOGGER = logging.getLogger(__name__)

_TIMEOUT = aiohttp.ClientTimeout(total=30)


class NomilApiError(Exception):
    """A request to the NOMIL backend failed."""


class NomilAuthError(NomilApiError):
    """Authentication with the NOMIL backend failed."""


class NomilApiClient:
    """Minimal client: log in for a token, then read address/pickup data."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session
        self._token: str | None = None

    async def _login(self) -> None:
        try:
            async with self._session.post(
                API_BASE + "login",
                json={
                    "applikasjonsId": APPLIKASJONS_ID,
                    "oppdragsgiverId": OPPDRAGSGIVER_ID,
                },
                headers={"User-Agent": USER_AGENT},
                timeout=_TIMEOUT,
            ) as resp:
                resp.raise_for_status()
                token = resp.headers.get("Token")
        except aiohttp.ClientError as err:
            raise NomilApiError(f"Login request failed: {err}") from err
        if not token:
            raise NomilAuthError("Login did not return a Token header")
        self._token = token

    async def _get(self, path: str, params: dict[str, str]) -> list[dict]:
        if self._token is None:
            await self._login()
        for attempt in range(2):
            try:
                async with self._session.get(
                    API_BASE + path,
                    params=params,
                    headers={"Token": self._token or "", "User-Agent": USER_AGENT},
                    timeout=_TIMEOUT,
                ) as resp:
                    if resp.status == 401 and attempt == 0:
                        await self._login()
                        continue
                    resp.raise_for_status()
                    return await resp.json(content_type=None)
            except aiohttp.ClientError as err:
                raise NomilApiError(f"Request to {path} failed: {err}") from err
        raise NomilAuthError("Unauthorized even after re-login")

    async def search_addresses(self, address: str) -> list[dict]:
        """Return properties whose address starts with the given string."""
        return await self._get("eiendommer", {"adresse": address})

    async def get_pickups(
        self, eiendom_id: str, date_from: date, date_to: date
    ) -> list[dict]:
        """Return concrete pickup entries for a property in a date range."""
        return await self._get(
            "tomminger",
            {
                "eiendomId": eiendom_id,
                "datoFra": date_from.isoformat(),
                "datoTil": date_to.isoformat(),
            },
        )

    async def validate_id(self, eiendom_id: str) -> bool:
        """Cheaply check that a property id is accepted by the API."""
        today = date.today()
        await self.get_pickups(eiendom_id, today, today)
        return True
