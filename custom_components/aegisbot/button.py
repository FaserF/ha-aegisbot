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


class AegisBotSyncButton(CoordinatorEntity[AegisBotDataCoordinator], ButtonEntity):
    """Representation of an AegisBot sync button."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AegisBotDataCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sync button."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_sync_filters"
        self._attr_translation_key = "sync_filters"
        self._attr_icon = "mdi:sync"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="AegisBot System",
            manufacturer="AegisBot",
            entry_type=DeviceEntryType.SERVICE,
        )

    async def async_press(self) -> None:
        """Press the button."""
        await self.coordinator.api.async_sync_filters()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up AegisBot buttons from a config entry."""
    coordinator: AegisBotDataCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([AegisBotSyncButton(coordinator, entry)])
