"""Binary sensor platform for AegisBot integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AegisBotDataCoordinator


@dataclass(frozen=True, kw_only=True)
class AegisBotBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describe an AegisBot binary sensor."""

    is_on_fn: Callable[[dict[str, Any]], bool]
    attributes_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


class AegisBotBinarySensorEntity(
    CoordinatorEntity[AegisBotDataCoordinator], BinarySensorEntity
):
    """Representation of an AegisBot binary sensor."""

    entity_description: AegisBotBinarySensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AegisBotDataCoordinator,
        entry: ConfigEntry,
        description: AegisBotBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_translation_key = description.key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="AegisBot System",
            manufacturer="AegisBot",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        return self.entity_description.is_on_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        if self.entity_description.attributes_fn:
            return self.entity_description.attributes_fn(self.coordinator.data)
        return None


class AegisBotGroupBinarySensorEntity(
    CoordinatorEntity[AegisBotDataCoordinator], BinarySensorEntity
):
    """Representation of an AegisBot group binary sensor."""

    entity_description: AegisBotBinarySensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AegisBotDataCoordinator,
        entry: ConfigEntry,
        group_id: int,
        description: AegisBotBinarySensorEntityDescription,
    ) -> None:
        """Initialize the group binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._group_id = group_id
        self._attr_unique_id = f"{entry.entry_id}_{group_id}_{description.key}"
        self._attr_translation_key = description.key

        group_data = coordinator.data["groups"].get(group_id, {})
        group_title = group_data.get("title", f"Group {group_id}")

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_group_{group_id}")},
            name=f"Group: {group_title}",
            manufacturer="AegisBot",
            model="Telegram Group",
            via_device=(DOMAIN, entry.entry_id),
        )

    @property
    def is_on(self) -> bool:
        """Return true if the group is active."""
        group_data = self.coordinator.data["groups"].get(self._group_id, {})
        return self.entity_description.is_on_fn(group_data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        if self.entity_description.attributes_fn:
            group_data = self.coordinator.data["groups"].get(self._group_id, {})
            return self.entity_description.attributes_fn(group_data)
        return None


GLOBAL_BINARY_SENSORS: tuple[AegisBotBinarySensorEntityDescription, ...] = (
    AegisBotBinarySensorEntityDescription(
        key="status",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda data: data.get("health", {}).get("status") == "healthy",
        attributes_fn=lambda data: {
            "version": data.get("health", {}).get("version"),
            "environment": data.get("health", {}).get("environment"),
        },
    ),
    AegisBotBinarySensorEntityDescription(
        key="raid_active",
        device_class=BinarySensorDeviceClass.SAFETY,
        is_on_fn=lambda data: (
            data.get("intel", {}).get("stats", {}).get("active_raids", 0) > 0
        ),
        attributes_fn=lambda data: {
            "raids": data.get("intel", {}).get("stats", {}).get("active_raids", 0),
        },
    ),
    AegisBotBinarySensorEntityDescription(
        key="database_health",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        is_on_fn=lambda data: (
            data.get("health", {}).get("infrastructure", {}).get("database")
            != "healthy"
        ),
    ),
    AegisBotBinarySensorEntityDescription(
        key="whatsapp_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        is_on_fn=lambda data: (
            data.get("whatsapp", {}).get("status")
            in ("connected", "ready", "authenticated")
            or data.get("whatsapp", {}).get("connected") is True
        ),
        attributes_fn=lambda data: {
            "bridge_status": data.get("whatsapp", {}).get("status"),
            "phone_number": data.get("whatsapp", {}).get("phone_number"),
            "session_active": data.get("whatsapp", {}).get("session_active"),
        },
    ),
)

GROUP_BINARY_SENSORS: tuple[AegisBotBinarySensorEntityDescription, ...] = (
    AegisBotBinarySensorEntityDescription(
        key="group_active",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        is_on_fn=lambda group: bool(
            group.get("platform") or group.get("is_active", True)
        ),
        attributes_fn=lambda group: {
            "platform": group.get("platform"),
            "type": group.get("type"),
        },
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up AegisBot binary sensors from a config entry."""
    coordinator: AegisBotDataCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[BinarySensorEntity] = []

    # Global Binary Sensors
    for description in GLOBAL_BINARY_SENSORS:
        entities.append(AegisBotBinarySensorEntity(coordinator, entry, description))

    async_add_entities(entities)

    # Dynamic Group Binary Sensors
    known_groups: set[int] = set()

    @callback
    def _async_add_group_binary_sensors() -> None:
        """Add binary sensors for new groups."""
        new_entities: list[BinarySensorEntity] = []
        for group_id in coordinator.data["groups"]:
            if group_id not in known_groups:
                for description in GROUP_BINARY_SENSORS:
                    new_entities.append(
                        AegisBotGroupBinarySensorEntity(
                            coordinator, entry, group_id, description
                        )
                    )
                known_groups.add(group_id)
        if new_entities:
            async_add_entities(new_entities)

    entry.async_on_unload(
        coordinator.async_add_listener(_async_add_group_binary_sensors)
    )
    _async_add_group_binary_sensors()
