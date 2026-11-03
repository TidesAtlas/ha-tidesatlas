"""TidesAtlas Tides: high and low tide times for 13,000+ places worldwide."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TidesAtlasClient
from .const import CONF_PORT_ID
from .coordinator import TidesAtlasCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]

type TidesAtlasConfigEntry = ConfigEntry[TidesAtlasCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: TidesAtlasConfigEntry) -> bool:
    """Set up one place."""
    client = TidesAtlasClient(async_get_clientsession(hass), hass.config.language)
    coordinator = TidesAtlasCoordinator(hass, entry, client, int(entry.data[CONF_PORT_ID]))
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: TidesAtlasConfigEntry) -> bool:
    """Unload one place."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
