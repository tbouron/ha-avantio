"""The Avantio integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .client import AvantioClient
from .const import CONF_USERNAME, CONF_PASSWORD, DOMAIN
from .coordinator import AvantioCoordinator
from .model import CACHE_VERSION, storage_key

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.CALENDAR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Avantio from a config entry."""
    client = AvantioClient(
        username=entry.data.get(CONF_USERNAME), password=entry.data.get(CONF_PASSWORD)
    )

    coordinator = AvantioCoordinator(hass, entry, client)
    await coordinator.async_load_cache()

    if coordinator.has_data:
        # Set up from the cache even when Avantio cannot be reached; a failed
        # sync is retried hourly and reported by the sync status entities.
        await coordinator.async_refresh()
    else:
        # Nothing to show yet: raises ConfigEntryNotReady (Home Assistant
        # retries the setup) or ConfigEntryAuthFailed (starts re-authentication).
        await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Delete the cached bookings when the integration is removed."""
    await Store(hass, CACHE_VERSION, storage_key(entry.entry_id)).async_remove()
