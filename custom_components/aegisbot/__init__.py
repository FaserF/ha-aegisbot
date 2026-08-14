"""The AegisBot integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN
from .coordinator import AegisBotDataCoordinator

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.BUTTON,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up AegisBot from a config entry."""
    coordinator = AegisBotDataCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register Services
    async def handle_send_message(call: ServiceCall) -> None:
        """Handle the send_message service call."""
        group_id = call.data["group_id"]
        text = call.data["text"]
        thread_id = call.data.get("message_thread_id")
        await coordinator.api.async_send_message(group_id, text, thread_id)

    async def handle_ban_user(call: ServiceCall) -> None:
        """Handle the ban_user service call."""
        group_id = call.data["group_id"]
        user_id = call.data["user_id"]
        duration = call.data.get("duration")
        reason = call.data.get("reason")
        await coordinator.api.async_ban_user(group_id, user_id, duration, reason)

    async def handle_unban_user(call: ServiceCall) -> None:
        """Handle the unban_user service call."""
        group_id = call.data["group_id"]
        user_id = call.data["user_id"]
        await coordinator.api.async_unban_user(group_id, user_id)

    async def handle_mute_user(call: ServiceCall) -> None:
        """Handle the mute_user service call."""
        group_id = call.data["group_id"]
        user_id = call.data["user_id"]
        duration = call.data["duration"]
        reason = call.data.get("reason")
        await coordinator.api.async_mute_user(group_id, user_id, duration, reason)

    async def handle_warn_user(call: ServiceCall) -> None:
        """Handle the warn_user service call."""
        group_id = call.data["group_id"]
        user_id = call.data["user_id"]
        reason = call.data["reason"]
        await coordinator.api.async_warn_user(group_id, user_id, reason)

    async def handle_broadcast(call: ServiceCall) -> None:
        """Handle the broadcast service call."""
        text = call.data["text"]
        group_ids = call.data.get("group_ids")
        platform = call.data.get("platform")
        await coordinator.api.async_broadcast(
            text=text, group_ids=group_ids, platform=platform
        )

    async def handle_adjust_reputation(call: ServiceCall) -> None:
        """Handle the adjust_reputation service call."""
        user_id = call.data["user_id"]
        delta = call.data["delta"]
        reason = call.data.get("reason")
        group_id = call.data.get("group_id")
        await coordinator.api.async_adjust_reputation(
            user_id=user_id, delta=delta, reason=reason, group_id=group_id
        )

    async def handle_apply_preset(call: ServiceCall) -> None:
        """Handle the apply_preset service call."""
        group_id = call.data["group_id"]
        preset_name = call.data["preset_name"]
        await coordinator.api.async_apply_preset(
            group_id=group_id, preset_name=preset_name
        )
        await coordinator.async_request_refresh()

    async def handle_maintenance_cleanup(call: ServiceCall) -> None:
        """Handle the maintenance_cleanup service call."""
        days = call.data.get("days")
        await coordinator.api.async_maintenance_cleanup(days=days)
        await coordinator.async_request_refresh()

    async def handle_maintenance_purge(call: ServiceCall) -> None:
        """Handle the maintenance_purge service call."""
        group_id = call.data["group_id"]
        await coordinator.api.async_maintenance_purge(group_id=group_id)
        await coordinator.async_request_refresh()

    async def handle_mark_notifications_read(call: ServiceCall) -> None:
        """Handle the mark_notifications_read service call."""
        notification_ids = call.data.get("notification_ids")
        await coordinator.api.async_mark_notifications_read(
            notification_ids=notification_ids
        )

    async def handle_whatsapp_action(call: ServiceCall) -> None:
        """Handle the whatsapp_action service call."""
        action = call.data["action"]
        data = call.data.get("data")
        await coordinator.api.async_whatsapp_action(action=action, data=data)
        await coordinator.async_request_refresh()

    hass.services.async_register(DOMAIN, "send_message", handle_send_message)
    hass.services.async_register(DOMAIN, "ban_user", handle_ban_user)
    hass.services.async_register(DOMAIN, "unban_user", handle_unban_user)
    hass.services.async_register(DOMAIN, "mute_user", handle_mute_user)
    hass.services.async_register(DOMAIN, "warn_user", handle_warn_user)
    hass.services.async_register(DOMAIN, "broadcast", handle_broadcast)
    hass.services.async_register(DOMAIN, "adjust_reputation", handle_adjust_reputation)
    hass.services.async_register(DOMAIN, "apply_preset", handle_apply_preset)
    hass.services.async_register(
        DOMAIN, "maintenance_cleanup", handle_maintenance_cleanup
    )
    hass.services.async_register(DOMAIN, "maintenance_purge", handle_maintenance_purge)
    hass.services.async_register(
        DOMAIN, "mark_notifications_read", handle_mark_notifications_read
    )
    hass.services.async_register(DOMAIN, "whatsapp_action", handle_whatsapp_action)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
