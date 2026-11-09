"""Tests for the snapshot model: conversion, the cache guard and derived values."""

import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from avantio_model import (
    InvalidResponse,
    booked_days_by_month,
    booking_events,
    bookings_for,
    build_snapshot,
    describe_booking,
    is_valid_snapshot,
    last_synced,
    parse_amount,
    total_earnings,
    yearly_earnings,
)

SYNCED_AT = datetime(2026, 11, 10, 9, 0, tzinfo=timezone.utc)
PARIS = ZoneInfo("Europe/Paris")


def booking_row(
    booking_id="B1",
    start="28 Jun 2026",
    end="03 Jul 2026",
    amount="1,234.50€",
    status="CONFIRMADA",
    agent="Airbnb",
    guests=None,
    property_id=1,
):
    """A booking row shaped like Avantio's fetchOwnerBookings response."""
    return {
        "id": booking_id,
        "propertyId": property_id,
        "bookingStart": start,
        "bookingEnd": end,
        "amount": amount,
        "status": {"name": status},
        "agent": {"name": agent},
        "guests": guests
        if guests is not None
        else {"numAdults": 2, "numChildren": 1, "numBabies": 0, "childrenAges": [7, 0]},
    }


ACCOMMODATIONS = [{"id": 1, "name": "Flat", "unused": "dropped"}]


def snapshot(*rows):
    return build_snapshot(list(rows), ACCOMMODATIONS, SYNCED_AT)


def test_build_snapshot_keeps_only_the_fields_used():
    result = snapshot(booking_row())

    assert result == {
        "accommodations": [{"id": 1, "name": "Flat"}],
        "bookings": [
            {
                "id": "B1",
                "start": "2026-06-28",
                "end": "2026-07-03",
                "amount": 1234.5,
                "is_rental": True,
                "agent": "Airbnb",
                "guests": {"adults": 2, "children": 1, "babies": 0, "children_ages": [7]},
                "accommodation_id": 1,
            }
        ],
        "last_synced": "2026-11-10T09:00:00+00:00",
    }


def test_snapshot_survives_a_json_round_trip():
    result = snapshot(booking_row(), booking_row("B2", status="PROPIETARIO", agent=""))

    reloaded = json.loads(json.dumps(result))

    assert reloaded == result
    assert is_valid_snapshot(reloaded)
    assert last_synced(reloaded) == SYNCED_AT


def test_owner_stays_are_not_rentals():
    result = snapshot(booking_row(status="PROPIETARIO"))

    assert result["bookings"][0]["is_rental"] is False


def test_missing_guests_and_agent_are_tolerated():
    row = booking_row()
    row["guests"] = None
    row["agent"] = None

    booking = snapshot(row)["bookings"][0]

    assert booking["guests"] is None
    assert booking["agent"] == ""


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("1,234.50€", 1234.5), ("€ 4,549.30", 4549.3), ("\u20ac 0.00", 0.0), ("0€", 0.0), ("", 0.0), ("  99 € ", 99.0), (12, 12.0)],
)
def test_parse_amount(raw, expected):
    assert parse_amount(raw) == expected


@pytest.mark.parametrize(
    ("bookings", "accommodations"),
    [(None, ACCOMMODATIONS), ([booking_row()], None), ("oops", ACCOMMODATIONS)],
)
def test_a_missing_list_is_rejected(bookings, accommodations):
    with pytest.raises(InvalidResponse):
        build_snapshot(bookings, accommodations, SYNCED_AT)


def test_an_empty_booking_list_cannot_wipe_cached_bookings():
    previous = snapshot(booking_row())

    with pytest.raises(InvalidResponse):
        build_snapshot([], ACCOMMODATIONS, SYNCED_AT, previous=previous)


def test_an_empty_accommodation_list_cannot_wipe_cached_accommodations():
    previous = snapshot(booking_row())

    with pytest.raises(InvalidResponse):
        build_snapshot([booking_row()], [], SYNCED_AT, previous=previous)


def test_empty_lists_are_accepted_without_a_cache():
    result = build_snapshot([], [], SYNCED_AT)

    assert result["bookings"] == []
    assert result["accommodations"] == []


def test_empty_lists_are_accepted_when_the_cache_is_empty_too():
    previous = build_snapshot([], [], SYNCED_AT)

    result = build_snapshot([], [], SYNCED_AT, previous=previous)

    assert result["bookings"] == []


def test_a_fresh_response_replaces_the_cache():
    previous = snapshot(booking_row("OLD"))

    result = build_snapshot([booking_row("NEW")], ACCOMMODATIONS, SYNCED_AT, previous=previous)

    assert [b["id"] for b in result["bookings"]] == ["NEW"]


@pytest.mark.parametrize("value", [None, [], {}, {"bookings": []}, {"bookings": [], "accommodations": "x"}])
def test_unreadable_cache_is_rejected(value):
    assert not is_valid_snapshot(value)


def test_bookings_are_split_by_accommodation():
    unknown = booking_row("U")
    del unknown["propertyId"]
    bookings = snapshot(
        booking_row("A", property_id=1), booking_row("B", property_id=2), unknown
    )["bookings"]

    assert [b["id"] for b in bookings_for(bookings, 1)] == ["A", "U"]
    assert [b["id"] for b in bookings_for(bookings, 2)] == ["B", "U"]


def test_earnings_total_and_per_check_in_year():
    bookings = snapshot(
        booking_row("A", start="30 Dec 2025", end="02 Jan 2026", amount="100.10€"),
        booking_row("B", amount="1,000.20€"),
        booking_row("C", amount="0€", status="PROPIETARIO"),
    )["bookings"]

    assert total_earnings(bookings) == 1100.3
    assert yearly_earnings(bookings) == {2025: 100.1, 2026: 1000.2}


def test_booked_days_split_by_month_and_kind():
    bookings = snapshot(
        booking_row("A", start="28 Jun 2026", end="03 Jul 2026"),
        booking_row("B", start="30 Dec 2025", end="02 Jan 2026", status="PROPIETARIO"),
    )["bookings"]

    assert booked_days_by_month(bookings, for_rental=True) == {2026: {6: 3, 7: 2}}
    assert booked_days_by_month(bookings, for_rental=False) == {2025: {12: 2}, 2026: {1: 1}}


def test_events_use_check_in_and_check_out_hours_in_the_local_time_zone():
    events = booking_events(snapshot(booking_row())["bookings"], PARIS)

    assert events[0]["uid"] == "B1"
    assert events[0]["start"] == datetime(2026, 6, 28, 17, 0, tzinfo=PARIS)
    assert events[0]["end"] == datetime(2026, 7, 3, 10, 0, tzinfo=PARIS)
    assert events[0]["is_rental"] is True
    assert events[0]["accommodation_id"] == 1


def test_rental_description():
    booking = snapshot(booking_row())["bookings"][0]

    assert describe_booking(booking).split("\n") == [
        "🧑‍🧑‍🧒‍🧒 3 personnes – 2 adultes, 1 enfants (ages 7 ans)",
        "💸 1,234.50€",
        "",
        "Réservé via Airbnb",
    ]


def test_owner_description_hides_the_amount():
    booking = snapshot(booking_row(status="PROPIETARIO", agent=""))["bookings"][0]

    assert describe_booking(booking).split("\n") == [
        "🧑‍🧑‍🧒‍🧒 3 personnes – 2 adultes, 1 enfants (ages 7 ans)",
        "",
        "",
        "",
    ]
