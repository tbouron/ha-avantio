# Avantio for Home Assistant

Custom integration that reads your bookings from the [Avantio](https://app.avantio.pro) owner portal and exposes
them as calendars and sensors, one device per accommodation.

## Installation

1. HACS → Integrations → ⋮ → Custom repositories → add `https://github.com/tbouron/ha-avantio` (Integration).
2. Install **Avantio** and restart Home Assistant.
3. Settings → Devices & services → Add integration → **Avantio**.

## Configuration

| Field | Notes |
|---|---|
| Username / password | Your Avantio owner portal account. |

- **Re-authenticate** is offered automatically when Avantio rejects the credentials.

Data syncs once a day. A failed sync is retried every hour, and the last good data is kept on disk, so the
entities keep their values through Avantio outages and Home Assistant restarts.

## Entities

### Per accommodation

Entity ids use the Avantio accommodation id, e.g. `12345` → `sensor.avantio_12345_total_earnings`.

| Entity | State | Attributes |
|---|---|---|
| `sensor.avantio_<id>_total_earnings` | Sum of the amounts of all bookings (€) | `{year: 1234.56}` (float, €) by check-in year |
| `sensor.avantio_<id>_rental_days` | Total nights of rental bookings | `breakdown: {year: {month: nights}}` |
| `sensor.avantio_<id>_owner_days` | Total nights of owner bookings | `breakdown: {year: {month: nights}}` |
| `calendar.avantio_<id>_rental` | On during a rental stay | Event: booking id, guests, `💸 <amount>€`, `Réservé via <agent>` |
| `calendar.avantio_<id>_owner` | On during an owner stay | Event: booking id, guests |

Calendar events run from 17:00 on the check-in day to 10:00 on the check-out day. Bookings with the Avantio
status `PROPIETARIO` go to the owner calendar, all others to the rental calendar.

### Per account (diagnostic)

| Entity | State |
|---|---|
| `sensor.avantio_last_sync` | When the data shown was last fetched from Avantio |
| `binary_sensor.avantio_sync_problem` | On when the last sync attempt failed |

## New booking alerts

When a sync finds a rental booking that was not there before, the integration creates a persistent
notification ("🏠 New booking — From <start> to <end>", in English or French). Bookings made while Home
Assistant was down are notified on the next sync.

## Development

```bash
python3.14 -m venv .venv
.venv/bin/pip install -r requirements_test.txt
.venv/bin/python -m pytest
```

The tests cover the Avantio client and the data model and do not need Home Assistant installed.
