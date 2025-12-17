"""The Avantio integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import ConfigType

from .client import AvantioClient
from .const import CONF_USERNAME, CONF_PASSWORD, DOMAIN
from .coordinator import AvantioCoordinator

PLATFORMS: list[Platform] = [Platform.CALENDAR, Platform.SENSOR]


def setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Your controller/hub specific code."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Travel Paradise from a config entry."""
    client = AvantioClient(
        username=entry.data.get(CONF_USERNAME), password=entry.data.get(CONF_PASSWORD)
    )

    coordinator = AvantioCoordinator(hass, client)
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await coordinator.async_request_refresh()

    # Forward the setup to the platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    await coordinator.async_cleanup()

    unload_ok = True
    for platform in PLATFORMS:
        unload_ok = unload_ok and await hass.config_entries.async_forward_entry_unload(
            entry, platform
        )

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
