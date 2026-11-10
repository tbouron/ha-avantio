"""The data model the integration keeps, independent of Home Assistant.

Avantio's API responses are turned into a small snapshot of our own, which is
what gets cached on disk and what every entity reads from. Keeping this module
free of Home Assistant imports lets it be tested on its own.

Snapshot format (version 1):

    {
        "accommodations": [{"id": ..., "name": ...}],
        "bookings": [
            {
                "id": ...,
                "start": "YYYY-MM-DD",   # check-in day
                "end": "YYYY-MM-DD",     # check-out day
                "amount": 1234.5,        # euros
                "is_rental": true,       # false for owner stays
                "agent": "...",          # booking channel, may be ""
                "guests": {"adults": 2, "children": 1, "babies": 0, "children_ages": [7]},
                "accommodation_id": 12345   # null if the API did not say
            }
        ],
        "last_synced": "2026-11-10T09:00:00+00:00"
    }
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

CACHE_VERSION = 1

OWNER_STATUS = "PROPIETARIO"
API_DATE_FORMAT = "%d %b %Y"
CHECK_IN_HOUR = 17
CHECK_OUT_HOUR = 10


class InvalidResponse(Exception):
    """The API answered, but not with data that may replace the cache."""


def storage_key(entry_id: str) -> str:
    """Return the Home Assistant storage key holding an entry's snapshot."""
    return f"avantio.{entry_id}"


def parse_api_date(value: str) -> str:
    """Turn an API date such as '01 Jul 2026' into '2026-07-01'."""
    return datetime.strptime(value, API_DATE_FORMAT).date().isoformat()


def parse_amount(value: Any) -> float:
    """Turn an API amount such as '1,234.50€' into 1234.5."""
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = str(value).replace(",", "").replace("€", "").strip()
    return float(cleaned) if cleaned else 0.0


def normalize_guests(guests: dict | None) -> dict | None:
    """Keep only the guest counts the integration displays."""
    if guests is None:
        return None
    return {
        "adults": guests.get("numAdults", 0) or 0,
        "children": guests.get("numChildren", 0) or 0,
        "babies": guests.get("numBabies", 0) or 0,
        "children_ages": [age for age in guests.get("childrenAges") or [] if age > 0],
    }


def normalize_booking(row: dict) -> dict:
    """Turn one booking row from the API into the snapshot format."""
    return {
        "id": row["id"],
        "start": parse_api_date(row["bookingStart"]),
        "end": parse_api_date(row["bookingEnd"]),
        "amount": parse_amount(row["amount"]),
        "is_rental": row["status"]["name"] != OWNER_STATUS,
        "agent": (row.get("agent") or {}).get("name") or "",
        "guests": normalize_guests(row.get("guests")),
        "accommodation_id": row.get("propertyId"),
    }


def normalize_accommodation(row: dict) -> dict:
    """Turn one accommodation row from the API into the snapshot format."""
    return {"id": row["id"], "name": row.get("name")}


def build_snapshot(
    bookings: list | None,
    accommodations: list | None,
    synced_at: datetime,
    previous: dict | None = None,
) -> dict:
    """Build a snapshot from fresh API data, refusing data that looks broken.

    A successful response replaces the previous snapshot entirely. An empty
    list where the previous snapshot had entries is treated as a broken
    response rather than as everything having been deleted, so it cannot
    wipe the cache.
    """
    if not isinstance(bookings, list):
        raise InvalidResponse("No booking list in the response")
    if not isinstance(accommodations, list):
        raise InvalidResponse("No accommodation list in the response")
    if previous:
        if not bookings and previous.get("bookings"):
            raise InvalidResponse("Empty booking list, keeping the cached bookings")
        if not accommodations and previous.get("accommodations"):
            raise InvalidResponse(
                "Empty accommodation list, keeping the cached accommodations"
            )
    return {
        "accommodations": [normalize_accommodation(row) for row in accommodations],
        "bookings": [normalize_booking(row) for row in bookings],
        "last_synced": synced_at.isoformat(),
    }


