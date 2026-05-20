"""Add sensor entities for a given HomeAssistant ConfigEntry."""

from collections import defaultdict
from datetime import timedelta

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

    entities = []
    for accommodation in coordinator.get_accommodations():
        acc_id = accommodation["id"]
        entities.append(TotalEarningsSensor(coordinator=coordinator, unique_id=f"{acc_id}_total_earnings"))
        entities.append(BookingDaysSensor(coordinator=coordinator, unique_id=f"{acc_id}_rental_days", for_rental=True))
        entities.append(BookingDaysSensor(coordinator=coordinator, unique_id=f"{acc_id}_owner_days", for_rental=False))

    async_add_entities(entities, True)
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


class BookingDaysSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing total booking days with a per-year/month breakdown."""

    coordinator: AvantioCoordinator
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "d"

    def __init__(self, coordinator: AvantioCoordinator, unique_id: str, for_rental: bool) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_id = f"{Platform.SENSOR}.{DOMAIN}_{unique_id}"
        self._attr_unique_id = unique_id
        self._attr_translation_key = "rental_days" if for_rental else "owner_days"
        self._for_rental = for_rental

    def _monthly_breakdown(self) -> dict[int, dict[int, int]]:
        events = self.coordinator.get_bookings_guests() if self._for_rental else self.coordinator.get_bookings_owner()
        result: dict[tuple[int, int], int] = defaultdict(int)
        for event in events:
            current = event["start"].date()
            end = event["end"].date()
            while current < end:
                result[(current.year, current.month)] += 1
                current += timedelta(days=1)
        breakdown: dict[int, dict[int, int]] = {}
        for (year, month), days in result.items():
            breakdown.setdefault(year, {})[month] = days
        return breakdown

    @property
    def state(self):
        """Return total booking days across all time."""
        breakdown = self._monthly_breakdown()
        return sum(days for months in breakdown.values() for days in months.values())

    @property
    def extra_state_attributes(self):
        """Return per-year, per-month breakdown."""
        return {"breakdown": self._monthly_breakdown()}
