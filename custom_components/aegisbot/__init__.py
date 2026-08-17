"""The AegisBot integration."""

from __future__ import annotations

import asyncio
import logging
from aiohttp import web
from homeassistant.components import webhook
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.discovery import async_load_platform

from .const import (
    CONF_ALLOWED_CHAT_IDS,
    CONF_CHAT_ID,
    CONF_WEBHOOK_ID,
    DOMAIN,
    EVENT_AEGISBOT_CALLBACK,
    EVENT_AEGISBOT_COMMAND,
    EVENT_AEGISBOT_POLL_ANSWER,
    EVENT_AEGISBOT_POLL_RESULT,
    EVENT_AEGISBOT_POLL_UPDATE,
    EVENT_AEGISBOT_TEXT,
    LOGGER,
)
from .coordinator import AegisBotDataCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.BUTTON,
    Platform.NOTIFY,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up AegisBot from a config entry."""
    coordinator = AegisBotDataCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Allowed Chat IDs resolution
    allowed_chat_ids = entry.options.get(
        CONF_ALLOWED_CHAT_IDS, entry.data.get(CONF_ALLOWED_CHAT_IDS, [])
    )
    if isinstance(allowed_chat_ids, str):
        allowed_chat_ids = [x.strip() for x in allowed_chat_ids.split(",") if x.strip()]

    # Load Notify platform
    discovery_info = {
        "entry_id": entry.entry_id,
        CONF_ALLOWED_CHAT_IDS: allowed_chat_ids,
    }
    hass.async_create_task(
        async_load_platform(hass, Platform.NOTIFY, DOMAIN, discovery_info, {})
    )

    # Webhook Setup for Real-time AegisBot Events
    webhook_id = entry.data.get(CONF_WEBHOOK_ID) or f"{DOMAIN}_{entry.entry_id}"

    async def handle_webhook(
        hass: HomeAssistant, webhook_id: str, request: web.Request
    ) -> web.Response:
        """Handle incoming webhook requests from AegisBot."""
        try:
            payload = await request.json()
        except Exception:
            return web.Response(status=400, text="Invalid JSON")

        event_type = payload.get("event_type")
        event_data = payload.get("event_data") or payload.get("data") or payload

        if event_type:
            hass.bus.async_fire(event_type, event_data)
        else:
            # Fallback event
            hass.bus.async_fire(EVENT_AEGISBOT_TEXT, event_data)

        return web.Response(status=200, text="OK")

    try:
        webhook.async_register(
            hass,
            DOMAIN,
            "AegisBot Webhook",
            webhook_id,
            handle_webhook,
        )
    except Exception as ex:
        _LOGGER.debug("Webhook registration notice: %s", ex)

    # Sync Webhook & Allowed Chats to AegisBot in background
    async def _sync_with_aegisbot() -> None:
        try:
            # Get HA External/Internal URL if available
            ha_url = str(hass.config.api.base_url) if hasattr(hass.config, "api") and hasattr(hass.config.api, "base_url") else None
            await coordinator.api.async_register_ha_webhook(
                webhook_id=webhook_id,
                ha_url=ha_url,
                allowed_chat_ids=allowed_chat_ids,
            )
            # Bidirectional sync: also fetch current allowed chats
            remote_chats = await coordinator.api.async_telegram_get_allowed_chats()
            if remote_chats and not allowed_chat_ids:
                new_opts = dict(entry.options)
                new_opts[CONF_ALLOWED_CHAT_IDS] = remote_chats
                hass.config_entries.async_update_entry(entry, options=new_opts)
        except Exception as e:
            _LOGGER.debug("Initial AegisBot webhook sync failed: %s", e)

    hass.async_create_task(_sync_with_aegisbot())

    # ------------------------------------------------------------------
    # Service Handlers
    # ------------------------------------------------------------------

    def _resolve_target(call: ServiceCall) -> list[Any]:
        target = (
            call.data.get("target")
            or call.data.get("chat_id")
            or call.data.get("group_id")
            or allowed_chat_ids
        )
        if not target:
            return []
        return target if isinstance(target, list) else [target]

    async def handle_send_message(call: ServiceCall) -> None:
        """Handle send_message (1:1 Telegram compatible)."""
        targets = _resolve_target(call)
        text = call.data.get("message") or call.data.get("text", "")
        title = call.data.get("title")
        if title:
            text = f"<b>{title}</b>\n{text}"

        data = call.data.get("data") or {}
        parse_mode = call.data.get("parse_mode") or data.get("parse_mode", "HTML")
        inline_keyboard = call.data.get("inline_keyboard") or data.get("inline_keyboard")
        keyboard = call.data.get("keyboard") or data.get("keyboard")
        reply_markup = call.data.get("reply_markup") or data.get("reply_markup")
        disable_notification = call.data.get("disable_notification", data.get("disable_notification", False))
        reply_to_message_id = call.data.get("reply_to_message_id") or data.get("reply_to_message_id")
        message_thread_id = call.data.get("message_thread_id") or data.get("message_thread_id")

        for t in targets:
            await coordinator.api.async_telegram_send_message(
                chat_id=t,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
                inline_keyboard=inline_keyboard,
                keyboard=keyboard,
                disable_notification=disable_notification,
                reply_to_message_id=reply_to_message_id,
                message_thread_id=message_thread_id,
            )

    async def handle_send_photo(call: ServiceCall) -> None:
        """Handle send_photo (1:1 Telegram compatible)."""
        targets = _resolve_target(call)
        file_path = (
            call.data.get("file")
            or call.data.get("url")
            or call.data.get("photo")
        )
        caption = call.data.get("caption") or call.data.get("message") or call.data.get("text")
        data = call.data.get("data") or {}
        parse_mode = call.data.get("parse_mode") or data.get("parse_mode", "HTML")
        inline_keyboard = call.data.get("inline_keyboard") or data.get("inline_keyboard")
        keyboard = call.data.get("keyboard") or data.get("keyboard")
        reply_markup = call.data.get("reply_markup") or data.get("reply_markup")
        disable_notification = call.data.get("disable_notification", data.get("disable_notification", False))
        reply_to_message_id = call.data.get("reply_to_message_id") or data.get("reply_to_message_id")
        message_thread_id = call.data.get("message_thread_id") or data.get("message_thread_id")

        for t in targets:
            await coordinator.api.async_telegram_send_photo(
                chat_id=t,
                file=file_path,
                caption=caption,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
                inline_keyboard=inline_keyboard,
                keyboard=keyboard,
                disable_notification=disable_notification,
                reply_to_message_id=reply_to_message_id,
                message_thread_id=message_thread_id,
            )

    async def handle_send_video(call: ServiceCall) -> None:
        """Handle send_video (1:1 Telegram compatible)."""
        targets = _resolve_target(call)
        file_path = call.data.get("file") or call.data.get("video") or call.data.get("url")
        caption = call.data.get("caption") or call.data.get("message") or call.data.get("text")
        data = call.data.get("data") or {}
        parse_mode = call.data.get("parse_mode") or data.get("parse_mode", "HTML")
        inline_keyboard = call.data.get("inline_keyboard") or data.get("inline_keyboard")
        keyboard = call.data.get("keyboard") or data.get("keyboard")
        reply_markup = call.data.get("reply_markup") or data.get("reply_markup")
        disable_notification = call.data.get("disable_notification", data.get("disable_notification", False))
        reply_to_message_id = call.data.get("reply_to_message_id") or data.get("reply_to_message_id")
        message_thread_id = call.data.get("message_thread_id") or data.get("message_thread_id")

        for t in targets:
            await coordinator.api.async_telegram_send_video(
                chat_id=t,
                file=file_path,
                caption=caption,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
                inline_keyboard=inline_keyboard,
                keyboard=keyboard,
                disable_notification=disable_notification,
                reply_to_message_id=reply_to_message_id,
                message_thread_id=message_thread_id,
            )

    async def handle_send_document(call: ServiceCall) -> None:
        """Handle send_document (1:1 Telegram compatible)."""
        targets = _resolve_target(call)
        file_path = call.data.get("file") or call.data.get("document") or call.data.get("url")
        caption = call.data.get("caption") or call.data.get("message") or call.data.get("text")
        data = call.data.get("data") or {}
        parse_mode = call.data.get("parse_mode") or data.get("parse_mode", "HTML")
        inline_keyboard = call.data.get("inline_keyboard") or data.get("inline_keyboard")
        keyboard = call.data.get("keyboard") or data.get("keyboard")
        reply_markup = call.data.get("reply_markup") or data.get("reply_markup")
        disable_notification = call.data.get("disable_notification", data.get("disable_notification", False))
        reply_to_message_id = call.data.get("reply_to_message_id") or data.get("reply_to_message_id")
        message_thread_id = call.data.get("message_thread_id") or data.get("message_thread_id")

        for t in targets:
            await coordinator.api.async_telegram_send_document(
                chat_id=t,
                file=file_path,
                caption=caption,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
                inline_keyboard=inline_keyboard,
                keyboard=keyboard,
                disable_notification=disable_notification,
                reply_to_message_id=reply_to_message_id,
                message_thread_id=message_thread_id,
            )

    async def handle_send_animation(call: ServiceCall) -> None:
        """Handle send_animation (1:1 Telegram compatible)."""
        targets = _resolve_target(call)
        file_path = call.data.get("file") or call.data.get("animation") or call.data.get("url")
        caption = call.data.get("caption") or call.data.get("message") or call.data.get("text")
        data = call.data.get("data") or {}
        parse_mode = call.data.get("parse_mode") or data.get("parse_mode", "HTML")
        inline_keyboard = call.data.get("inline_keyboard") or data.get("inline_keyboard")
        keyboard = call.data.get("keyboard") or data.get("keyboard")
        reply_markup = call.data.get("reply_markup") or data.get("reply_markup")
        disable_notification = call.data.get("disable_notification", data.get("disable_notification", False))
        reply_to_message_id = call.data.get("reply_to_message_id") or data.get("reply_to_message_id")
        message_thread_id = call.data.get("message_thread_id") or data.get("message_thread_id")

        for t in targets:
            await coordinator.api.async_telegram_send_animation(
                chat_id=t,
                file=file_path,
                caption=caption,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
                inline_keyboard=inline_keyboard,
                keyboard=keyboard,
                disable_notification=disable_notification,
                reply_to_message_id=reply_to_message_id,
                message_thread_id=message_thread_id,
            )

    async def handle_send_voice(call: ServiceCall) -> None:
        """Handle send_voice (1:1 Telegram compatible)."""
        targets = _resolve_target(call)
        file_path = call.data.get("file") or call.data.get("voice") or call.data.get("url")
        caption = call.data.get("caption") or call.data.get("message") or call.data.get("text")
        data = call.data.get("data") or {}
        parse_mode = call.data.get("parse_mode") or data.get("parse_mode", "HTML")
        inline_keyboard = call.data.get("inline_keyboard") or data.get("inline_keyboard")
        keyboard = call.data.get("keyboard") or data.get("keyboard")
        reply_markup = call.data.get("reply_markup") or data.get("reply_markup")
        disable_notification = call.data.get("disable_notification", data.get("disable_notification", False))
        reply_to_message_id = call.data.get("reply_to_message_id") or data.get("reply_to_message_id")
        message_thread_id = call.data.get("message_thread_id") or data.get("message_thread_id")

        for t in targets:
            await coordinator.api.async_telegram_send_voice(
                chat_id=t,
                file=file_path,
                caption=caption,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
                inline_keyboard=inline_keyboard,
                keyboard=keyboard,
                disable_notification=disable_notification,
                reply_to_message_id=reply_to_message_id,
                message_thread_id=message_thread_id,
            )

    async def handle_send_location(call: ServiceCall) -> None:
        """Handle send_location (1:1 Telegram compatible)."""
        targets = _resolve_target(call)
        lat = call.data["latitude"]
        lon = call.data["longitude"]
        live_period = call.data.get("live_period")
        inline_keyboard = call.data.get("inline_keyboard")
        reply_markup = call.data.get("reply_markup")
        disable_notification = call.data.get("disable_notification", False)
        reply_to_message_id = call.data.get("reply_to_message_id")
        message_thread_id = call.data.get("message_thread_id")

        for t in targets:
            await coordinator.api.async_telegram_send_location(
                chat_id=t,
                latitude=float(lat),
                longitude=float(lon),
                live_period=live_period,
                reply_markup=reply_markup,
                inline_keyboard=inline_keyboard,
                disable_notification=disable_notification,
                reply_to_message_id=reply_to_message_id,
                message_thread_id=message_thread_id,
            )

    async def handle_send_poll(call: ServiceCall) -> None:
        """Handle send_poll (smart polls for meetings, votes, food, etc.)."""
        targets = _resolve_target(call)
        question = call.data["question"]
        options = call.data["options"]
        is_anonymous = call.data.get("is_anonymous", True)
        poll_type = call.data.get("type", "regular")
        allows_multiple_answers = call.data.get("allows_multiple_answers", False)
        correct_option_id = call.data.get("correct_option_id")
        explanation = call.data.get("explanation")
        category = call.data.get("category", "general")
        reply_markup = call.data.get("reply_markup")
        disable_notification = call.data.get("disable_notification", False)
        reply_to_message_id = call.data.get("reply_to_message_id")
        message_thread_id = call.data.get("message_thread_id")

        for t in targets:
            await coordinator.api.async_telegram_send_poll(
                chat_id=t,
                question=question,
                options=options,
                is_anonymous=is_anonymous,
                poll_type=poll_type,
                allows_multiple_answers=allows_multiple_answers,
                correct_option_id=correct_option_id,
                explanation=explanation,
                category=category,
                reply_markup=reply_markup,
                disable_notification=disable_notification,
                reply_to_message_id=reply_to_message_id,
                message_thread_id=message_thread_id,
            )

    async def handle_stop_poll(call: ServiceCall) -> None:
        """Handle stop_poll service call."""
        targets = _resolve_target(call)
        message_id = call.data["message_id"]
        reply_markup = call.data.get("reply_markup")
        for t in targets:
            await coordinator.api.async_telegram_stop_poll(
                chat_id=t, message_id=message_id, reply_markup=reply_markup
            )

    async def handle_edit_message(call: ServiceCall) -> None:
        """Handle edit_message / edit_message_text service call."""
        targets = _resolve_target(call)
        message_id = call.data["message_id"]
        text = call.data.get("message") or call.data.get("text", "")
        parse_mode = call.data.get("parse_mode", "HTML")
        inline_keyboard = call.data.get("inline_keyboard")
        reply_markup = call.data.get("reply_markup")

        for t in targets:
            await coordinator.api.async_telegram_edit_message_text(
                chat_id=t,
                message_id=message_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
                inline_keyboard=inline_keyboard,
            )

    async def handle_edit_caption(call: ServiceCall) -> None:
        """Handle edit_caption service call."""
        targets = _resolve_target(call)
        message_id = call.data["message_id"]
        caption = call.data["caption"]
        parse_mode = call.data.get("parse_mode", "HTML")
        inline_keyboard = call.data.get("inline_keyboard")
        reply_markup = call.data.get("reply_markup")

        for t in targets:
            await coordinator.api.async_telegram_edit_message_caption(
                chat_id=t,
                message_id=message_id,
                caption=caption,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
                inline_keyboard=inline_keyboard,
            )

    async def handle_edit_replymarkup(call: ServiceCall) -> None:
        """Handle edit_replymarkup service call."""
        targets = _resolve_target(call)
        message_id = call.data["message_id"]
        inline_keyboard = call.data.get("inline_keyboard")
        reply_markup = call.data.get("reply_markup")

        for t in targets:
            await coordinator.api.async_telegram_edit_message_reply_markup(
                chat_id=t,
                message_id=message_id,
                reply_markup=reply_markup,
                inline_keyboard=inline_keyboard,
            )

    async def handle_delete_message(call: ServiceCall) -> None:
        """Handle delete_message service call."""
        targets = _resolve_target(call)
        message_id = call.data["message_id"]
        for t in targets:
            await coordinator.api.async_telegram_delete_message(
                chat_id=t, message_id=message_id
            )

    async def handle_answer_callback_query(call: ServiceCall) -> None:
        """Handle answer_callback_query service call."""
        cb_id = call.data["callback_query_id"]
        text = call.data.get("message") or call.data.get("text")
        show_alert = call.data.get("show_alert", False)
        url = call.data.get("url")
        cache_time = call.data.get("cache_time")
        await coordinator.api.async_telegram_answer_callback_query(
            callback_query_id=cb_id,
            text=text,
            show_alert=show_alert,
            url=url,
            cache_time=cache_time,
        )

    async def handle_leave_chat(call: ServiceCall) -> None:
        """Handle leave_chat service call."""
        targets = _resolve_target(call)
        for t in targets:
            await coordinator.api.async_telegram_leave_chat(chat_id=t)

    # Legacy / Bot Administration Services
    async def handle_ban_user(call: ServiceCall) -> None:
        group_id = call.data["group_id"]
        user_id = call.data["user_id"]
        duration = call.data.get("duration")
        reason = call.data.get("reason")
        await coordinator.api.async_ban_user(group_id, user_id, duration, reason)

    async def handle_unban_user(call: ServiceCall) -> None:
        group_id = call.data["group_id"]
        user_id = call.data["user_id"]
        await coordinator.api.async_unban_user(group_id, user_id)

    async def handle_mute_user(call: ServiceCall) -> None:
        group_id = call.data["group_id"]
        user_id = call.data["user_id"]
        duration = call.data["duration"]
        reason = call.data.get("reason")
        await coordinator.api.async_mute_user(group_id, user_id, duration, reason)

    async def handle_warn_user(call: ServiceCall) -> None:
        group_id = call.data["group_id"]
        user_id = call.data["user_id"]
        reason = call.data["reason"]
        await coordinator.api.async_warn_user(group_id, user_id, reason)

    async def handle_broadcast(call: ServiceCall) -> None:
        text = call.data["text"]
        group_ids = call.data.get("group_ids")
        platform = call.data.get("platform")
        await coordinator.api.async_broadcast(
            text=text, group_ids=group_ids, platform=platform
        )

    async def handle_adjust_reputation(call: ServiceCall) -> None:
        user_id = call.data["user_id"]
        delta = call.data["delta"]
        reason = call.data.get("reason")
        group_id = call.data.get("group_id")
        await coordinator.api.async_adjust_reputation(
            user_id=user_id, delta=delta, reason=reason, group_id=group_id
        )

    async def handle_apply_preset(call: ServiceCall) -> None:
        group_id = call.data["group_id"]
        preset_name = call.data["preset_name"]
        await coordinator.api.async_apply_preset(
            group_id=group_id, preset_name=preset_name
        )
        await coordinator.async_request_refresh()

    async def handle_maintenance_cleanup(call: ServiceCall) -> None:
        days = call.data.get("days")
        await coordinator.api.async_maintenance_cleanup(days=days)
        await coordinator.async_request_refresh()

    async def handle_maintenance_purge(call: ServiceCall) -> None:
        group_id = call.data["group_id"]
        await coordinator.api.async_maintenance_purge(group_id=group_id)
        await coordinator.async_request_refresh()

    async def handle_mark_notifications_read(call: ServiceCall) -> None:
        notification_ids = call.data.get("notification_ids")
        await coordinator.api.async_mark_notifications_read(
            notification_ids=notification_ids
        )

    async def handle_whatsapp_action(call: ServiceCall) -> None:
        action = call.data["action"]
        data = call.data.get("data")
        await coordinator.api.async_whatsapp_action(action=action, data=data)
        await coordinator.async_request_refresh()

    async def handle_maintenance_vacuum(call: ServiceCall) -> None:
        await coordinator.api.async_maintenance_vacuum()
        await coordinator.async_request_refresh()

    async def handle_maintenance_live_test(call: ServiceCall) -> None:
        await coordinator.api.async_maintenance_live_test()
        await coordinator.async_request_refresh()

    async def handle_sync_filters(call: ServiceCall) -> None:
        await coordinator.api.async_sync_filters()
        await coordinator.async_request_refresh()

    # Register all services
    hass.services.async_register(DOMAIN, "send_message", handle_send_message)
    hass.services.async_register(DOMAIN, "send_photo", handle_send_photo)
    hass.services.async_register(DOMAIN, "send_video", handle_send_video)
    hass.services.async_register(DOMAIN, "send_document", handle_send_document)
    hass.services.async_register(DOMAIN, "send_animation", handle_send_animation)
    hass.services.async_register(DOMAIN, "send_voice", handle_send_voice)
    hass.services.async_register(DOMAIN, "send_location", handle_send_location)
    hass.services.async_register(DOMAIN, "send_poll", handle_send_poll)
    hass.services.async_register(DOMAIN, "stop_poll", handle_stop_poll)
    hass.services.async_register(DOMAIN, "edit_message", handle_edit_message)
    hass.services.async_register(DOMAIN, "edit_caption", handle_edit_caption)
    hass.services.async_register(DOMAIN, "edit_replymarkup", handle_edit_replymarkup)
    hass.services.async_register(DOMAIN, "delete_message", handle_delete_message)
    hass.services.async_register(DOMAIN, "answer_callback_query", handle_answer_callback_query)
    hass.services.async_register(DOMAIN, "leave_chat", handle_leave_chat)

    # Legacy & admin services
    hass.services.async_register(DOMAIN, "ban_user", handle_ban_user)
    hass.services.async_register(DOMAIN, "unban_user", handle_unban_user)
    hass.services.async_register(DOMAIN, "mute_user", handle_mute_user)
    hass.services.async_register(DOMAIN, "warn_user", handle_warn_user)
    hass.services.async_register(DOMAIN, "broadcast", handle_broadcast)
    hass.services.async_register(DOMAIN, "adjust_reputation", handle_adjust_reputation)
    hass.services.async_register(DOMAIN, "apply_preset", handle_apply_preset)
    hass.services.async_register(DOMAIN, "sync_filters", handle_sync_filters)
    hass.services.async_register(DOMAIN, "maintenance_vacuum", handle_maintenance_vacuum)
    hass.services.async_register(DOMAIN, "maintenance_cleanup", handle_maintenance_cleanup)
    hass.services.async_register(DOMAIN, "maintenance_purge", handle_maintenance_purge)
    hass.services.async_register(DOMAIN, "maintenance_live_test", handle_maintenance_live_test)
    hass.services.async_register(DOMAIN, "mark_notifications_read", handle_mark_notifications_read)
    hass.services.async_register(DOMAIN, "whatsapp_action", handle_whatsapp_action)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    webhook_id = entry.data.get(CONF_WEBHOOK_ID) or f"{DOMAIN}_{entry.entry_id}"
    try:
        webhook.async_unregister(hass, webhook_id)
    except Exception:
        pass

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
