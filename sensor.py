"""Add sensor entities for a given HomeAssistant ConfigEntry."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, Platform, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AvantioCoordinator
from .entity import AvantioEntity, AvantioSyncEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up the sensor platform from a config entry."""
    coordinator: AvantioCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = [
        LastSyncSensor(coordinator=coordinator, unique_id=f"{entry.entry_id}_last_sync")
    ]
    for accommodation in coordinator.get_accommodations():
        acc_id = accommodation["id"]
        entities.append(TotalEarningsSensor(coordinator, accommodation, unique_id=f"{acc_id}_total_earnings"))
        entities.append(BookingDaysSensor(coordinator, accommodation, unique_id=f"{acc_id}_rental_days", for_rental=True))
        entities.append(BookingDaysSensor(coordinator, accommodation, unique_id=f"{acc_id}_owner_days", for_rental=False))

    async_add_entities(entities)


class TotalEarningsSensor(AvantioEntity, SensorEntity):
    """Representation of a Sensor that shows the total earnings."""

    _attr_translation_key = "total_earnings"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = "€"

    def __init__(self, coordinator: AvantioCoordinator, accommodation: dict, unique_id: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, accommodation)
        self.entity_id = f"{Platform.SENSOR}.{DOMAIN}_{unique_id}"
        self._attr_unique_id = unique_id

    @property
    def native_value(self) -> float | None:
        """Return the total earnings."""
        return self.coordinator.get_total_earnings(self._accommodation_id)

    @property
    def extra_state_attributes(self):
        """Return the earnings per year."""
        return {
            year: f"{value} €"
            for year, value in self.coordinator.get_yearly_earnings(self._accommodation_id).items()
        }


class BookingDaysSensor(AvantioEntity, SensorEntity):
    """Sensor showing total booking days with a per-year/month breakdown."""

    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = UnitOfTime.DAYS

    def __init__(self, coordinator: AvantioCoordinator, accommodation: dict, unique_id: str, for_rental: bool) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, accommodation)
        self.entity_id = f"{Platform.SENSOR}.{DOMAIN}_{unique_id}"
        self._attr_unique_id = unique_id
        self._attr_translation_key = "rental_days" if for_rental else "owner_days"
        self._for_rental = for_rental

    @property
    def native_value(self) -> int:
        """Return total booking days across all time."""
        breakdown = self.coordinator.get_booked_days_by_month(self._accommodation_id, self._for_rental)
        return sum(days for months in breakdown.values() for days in months.values())

    @property
    def extra_state_attributes(self):
        """Return per-year, per-month breakdown."""
        return {"breakdown": self.coordinator.get_booked_days_by_month(self._accommodation_id, self._for_rental)}


class LastSyncSensor(AvantioSyncEntity, SensorEntity):
    """When the data shown by the other entities was last fetched from Avantio."""
    _attr_translation_key = "last_sync"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: AvantioCoordinator, unique_id: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_id = f"{Platform.SENSOR}.{DOMAIN}_last_sync"
        self._attr_unique_id = unique_id

    @property
    def native_value(self) -> datetime | None:
        """Return when the last successful sync happened."""
        return self.coordinator.last_synced
