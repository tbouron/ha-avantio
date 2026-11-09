"""Add binary sensor entities for a given HomeAssistant ConfigEntry."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AvantioCoordinator
from .entity import AvantioSyncEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensor platform from a config entry."""
    coordinator: AvantioCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [SyncProblemBinarySensor(coordinator, unique_id=f"{entry.entry_id}_sync_problem")]
    )


class SyncProblemBinarySensor(AvantioSyncEntity, BinarySensorEntity):
    """On when the last attempt to sync with Avantio failed."""

    _attr_translation_key = "sync_problem"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: AvantioCoordinator, unique_id: str) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.entity_id = f"{Platform.BINARY_SENSOR}.{DOMAIN}_sync_problem"
        self._attr_unique_id = unique_id

    @property
    def is_on(self) -> bool:
        """Return whether the last sync attempt failed."""
        return not self.coordinator.last_update_success
