"""Config flow: search a place by name, or pick one near home."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig, SelectSelectorMode

from .api import TidesAtlasClient, TidesAtlasError
from .const import CONF_PORT_ID, CONF_PORT_NAME, DOMAIN


def _label(port: dict[str, Any]) -> str:
    label = f"{port['name']}, {port['country']}"
    if port.get("distance_km") is not None:
        label += f" ({port['distance_km']} km)"
    return label


class TidesAtlasConfigFlow(ConfigFlow, domain=DOMAIN):
    """Add a place."""

    VERSION = 1

    def __init__(self) -> None:
        self._ports: list[dict[str, Any]] = []

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask for a place name (empty = places near home)."""
        errors: dict[str, str] = {}
        if user_input is not None:
            client = TidesAtlasClient(async_get_clientsession(self.hass), self.hass.config.language)
            query = (user_input.get("search") or "").strip()
            try:
                if query:
                    self._ports = await client.search(query)
                else:
                    self._ports = await client.nearest(self.hass.config.latitude, self.hass.config.longitude)
            except TidesAtlasError:
                errors["base"] = "cannot_connect"
            else:
                if self._ports:
                    return await self.async_step_pick()
                errors["base"] = "no_results"
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Optional("search", default=""): str}),
            errors=errors,
        )

    async def async_step_pick(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Choose one of the places found."""
        if user_input is not None:
            port = next(p for p in self._ports if str(p["id"]) == user_input[CONF_PORT_ID])
            await self.async_set_unique_id(str(port["id"]))
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=port["name"],
                data={CONF_PORT_ID: int(port["id"]), CONF_PORT_NAME: port["name"]},
            )
        options = [{"value": str(p["id"]), "label": _label(p)} for p in self._ports]
        return self.async_show_form(
            step_id="pick",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PORT_ID, default=options[0]["value"]): SelectSelector(
                        SelectSelectorConfig(options=options, mode=SelectSelectorMode.LIST)
                    )
                }
            ),
        )
