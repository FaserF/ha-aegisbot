"""Switch platform for AegisBot integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AegisBotDataCoordinator

LOCK_TYPES = [
    "media",
    "links",
    "rtl",
    "stickers",
    "gifs",
    "documents",
    "voice",
    "video_notes",
    "contacts",
    "location",
    "games",
    "polls",
    "inline",
    "buttons",
    "forwards",
    "commands",
    "emails",
    "usernames",
    "markdown",
]


class AegisBotGroupLockSwitch(CoordinatorEntity[AegisBotDataCoordinator], SwitchEntity):
    """Representation of an AegisBot group lock switch."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AegisBotDataCoordinator,
        entry: ConfigEntry,
        group_id: int,
        lock_type: str,
    ) -> None:
        """Initialize the group lock switch."""
        super().__init__(coordinator)
        self._group_id = group_id
        self._lock_type = lock_type
        self._attr_unique_id = f"{entry.entry_id}_{group_id}_lock_{lock_type}"
        self._attr_translation_key = f"lock_{lock_type}"

        group_data = coordinator.data["groups"].get(group_id, {})
        group_title = group_data.get("title", f"Group {group_id}")

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_group_{group_id}")},
            name=f"Group: {group_title}",
            manufacturer="AegisBot",
            model="Telegram Group",
            via_device=(DOMAIN, entry.entry_id),
        )

        # Disable niche locks by default to keep HA UI clean
        if lock_type not in ["media", "links"]:
            self._attr_entity_registry_enabled_default = False

    @property
    def name(self) -> str:
        """Return the name of the switch."""
        return f"Lock {self._lock_type.capitalize()}"

    @property
    def is_on(self) -> bool:
        """Return true if the lock is active."""
        locks = self.coordinator.data["locks"].get(self._group_id, {})
        return locks.get(self._lock_type, False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the lock on."""
        await self.coordinator.api.async_toggle_lock(
            self._group_id, self._lock_type, True
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the lock off."""
        await self.coordinator.api.async_toggle_lock(
            self._group_id, self._lock_type, False
        )
        await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up AegisBot switches from a config entry."""
    coordinator: AegisBotDataCoordinator = hass.data[DOMAIN][entry.entry_id]

    known_groups: set[int] = set()

    @callback
    def _async_add_group_switches() -> None:
        """Add switches for new groups."""
        new_entities: list[SwitchEntity] = []
        for group_id in coordinator.data["groups"]:
            if group_id not in known_groups:
                for lock_type in LOCK_TYPES:
                    new_entities.append(
                        AegisBotGroupLockSwitch(coordinator, entry, group_id, lock_type)
                    )
                known_groups.add(group_id)
        if new_entities:
            async_add_entities(new_entities)

    entry.async_on_unload(coordinator.async_add_listener(_async_add_group_switches))
    _async_add_group_switches()
