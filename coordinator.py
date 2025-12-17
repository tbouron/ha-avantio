"""Fetch data using the given AvantioClient, for a specific HomeAssistant ConfigEntry."""

from collections import defaultdict
from datetime import datetime, timedelta
import logging
from zoneinfo import ZoneInfo

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import AvantioClient, InvalidAuth

_LOGGER = logging.getLogger(__name__)


class AvantioCoordinator(DataUpdateCoordinator):
    """My custom coordinator."""

    def __init__(self, hass: HomeAssistant, client: AvantioClient) -> None:
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="Travel Paradise Locations",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(days=1),
        )
        self._client = client
        self._events = None
        self._total_earnings = None
        self._yearly_earnings = None
        self._accommodations = None

    async def _async_setup(self):
        """Set up the coordinator."""
        if await self._client.sign_in():
            await self.async_request_refresh()
            return True

        return False

    async def async_cleanup(self):
        """Clean up the open sessions from the client."""
        await self._client.close()

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:
            data = await self._client.get_bookings()
            timezone = ZoneInfo(self.hass.config.time_zone)

            self._events = [
                {
                    "uid": row["id"],
                    "start": parse_date_with_time(row["bookingStart"], 17, timezone),
                    "end": parse_date_with_time(row["bookingEnd"], 10, timezone),
                    "summary": row["id"],
                    "description": "\n".join(
                        [
                            f"🧑‍🧑‍🧒‍🧒 {stringify_guests(row['guests'])}",
                            f"💸 {row['amount']}",
                            "",
                            f"Réservé via {row['agent']['name']}"
                            if row["agent"]["name"] != ""
                            else "",
                        ]
                    ),
                    "is_rental": row["status"]["name"] != "PROPIETARIO",
                }
                for row in data
            ]

            self._total_earnings = sum(
                map(
                    float,
                    [row["amount"].replace(",", "").replace("€", "") for row in data],
                )
            )
            yearly_earnings = defaultdict(float)
            for row in data:
                year = datetime.strptime(row["bookingStart"], "%d %b %Y").year
                yearly_earnings[year] += float(
                    row["amount"].replace(",", "").replace("€", "")
                )

            self._yearly_earnings = dict(yearly_earnings)

            self._accommodations = await self._client.get_accommodations()
        except InvalidAuth as err:
            raise ConfigEntryAuthFailed(
                f"Credentials expired for {self.config_entry.entry_id}"
            ) from err
        except Exception as err:
            raise UpdateFailed(f"Error fetching booking data: {err}") from err

        return self._events

    def get_bookings(self):
        """Get all bookings, i.e. for guests and owners."""
        return self._events if self._events is not None else []

    def get_bookings_guests(self):
        """Filter bookings where `is_rental` is True."""
        return [event for event in self.get_bookings() if event.get("is_rental", False)]

    def get_bookings_owner(self):
        """Filter bookings where `is_rental` is False."""
        return [event for event in self.get_bookings() if not event.get("is_rental", False)]

    def get_total_earnings(self):
        """Get the total earnings sum, in euros."""
        return self._total_earnings

    def get_yearly_earnings(self):
        """Get the yearly earning map, in euros."""
        return self._yearly_earnings if self._yearly_earnings is not None else {}

    def get_accommodations(self):
        """Get the accommodations map."""
        return self._accommodations if self._accommodations is not None else []

def parse_date_with_time(date_str: str, hour: int, timezone: ZoneInfo) -> datetime:
    """Parse a date in the format '%d %b %Y', set the time, and add timezone info."""
    date = datetime.strptime(date_str, "%d %b %Y")
    return date.astimezone(timezone).replace(hour=hour)


def stringify_guests(guests: dict) -> str:
    """Stringify the guests information."""
    if guests is None:
        return "**Unknown**"

    num_adults = guests.get("numAdults", 0)
    num_children = guests.get("numChildren", 0)
    num_babies = guests.get("numBabies", 0)
    children_ages = [age for age in guests.get("childrenAges", []) if age > 0]

    parts = []

    total_people = num_adults + num_children + num_babies
    if total_people > 0:
        parts.append(f"{total_people} personnes")

    breakdown = []
    if num_adults > 0:
        breakdown.append(f"{num_adults} adultes")

    if num_children > 0:
        breakdown.append(f"{num_children} enfants")

    if num_babies > 0:
        breakdown.append(f"{num_babies} bébés")

    details = []
    if len(breakdown) > 0:
        details.append(", ".join(breakdown))
    if len(children_ages) > 0:
        ages = ", ".join(map(str, children_ages))
        details.append(f"(ages {ages} ans)")

    if len(details) > 0:
        parts.append(" ".join(details))

    return " – ".join(parts)