def is_valid_snapshot(data: Any) -> bool:
    """Tell whether data loaded from disk looks like a snapshot."""
    return (
        isinstance(data, dict)
        and isinstance(data.get("bookings"), list)
        and isinstance(data.get("accommodations"), list)
    )


def last_synced(snapshot: dict) -> datetime | None:
    """Return when the snapshot was fetched."""
    value = snapshot.get("last_synced")
    return datetime.fromisoformat(value) if value else None


def bookings_for(bookings: list[dict], accommodation_id: Any) -> list[dict]:
    """Keep the bookings of one accommodation.

    A booking whose accommodation is unknown is kept for every accommodation,
    rather than silently disappearing.
    """
    return [
        booking
        for booking in bookings
        if booking.get("accommodation_id") in (None, accommodation_id)
    ]


def total_earnings(bookings: list[dict]) -> float:
    """Sum the amounts of all bookings, in euros."""
    return round(sum(booking["amount"] for booking in bookings), 2)


def yearly_earnings(bookings: list[dict]) -> dict[int, float]:
    """Sum the amounts per check-in year, in euros."""
    result: dict[int, float] = defaultdict(float)
    for booking in bookings:
        result[date.fromisoformat(booking["start"]).year] += booking["amount"]
    return {year: round(value, 2) for year, value in sorted(result.items())}


def booked_days_by_month(
    bookings: list[dict], for_rental: bool
) -> dict[int, dict[int, int]]:
    """Count booked nights per year and month, for rentals or owner stays."""
    counts: dict[tuple[int, int], int] = defaultdict(int)
    for booking in bookings:
        if booking["is_rental"] is not for_rental:
            continue
        current = date.fromisoformat(booking["start"])
        end = date.fromisoformat(booking["end"])
        while current < end:
            counts[(current.year, current.month)] += 1
            current += timedelta(days=1)
    breakdown: dict[int, dict[int, int]] = {}
    for (year, month), days in sorted(counts.items()):
        breakdown.setdefault(year, {})[month] = days
    return breakdown


def describe_guests(guests: dict | None) -> str:
    """Describe the guests of a booking, in French."""
    if guests is None:
        return "**Unknown**"

    adults = guests.get("adults", 0)
    children = guests.get("children", 0)
    babies = guests.get("babies", 0)
    children_ages = guests.get("children_ages", [])

    parts = []
    total_people = adults + children + babies
    if total_people > 0:
        parts.append(f"{total_people} personnes")

    breakdown = []
    if adults > 0:
        breakdown.append(f"{adults} adultes")
    if children > 0:
        breakdown.append(f"{children} enfants")
    if babies > 0:
        breakdown.append(f"{babies} bébés")

    details = []
    if breakdown:
        details.append(", ".join(breakdown))
    if children_ages:
        details.append(f"(ages {', '.join(map(str, children_ages))} ans)")
    if details:
        parts.append(" ".join(details))

    return " – ".join(parts)


def describe_booking(booking: dict) -> str:
    """Build the calendar event description of a booking."""
    return "\n".join(
        [
            f"🧑‍🧑‍🧒‍🧒 {describe_guests(booking['guests'])}",
            f"💸 {booking['amount']:,.2f}€" if booking["is_rental"] else "",
            "",
            f"Réservé via {booking['agent']}" if booking["agent"] else "",
        ]
    )


def booking_events(bookings: list[dict], timezone: ZoneInfo) -> list[dict]:
    """Turn bookings into calendar events, in the given time zone."""
    return [
        {
            "uid": str(booking["id"]),
            "start": datetime.combine(
                date.fromisoformat(booking["start"]), time(CHECK_IN_HOUR), timezone
            ),
            "end": datetime.combine(
                date.fromisoformat(booking["end"]), time(CHECK_OUT_HOUR), timezone
            ),
            "summary": str(booking["id"]),
            "description": describe_booking(booking),
            "is_rental": booking["is_rental"],
            "accommodation_id": booking.get("accommodation_id"),
        }
        for booking in bookings
    ]
