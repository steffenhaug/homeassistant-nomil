"""Config flow for NOMIL: address lookup or direct property id."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import NomilApiClient, NomilApiError
from .const import CONF_ADDRESS, CONF_EIENDOM_ID, DOMAIN


def _title(match: dict) -> str:
    address = (match.get("adresse") or "Ukjend adresse").strip()
    kommune = (match.get("kommune") or "").strip()
    return f"{address}, {kommune}" if kommune else address


class NomilConfigFlow(ConfigFlow, domain=DOMAIN):
    """Guided setup: pick a property by address, or enter its id."""

    VERSION = 1

    def __init__(self) -> None:
        self._matches: list[dict] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return self.async_show_menu(
            step_id="user", menu_options=["address", "manual"]
        )

    async def async_step_address(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            client = NomilApiClient(async_get_clientsession(self.hass))
            try:
                matches = await client.search_addresses(user_input[CONF_ADDRESS])
            except NomilApiError:
                errors["base"] = "cannot_connect"
            else:
                # De-duplicate by property id so the dropdown values are unique.
                seen: set[str] = set()
                self._matches = [
                    m for m in matches
                    if m.get("id") and not (m["id"] in seen or seen.add(m["id"]))
                ]
                if not self._matches:
                    errors["base"] = "no_results"
                else:
                    return await self.async_step_select()
        return self.async_show_form(
            step_id="address",
            data_schema=vol.Schema({vol.Required(CONF_ADDRESS): str}),
            errors=errors,
        )

    async def async_step_select(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            eiendom_id = user_input[CONF_EIENDOM_ID]
            match = next((m for m in self._matches if m["id"] == eiendom_id), None)
            await self.async_set_unique_id(eiendom_id)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=_title(match) if match else eiendom_id,
                data={CONF_EIENDOM_ID: eiendom_id},
            )
        options = [
            SelectOptionDict(value=m["id"], label=_title(m)) for m in self._matches
        ]
        return self.async_show_form(
            step_id="select",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EIENDOM_ID): SelectSelector(
                        SelectSelectorConfig(
                            options=options, mode=SelectSelectorMode.DROPDOWN
                        )
                    )
                }
            ),
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            eiendom_id = user_input[CONF_EIENDOM_ID].strip()
            client = NomilApiClient(async_get_clientsession(self.hass))
            try:
                await client.validate_id(eiendom_id)
            except NomilApiError:
                errors["base"] = "invalid_id"
            else:
                await self.async_set_unique_id(eiendom_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"NOMIL {eiendom_id[:8]}",
                    data={CONF_EIENDOM_ID: eiendom_id},
                )
        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema({vol.Required(CONF_EIENDOM_ID): str}),
            errors=errors,
        )
