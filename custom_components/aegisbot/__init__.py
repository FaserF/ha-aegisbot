"""The AegisBot integration."""

from __future__ import annotations

import asyncio

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

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
    async def handle_send_message(call) -> None:
        """Handle the send_message service call."""
        group_id = call.data["group_id"]
        text = call.data["text"]
        thread_id = call.data.get("message_thread_id")
        await coordinator.api.async_send_message(group_id, text, thread_id)

    async def handle_ban_user(call) -> None:
        """Handle the ban_user service call."""
        group_id = call.data["group_id"]
        user_id = call.data["user_id"]
        duration = call.data.get("duration")
        reason = call.data.get("reason")
        await coordinator.api.async_ban_user(group_id, user_id, duration, reason)

    async def handle_unban_user(call) -> None:
        """Handle the unban_user service call."""
        group_id = call.data["group_id"]
        user_id = call.data["user_id"]
        await coordinator.api.async_unban_user(group_id, user_id)

    async def handle_mute_user(call) -> None:
        """Handle the mute_user service call."""
        group_id = call.data["group_id"]
        user_id = call.data["user_id"]
        duration = call.data["duration"]
        reason = call.data.get("reason")
        await coordinator.api.async_mute_user(group_id, user_id, duration, reason)

    async def handle_warn_user(call) -> None:
        """Handle the warn_user service call."""
        group_id = call.data["group_id"]
        user_id = call.data["user_id"]
        reason = call.data["reason"]
        await coordinator.api.async_warn_user(group_id, user_id, reason)

    hass.services.async_register(DOMAIN, "send_message", handle_send_message)
    hass.services.async_register(DOMAIN, "ban_user", handle_ban_user)
    hass.services.async_register(DOMAIN, "unban_user", handle_unban_user)
    hass.services.async_register(DOMAIN, "mute_user", handle_mute_user)
    hass.services.async_register(DOMAIN, "warn_user", handle_warn_user)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
