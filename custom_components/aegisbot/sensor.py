"""Sensor platform for AegisBot integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AegisBotDataCoordinator


@dataclass(frozen=True, kw_only=True)
class AegisBotSensorEntityDescription(SensorEntityDescription):
    """Describe an AegisBot sensor."""

    value_fn: Callable[[dict[str, Any]], StateType]
    attributes_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


class AegisBotSensorEntity(CoordinatorEntity[AegisBotDataCoordinator], SensorEntity):
    """Representation of an AegisBot sensor."""

    entity_description: AegisBotSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AegisBotDataCoordinator,
        entry: ConfigEntry,
        description: AegisBotSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
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
    def native_value(self) -> StateType:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        if self.entity_description.attributes_fn:
            return self.entity_description.attributes_fn(self.coordinator.data)
        return None


class AegisBotGroupSensorEntity(
    CoordinatorEntity[AegisBotDataCoordinator], SensorEntity
):
    """Representation of an AegisBot group sensor."""

    entity_description: AegisBotSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AegisBotDataCoordinator,
        entry: ConfigEntry,
        group_id: int,
        description: AegisBotSensorEntityDescription,
    ) -> None:
        """Initialize the group sensor."""
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
    def native_value(self) -> StateType:
        """Return the sensor value."""
        group_data = self.coordinator.data["groups"].get(self._group_id, {})
        return self.entity_description.value_fn(group_data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        if self.entity_description.attributes_fn:
            group_data = self.coordinator.data["groups"].get(self._group_id, {})
            return self.entity_description.attributes_fn(group_data)
        return None


GLOBAL_SENSORS: tuple[AegisBotSensorEntityDescription, ...] = (
    AegisBotSensorEntityDescription(
        key="protected_groups",
        icon="mdi:shield-home",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("stats", {}).get("protected_groups", 0),
        attributes_fn=lambda data: {
            "total_users": data.get("stats", {}).get("total_users"),
            "total_groups": len(data.get("groups", {})),
        },
    ),
    AegisBotSensorEntityDescription(
        key="active_warnings",
        icon="mdi:alert",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("stats", {}).get("active_warnings", 0),
    ),
    AegisBotSensorEntityDescription(
        key="malicious_links",
        icon="mdi:link-off",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_registry_enabled_default=False,
        value_fn=lambda data: data.get("stats", {}).get("malicious_links", 0),
    ),
    AegisBotSensorEntityDescription(
        key="active_signals",
        icon="mdi:wifi-marker",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: (
            data.get("intel", {}).get("stats", {}).get("total_alerts", 0)
        ),
        attributes_fn=lambda data: {
            "raids": data.get("intel", {}).get("stats", {}).get("active_raids", 0),
            "threat_level": data.get("intel", {}).get("stats", {}).get("threat_level"),
        },
    ),
    AegisBotSensorEntityDescription(
        key="fed_sync_points",
        icon="mdi:webhook",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: (
            data.get("intel", {}).get("stats", {}).get("sync_points", 0)
        ),
    ),
    AegisBotSensorEntityDescription(
        key="ai_faq_count",
        icon="mdi:robot",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_registry_enabled_default=False,
        value_fn=lambda data: data.get("stats", {}).get("ai_faq_count", 0),
    ),
    AegisBotSensorEntityDescription(
        key="db_size_mb",
        icon="mdi:database",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="MB",
        entity_registry_enabled_default=False,
        value_fn=lambda data: (
            round(data.get("maintenance", {}).get("db_size_bytes", 0) / (1024 * 1024), 2)
            if data.get("maintenance", {}).get("db_size_bytes") is not None
            else data.get("maintenance", {}).get("db_size_mb", 0)
        ),
        attributes_fn=lambda data: {
            "last_vacuum": data.get("maintenance", {}).get("last_vacuum"),
            "table_count": data.get("maintenance", {}).get("table_count"),
            "total_rows": data.get("maintenance", {}).get("total_rows"),
        },
    ),
    AegisBotSensorEntityDescription(
        key="event_backlog",
        icon="mdi:tray-full",
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda data: data.get("maintenance", {}).get("event_backlog", 0),
    ),
)

GROUP_SENSORS: tuple[AegisBotSensorEntityDescription, ...] = (
    AegisBotSensorEntityDescription(
        key="health_score",
        icon="mdi:heart-pulse",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda group: group.get("health_score", 0),
        attributes_fn=lambda group: {
            "platform": group.get("platform"),
            "member_count": group.get("member_count"),
            "security_preset": group.get("preset"),
        },
    ),
    AegisBotSensorEntityDescription(
        key="events_7d",
        icon="mdi:history",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda group: group.get("events_7d", 0),
    ),
    AegisBotSensorEntityDescription(
        key="warnings",
        icon="mdi:alert-circle",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda group: group.get("warnings", 0),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up AegisBot sensors from a config entry."""
    coordinator: AegisBotDataCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = []

    # Global System Sensors
    for description in GLOBAL_SENSORS:
        entities.append(AegisBotSensorEntity(coordinator, entry, description))

    async_add_entities(entities)

    # Dynamic Group Sensors
    known_groups: set[int] = set()

    @callback
    def _async_add_group_sensors() -> None:
        """Add sensors for new groups."""
        new_entities: list[SensorEntity] = []
        for group_id in coordinator.data["groups"]:
            if group_id not in known_groups:
                for description in GROUP_SENSORS:
                    new_entities.append(
                        AegisBotGroupSensorEntity(
                            coordinator, entry, group_id, description
                        )
                    )
                known_groups.add(group_id)
        if new_entities:
            async_add_entities(new_entities)

    entry.async_on_unload(coordinator.async_add_listener(_async_add_group_sensors))
    _async_add_group_sensors()
