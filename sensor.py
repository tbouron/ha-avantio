"""Add sensor entities for a given HomeAssistant ConfigEntry."""

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_registry import Platform
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AvantioCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up the sensor platform from a config entry."""
    coordinator: AvantioCoordinator = hass.data[DOMAIN][entry.entry_id]

    for accommodation in coordinator.get_accommodations():
        async_add_entities([TotalEarningsSensor(coordinator=coordinator, unique_id=f"{accommodation["id"]}_total_earnings")], True)

    await coordinator.async_request_refresh()


class TotalEarningsSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Sensor that shows the total earnings."""

    coordinator: AvantioCoordinator
    _attr_has_entity_name = True

    def __init__(self, coordinator: AvantioCoordinator, unique_id: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_id = f"{Platform.SENSOR}.{DOMAIN}_{unique_id}"
        self._attr_translation_key = "total_earnings"
        if unique_id is not None:
            self._attr_unique_id = unique_id
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_native_unit_of_measurement = "€"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self.coordinator.get_total_earnings()

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            year: f"{round(value, 2)} €"
            for year, value in self.coordinator.get_yearly_earnings().items()
        }
