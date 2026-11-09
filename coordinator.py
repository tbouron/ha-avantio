"""Fetch data using the given AvantioClient, for a specific HomeAssistant ConfigEntry."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
from zoneinfo import ZoneInfo

from homeassistant.components import persistent_notification
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.storage import Store
from homeassistant.helpers.translation import async_get_cached_translations
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .client import AvantioClient, InvalidAuth
from .const import DOMAIN
from .model import (
    CACHE_VERSION,
    booked_days_by_month,
    booking_events,
    bookings_for,
    build_snapshot,
    is_valid_snapshot,
    last_synced,
    storage_key,
    total_earnings,
    yearly_earnings,
)

_LOGGER = logging.getLogger(__name__)

SYNC_INTERVAL = timedelta(days=1)
RETRY_INTERVAL = timedelta(hours=1)


class AvantioCoordinator(DataUpdateCoordinator[dict | None]):
    """Sync Avantio bookings once a day and keep the last good copy on disk.

    `data` is the last good snapshot (see model.py), loaded from disk at
    startup and replaced after each successful sync. A failed sync leaves it
    untouched, so entities keep showing it.
    """

    config_entry: ConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: AvantioClient
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=SYNC_INTERVAL,
        )
        self._client = client
        self._store: Store[dict] = Store(
            hass, CACHE_VERSION, storage_key(entry.entry_id)
        )
        self._events: list[dict] = []
        self._known_uids: set = set()

    @property
    def has_data(self) -> bool:
        """Tell whether a snapshot is available, cached or fresh."""
        return self.data is not None

    async def async_load_cache(self) -> None:
        """Load the snapshot saved by the last successful sync, if any."""
        cached = await self._store.async_load()
        if cached is None:
            return
        if not is_valid_snapshot(cached):
            _LOGGER.warning("Ignoring unreadable Avantio cache")
            return
        self._use_snapshot(cached)
        # Bookings made while Home Assistant was down get notified on next sync.
        self._known_uids = {event["uid"] for event in self._events}
        self.data = cached
        _LOGGER.debug("Loaded Avantio data synced at %s", cached.get("last_synced"))

    async def _async_update_data(self) -> dict:
        """Fetch fresh data, keeping the cached snapshot when that fails."""
        # Failures retry hourly; a success goes back to the daily sync.
        self.update_interval = RETRY_INTERVAL

        if self._reauth_in_progress():
            # Avoid a failed login every hour while the credentials are known bad.
            raise UpdateFailed("Waiting for re-authentication")

        try:
            bookings = await self._client.get_bookings()
            accommodations = await self._client.get_accommodations()
            snapshot = build_snapshot(
                bookings, accommodations, dt_util.utcnow(), previous=self.data
            )
        except InvalidAuth as err:
            if not self.has_data:
                raise ConfigEntryAuthFailed(
                    f"Credentials expired for {self.config_entry.entry_id}"
                ) from err
            # With cached data, ask for new credentials but keep the entities
            # available instead of failing the whole entry.
            self.config_entry.async_start_reauth(self.hass)
            raise UpdateFailed(f"Invalid credentials: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Error fetching booking data: {err}") from err

        notify = self.has_data
        self._use_snapshot(snapshot)
        if notify:
            self._notify_new_bookings()
        self._known_uids = {event["uid"] for event in self._events}
        await self._store.async_save(snapshot)

        self.update_interval = SYNC_INTERVAL
        return snapshot

    def _reauth_in_progress(self) -> bool:
        return any(
            self.config_entry.async_get_active_flows(self.hass, {SOURCE_REAUTH})
        )

    def _use_snapshot(self, snapshot: dict) -> None:
        """Rebuild the calendar events of a snapshot."""
        timezone = ZoneInfo(self.hass.config.time_zone)
        self._events = booking_events(snapshot["bookings"], timezone)

    def _notify_new_bookings(self) -> None:
        """Create a notification for each rental not seen in a previous sync."""
        new_rentals = [
            event
            for event in self._events
            if event["is_rental"] and event["uid"] not in self._known_uids
        ]
        if not new_rentals:
            return
        translations = async_get_cached_translations(
            self.hass, self.hass.config.language, "notifications", DOMAIN
        )
        title = translations.get(
            "component.avantio.notifications.new_booking.title", "🏠 New booking"
        )
        message_tpl = translations.get(
            "component.avantio.notifications.new_booking.message",
            "From {start} to {end}",
        )
        for event in new_rentals:
            persistent_notification.async_create(
                self.hass,
                message_tpl.format(
                    start=event["start"].strftime("%d %b %Y"),
                    end=event["end"].strftime("%d %b %Y"),
                ),
                title=title,
                notification_id=f"avantio_new_booking_{event['uid']}",
            )

    @property
    def last_synced(self) -> datetime | None:
        """Return when the shown data was fetched."""
        return last_synced(self.data) if self.data else None

    def get_accommodations(self) -> list[dict]:
        """Get the accommodations."""
        return self.data["accommodations"] if self.data else []

    def _bookings(self, accommodation_id) -> list[dict]:
        return bookings_for(self.data["bookings"], accommodation_id) if self.data else []

    def get_events(self, accommodation_id, for_rental: bool) -> list[dict]:
        """Get the calendar events of one accommodation's rentals, or owner stays."""
        return [
            event
            for event in self._events
            if event["is_rental"] is for_rental
            and event["accommodation_id"] in (None, accommodation_id)
        ]

    def get_total_earnings(self, accommodation_id) -> float | None:
        """Get the total earnings of one accommodation, in euros."""
        return total_earnings(self._bookings(accommodation_id)) if self.data else None

    def get_yearly_earnings(self, accommodation_id) -> dict[int, float]:
        """Get the earnings of one accommodation per year, in euros."""
        return yearly_earnings(self._bookings(accommodation_id))

    def get_booked_days_by_month(
        self, accommodation_id, for_rental: bool
    ) -> dict[int, dict[int, int]]:
        """Get the booked nights of one accommodation per year and month."""
        return booked_days_by_month(self._bookings(accommodation_id), for_rental)
