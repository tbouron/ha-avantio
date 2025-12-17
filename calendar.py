"""Add calendar entities for a given HomeAssistant ConfigEntry."""

import datetime
from zoneinfo import ZoneInfo

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AvantioCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the calendar platform from a config entry."""
    coordinator: AvantioCoordinator = hass.data[DOMAIN][entry.entry_id]

    for accommodation in coordinator.get_accommodations():
        async_add_entities(
            [
                BookingCalendar(
                    translation_key="rental",
                    coordinator=coordinator,
                    unique_id=f"{accommodation['id']}_rental",
                    icon="mdi:calendar-check-outline",
                    for_rental=True,
                ),
                BookingCalendar(
                    translation_key="owner",
                    coordinator=coordinator,
                    unique_id=f"{accommodation['id']}_owner",
                    icon="mdi:calendar-account-outline",
                    for_rental=False,
                ),
            ],
            True,
        )


class BookingCalendar(CoordinatorEntity[AvantioCoordinator], CalendarEntity):
    """BookingCalendar is a class that represents a calendar entity for booking events."""

    _attr_has_entity_name = True

    def __init__(
        self,
        translation_key: str,
        coordinator: AvantioCoordinator,
        unique_id: str | None = None,
        icon: str | None = None,
        for_rental: bool = True,
    ) -> None:
        """Create the bookings calendar, with all its events."""
        super().__init__(coordinator)
        self.entity_id = f"{Platform.CALENDAR}.{DOMAIN}_{unique_id}"
        if unique_id is not None:
            self._attr_unique_id = unique_id
        self._attr_translation_key = translation_key
        self._attr_icon = icon
        self._events: list[CalendarEvent] = []
        self._event: CalendarEvent | None = None
        self._for_rental = for_rental

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._events = [
            CalendarEvent(**{k: v for k, v in event_data.items() if k != "is_rental"})
            for event_data in self.coordinator.get_bookings()
            if event_data["is_rental"] is self._for_rental
        ]
        self.async_write_ha_state()

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[CalendarEvent]:
        """Return the full list of events."""
        return self._events

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        if not self._events:
            return None

        now = datetime.datetime.now(ZoneInfo(self.coordinator.hass.config.time_zone))
        upcoming_events = [event for event in self._events if event.start > now]
        upcoming_events.sort(key=lambda event: event.start)

        return upcoming_events[0] if upcoming_events else None
