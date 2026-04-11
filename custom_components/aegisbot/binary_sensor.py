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


GLOBAL_BINARY_SENSORS: tuple[AegisBotBinarySensorEntityDescription, ...] = (
    AegisBotBinarySensorEntityDescription(
        key="status",
        name="Global Status",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda data: data["health"].get("status") == "healthy",
    ),
    AegisBotBinarySensorEntityDescription(
        key="raid_active",
        name="Active Raid Detected",
        device_class=BinarySensorDeviceClass.SAFETY,
        is_on_fn=lambda data: data["intel"]["stats"].get("active_raids", 0) > 0,
    ),
    AegisBotBinarySensorEntityDescription(
        key="database_health",
        name="Database Status",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        is_on_fn=lambda data: (
            data["health"].get("infrastructure", {}).get("database") != "healthy"
        ),
    ),
)

GROUP_BINARY_SENSORS: tuple[AegisBotBinarySensorEntityDescription, ...] = (
    AegisBotBinarySensorEntityDescription(
        key="group_active",
        name="Group Active",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        is_on_fn=lambda group: group.get("platform") == "telegram",  # Example logic
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
