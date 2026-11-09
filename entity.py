"""Base entity and devices for the Avantio integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AvantioCoordinator

MANUFACTURER = "Avantio"
CONFIGURATION_URL = "https://app.avantio.pro"


def account_device_info(entry: ConfigEntry) -> DeviceInfo:
    """The device of an Avantio account, holding the sync status entities."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer=MANUFACTURER,
        model="Owner account",
        entry_type=DeviceEntryType.SERVICE,
        configuration_url=CONFIGURATION_URL,
    )


def accommodation_device_info(entry: ConfigEntry, accommodation: dict) -> DeviceInfo:
    """The device of one accommodation, holding its sensors and calendars."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"accommodation_{accommodation['id']}")},
        name=accommodation.get("name") or f"Accommodation {accommodation['id']}",
        manufacturer=MANUFACTURER,
        model="Accommodation",
        via_device=(DOMAIN, entry.entry_id),
        configuration_url=CONFIGURATION_URL,
    )


class AvantioEntity(CoordinatorEntity[AvantioCoordinator]):
    """An entity of one accommodation, showing Avantio data, cached or fresh.

    Unlike a plain CoordinatorEntity, it stays available when a sync fails,
    as long as there is data to show. The sync status entities report how
    fresh that data is.
    """

    _attr_has_entity_name = True

    def __init__(self, coordinator: AvantioCoordinator, accommodation: dict) -> None:
        """Attach the entity to its accommodation's device."""
        super().__init__(coordinator)
        self._accommodation_id = accommodation["id"]
        self._attr_device_info = accommodation_device_info(
            coordinator.config_entry, accommodation
        )

    @property
    def available(self) -> bool:
        """Return whether there is data to show."""
        return self.coordinator.has_data


class AvantioSyncEntity(CoordinatorEntity[AvantioCoordinator]):
    """A diagnostic entity reporting on the sync of the whole account."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: AvantioCoordinator) -> None:
        """Attach the entity to the account's device."""
        super().__init__(coordinator)
        self._attr_device_info = account_device_info(coordinator.config_entry)

    @property
    def available(self) -> bool:
        """Always available: it reports on the sync itself."""
        return True
