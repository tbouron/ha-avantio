"""Add calendar entities for a given HomeAssistant ConfigEntry."""

import datetime
from zoneinfo import ZoneInfo

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AvantioCoordinator
from .entity import AvantioEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the calendar platform from a config entry."""
    coordinator: AvantioCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            BookingCalendar(
                translation_key=translation_key,
                coordinator=coordinator,
                accommodation=accommodation,
                unique_id=f"{accommodation['id']}_{translation_key}",
                icon=icon,
                for_rental=for_rental,
            )
            for accommodation in coordinator.get_accommodations()
            for translation_key, icon, for_rental in (
                ("rental", "mdi:calendar-check-outline", True),
                ("owner", "mdi:calendar-account-outline", False),
            )
        ]
    )


class BookingCalendar(AvantioEntity, CalendarEntity):
    """BookingCalendar is a class that represents a calendar entity for booking events."""

    def __init__(
        self,
        translation_key: str,
        coordinator: AvantioCoordinator,
        accommodation: dict,
        unique_id: str | None = None,
        icon: str | None = None,
        for_rental: bool = True,
    ) -> None:
        """Create the bookings calendar, with all its events."""
        super().__init__(coordinator, accommodation)
        self.entity_id = f"{Platform.CALENDAR}.{DOMAIN}_{unique_id}"
        if unique_id is not None:
            self._attr_unique_id = unique_id
        self._attr_translation_key = translation_key
        self._attr_icon = icon
        self._for_rental = for_rental

    @property
    def _events(self) -> list[CalendarEvent]:
        """Build the events from the coordinator's data, cached or fresh."""
        return [
            CalendarEvent(
                **{
                    k: v
                    for k, v in event_data.items()
                    if k not in ("is_rental", "accommodation_id")
                }
            )
            for event_data in self.coordinator.get_events(
                self._accommodation_id, self._for_rental
            )
        ]

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
        now = datetime.datetime.now(ZoneInfo(self.coordinator.hass.config.time_zone))
        upcoming_events = [event for event in self._events if event.start > now]
        upcoming_events.sort(key=lambda event: event.start)

        return upcoming_events[0] if upcoming_events else None
