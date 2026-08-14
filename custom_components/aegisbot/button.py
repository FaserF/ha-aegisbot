"""Button platform for AegisBot integration."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AegisBotDataCoordinator


class AegisBotButtonEntity(CoordinatorEntity[AegisBotDataCoordinator], ButtonEntity):
    """Base class for AegisBot buttons."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AegisBotDataCoordinator,
        entry: ConfigEntry,
        key: str,
        icon: str,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_icon = icon
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="AegisBot System",
            manufacturer="AegisBot",
            entry_type=DeviceEntryType.SERVICE,
        )


class AegisBotSyncButton(AegisBotButtonEntity):
    """Representation of an AegisBot sync button."""

    def __init__(
        self,
        coordinator: AegisBotDataCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sync button."""
        super().__init__(coordinator, entry, "sync_filters", "mdi:sync")

    async def async_press(self) -> None:
        """Press the button."""
        await self.coordinator.api.async_sync_filters()


class AegisBotVacuumButton(AegisBotButtonEntity):
    """Representation of an AegisBot database vacuum button."""

    def __init__(
        self,
        coordinator: AegisBotDataCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the vacuum button."""
        super().__init__(coordinator, entry, "maintenance_vacuum", "mdi:database-sync")

    async def async_press(self) -> None:
        """Press the button."""
        await self.coordinator.api.async_maintenance_vacuum()
        await self.coordinator.async_request_refresh()


class AegisBotLiveTestButton(AegisBotButtonEntity):
    """Representation of an AegisBot maintenance live-test button."""

    def __init__(
        self,
        coordinator: AegisBotDataCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the live test button."""
        super().__init__(coordinator, entry, "maintenance_live_test", "mdi:test-tube")

    async def async_press(self) -> None:
        """Press the button."""
        await self.coordinator.api.async_maintenance_live_test()
        await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up AegisBot buttons from a config entry."""
    coordinator: AegisBotDataCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            AegisBotSyncButton(coordinator, entry),
            AegisBotVacuumButton(coordinator, entry),
            AegisBotLiveTestButton(coordinator, entry),
        ]
    )
