"""The AegisBot integration."""

from __future__ import annotations

import logging
from typing import Any

from aiohttp import web
from homeassistant.components import webhook
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import Event, HomeAssistant, ServiceCall
from homeassistant.helpers.discovery import async_load_platform

from .const import (
    CONF_ALLOWED_CHAT_IDS,
    CONF_AUTO_SYNC_COMMANDS,
    CONF_BOT,
    CONF_BOT_ID,
    CONF_DEFAULT_BOT_ID,
    CONF_ENABLE_TELEGRAM_PROXY,
    CONF_IGNORED_COMMANDS,
    CONF_WEBHOOK_ID,
    DOMAIN,
    EVENT_AEGISBOT_TEXT,
)
from .coordinator import AegisBotDataCoordinator

_LOGGER = logging.getLogger(__name__)

EVENT_AUTOMATION_RELOADED = "automation_reloaded"

CORE_PLATFORMS: list[Platform] = [
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

    enable_telegram_proxy = entry.options.get(
        CONF_ENABLE_TELEGRAM_PROXY,
        entry.data.get(CONF_ENABLE_TELEGRAM_PROXY, True),
    )
    auto_sync_commands = entry.options.get(
        CONF_AUTO_SYNC_COMMANDS,
        entry.data.get(CONF_AUTO_SYNC_COMMANDS, True),
    )
    default_bot_id = entry.options.get(
        CONF_DEFAULT_BOT_ID,
        entry.data.get(CONF_DEFAULT_BOT_ID),
    )

    platforms = list(CORE_PLATFORMS)
    if enable_telegram_proxy:
        platforms.append(Platform.NOTIFY)

    await hass.config_entries.async_forward_entry_setups(entry, platforms)

    # Allowed Chat IDs resolution
    allowed_chat_ids = entry.options.get(
        CONF_ALLOWED_CHAT_IDS, entry.data.get(CONF_ALLOWED_CHAT_IDS, [])
    )
    if isinstance(allowed_chat_ids, str):
        allowed_chat_ids = [x.strip() for x in allowed_chat_ids.split(",") if x.strip()]

    # Load Notify platform if enabled
    if enable_telegram_proxy:
        discovery_info = {
            "entry_id": entry.entry_id,
            CONF_ALLOWED_CHAT_IDS: allowed_chat_ids,
            CONF_DEFAULT_BOT_ID: default_bot_id,
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
            api_conf = getattr(hass.config, "api", None)
            ha_url = (
                str(api_conf.base_url)
                if api_conf and hasattr(api_conf, "base_url")
                else None
            )
            await coordinator.api.async_register_ha_webhook(
                webhook_id=webhook_id,
                ha_url=ha_url,
                allowed_chat_ids=allowed_chat_ids,
            )
            remote_chats = await coordinator.api.async_telegram_get_allowed_chats()
            if remote_chats and not allowed_chat_ids:
                new_opts = dict(entry.options)
                new_opts[CONF_ALLOWED_CHAT_IDS] = remote_chats
                hass.config_entries.async_update_entry(entry, options=new_opts)
        except Exception as e:
            _LOGGER.debug("Initial AegisBot webhook sync failed: %s", e)

    hass.async_create_task(_sync_with_aegisbot())

    # ------------------------------------------------------------------
    # Automation Command Scanner & Auto-Sync
    # ------------------------------------------------------------------

    async def _async_scan_and_sync_commands() -> None:
        """Scan Home Assistant automations for Telegram commands and sync to bot."""
        if not auto_sync_commands or not enable_telegram_proxy:
            return

        raw_ignored = entry.options.get(
            CONF_IGNORED_COMMANDS, entry.data.get(CONF_IGNORED_COMMANDS, "")
        )
        ignored_set: set[str] = (
            {x.strip().lstrip("/").lower() for x in raw_ignored.split(",") if x.strip()}
            if isinstance(raw_ignored, str)
            else {str(x).strip().lstrip("/").lower() for x in raw_ignored}
        )

        discovered_commands: dict[str, str] = {}

        # 1. Inspect automation config from hass.data
        raw_configs = hass.data.get("automation_config") or []
        if isinstance(raw_configs, dict):
            raw_configs = list(raw_configs.values())

        for auto_conf in raw_configs:
            if not isinstance(auto_conf, dict):
                continue
            triggers = auto_conf.get("trigger") or auto_conf.get("triggers") or []
            if isinstance(triggers, dict):
                triggers = [triggers]
            alias = auto_conf.get("alias") or auto_conf.get("description") or ""

            for trig in triggers:
                if not isinstance(trig, dict):
                    continue
                if trig.get("platform") == "event":
                    ev_type = trig.get("event_type")
                    if ev_type in ("aegisbot_command", "telegram_command"):
                        ev_data = trig.get("event_data") or {}
                        cmd = ev_data.get("command")
                        if cmd:
                            clean_cmd = (
                                str(cmd).lstrip("/").split("@")[0].strip().lower()
                            )
                            if (
                                clean_cmd
                                and clean_cmd not in ignored_set
                                and clean_cmd not in discovered_commands
                            ):
                                discovered_commands[clean_cmd] = (
                                    alias or f"Command /{clean_cmd}"
                                )

        # 2. Inspect entity states for automations
        for state in hass.states.async_all("automation"):
            desc = state.attributes.get("friendly_name") or state.entity_id
            # If trigger metadata is attached in attributes
            extra_triggers = state.attributes.get("triggers") or []
            for trig in extra_triggers:
                if isinstance(trig, dict) and trig.get("event_type") in (
                    "aegisbot_command",
                    "telegram_command",
                ):
                    ev_data = trig.get("event_data") or {}
                    cmd = ev_data.get("command")
                    if cmd:
                        clean_cmd = str(cmd).lstrip("/").split("@")[0].strip().lower()
                        if (
                            clean_cmd
                            and clean_cmd not in ignored_set
                            and clean_cmd not in discovered_commands
                        ):
                            discovered_commands[clean_cmd] = desc

        if discovered_commands:
            payload_cmds = [
                {"command": cmd, "description": desc[:256]}
                for cmd, desc in discovered_commands.items()
            ]
            try:
                await coordinator.api.async_sync_commands(
                    commands=payload_cmds,
                    bot_id=default_bot_id,
                )
                _LOGGER.info(
                    "Auto-synced %d automation commands to AegisBot: %s",
                    len(payload_cmds),
                    list(discovered_commands.keys()),
                )
            except Exception as ex:
                _LOGGER.debug("Failed to auto-sync commands to AegisBot: %s", ex)

    # Trigger scan on startup & on automation reloads
    async def _on_automation_reloaded(event: Event) -> None:
        await _async_scan_and_sync_commands()

    hass.bus.async_listen(EVENT_AUTOMATION_RELOADED, _on_automation_reloaded)
    hass.async_create_task(_async_scan_and_sync_commands())

    # ------------------------------------------------------------------
    # Service Handlers & Multi-Bot Resolution
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

    def _resolve_bot(call: ServiceCall) -> int | str | None:
        data = call.data.get("data") or {}
        return (
            call.data.get(CONF_BOT)
            or call.data.get(CONF_BOT_ID)
            or data.get(CONF_BOT)
            or data.get(CONF_BOT_ID)
            or default_bot_id
        )

    if enable_telegram_proxy:

        async def handle_send_message(call: ServiceCall) -> None:
            """Handle send_message (1:1 Telegram compatible)."""
            targets = _resolve_target(call)
            text = call.data.get("message") or call.data.get("text", "")
            title = call.data.get("title")
            if title:
                text = f"<b>{title}</b>\n{text}"

            data = call.data.get("data") or {}
            parse_mode = call.data.get("parse_mode") or data.get("parse_mode", "HTML")
            inline_keyboard = call.data.get("inline_keyboard") or data.get(
                "inline_keyboard"
            )
            keyboard = call.data.get("keyboard") or data.get("keyboard")
            reply_markup = call.data.get("reply_markup") or data.get("reply_markup")
            disable_notification = call.data.get(
                "disable_notification", data.get("disable_notification", False)
            )
            reply_to_message_id = call.data.get("reply_to_message_id") or data.get(
                "reply_to_message_id"
            )
            message_thread_id = call.data.get("message_thread_id") or data.get(
                "message_thread_id"
            )
            bot = _resolve_bot(call)

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
                    bot_id=bot,
                )

        async def handle_send_photo(call: ServiceCall) -> None:
            """Handle send_photo (1:1 Telegram compatible)."""
            targets = _resolve_target(call)
            file_path = (
                call.data.get("file") or call.data.get("url") or call.data.get("photo")
            )
            caption = (
                call.data.get("caption")
                or call.data.get("message")
                or call.data.get("text")
            )
            data = call.data.get("data") or {}
            parse_mode = call.data.get("parse_mode") or data.get("parse_mode", "HTML")
            inline_keyboard = call.data.get("inline_keyboard") or data.get(
                "inline_keyboard"
            )
            keyboard = call.data.get("keyboard") or data.get("keyboard")
            reply_markup = call.data.get("reply_markup") or data.get("reply_markup")
            disable_notification = call.data.get(
                "disable_notification", data.get("disable_notification", False)
            )
            reply_to_message_id = call.data.get("reply_to_message_id") or data.get(
                "reply_to_message_id"
            )
            message_thread_id = call.data.get("message_thread_id") or data.get(
                "message_thread_id"
            )
            bot = _resolve_bot(call)

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
                    bot_id=bot,
                )

        async def handle_send_video(call: ServiceCall) -> None:
            """Handle send_video (1:1 Telegram compatible)."""
            targets = _resolve_target(call)
            file_path = (
                call.data.get("file") or call.data.get("video") or call.data.get("url")
            )
            caption = (
                call.data.get("caption")
                or call.data.get("message")
                or call.data.get("text")
            )
            data = call.data.get("data") or {}
            parse_mode = call.data.get("parse_mode") or data.get("parse_mode", "HTML")
            inline_keyboard = call.data.get("inline_keyboard") or data.get(
                "inline_keyboard"
            )
            keyboard = call.data.get("keyboard") or data.get("keyboard")
            reply_markup = call.data.get("reply_markup") or data.get("reply_markup")
            disable_notification = call.data.get(
                "disable_notification", data.get("disable_notification", False)
            )
            reply_to_message_id = call.data.get("reply_to_message_id") or data.get(
                "reply_to_message_id"
            )
            message_thread_id = call.data.get("message_thread_id") or data.get(
                "message_thread_id"
            )
            bot = _resolve_bot(call)

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
                    bot_id=bot,
                )

        async def handle_send_document(call: ServiceCall) -> None:
            """Handle send_document (1:1 Telegram compatible)."""
            targets = _resolve_target(call)
            file_path = (
                call.data.get("file")
                or call.data.get("document")
                or call.data.get("url")
            )
            caption = (
                call.data.get("caption")
                or call.data.get("message")
                or call.data.get("text")
            )
            data = call.data.get("data") or {}
            parse_mode = call.data.get("parse_mode") or data.get("parse_mode", "HTML")
            inline_keyboard = call.data.get("inline_keyboard") or data.get(
                "inline_keyboard"
            )
            keyboard = call.data.get("keyboard") or data.get("keyboard")
            reply_markup = call.data.get("reply_markup") or data.get("reply_markup")
            disable_notification = call.data.get(
                "disable_notification", data.get("disable_notification", False)
            )
            reply_to_message_id = call.data.get("reply_to_message_id") or data.get(
                "reply_to_message_id"
            )
            message_thread_id = call.data.get("message_thread_id") or data.get(
                "message_thread_id"
            )
            bot = _resolve_bot(call)

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
                    bot_id=bot,
                )

        async def handle_send_animation(call: ServiceCall) -> None:
            """Handle send_animation (1:1 Telegram compatible)."""
            targets = _resolve_target(call)
            file_path = (
                call.data.get("file")
                or call.data.get("animation")
                or call.data.get("url")
            )
            caption = (
                call.data.get("caption")
                or call.data.get("message")
                or call.data.get("text")
            )
            data = call.data.get("data") or {}
            parse_mode = call.data.get("parse_mode") or data.get("parse_mode", "HTML")
            inline_keyboard = call.data.get("inline_keyboard") or data.get(
                "inline_keyboard"
            )
            keyboard = call.data.get("keyboard") or data.get("keyboard")
            reply_markup = call.data.get("reply_markup") or data.get("reply_markup")
            disable_notification = call.data.get(
                "disable_notification", data.get("disable_notification", False)
            )
            reply_to_message_id = call.data.get("reply_to_message_id") or data.get(
                "reply_to_message_id"
            )
            message_thread_id = call.data.get("message_thread_id") or data.get(
                "message_thread_id"
            )
            bot = _resolve_bot(call)

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
                    bot_id=bot,
                )

        async def handle_send_voice(call: ServiceCall) -> None:
            """Handle send_voice (1:1 Telegram compatible)."""
            targets = _resolve_target(call)
            file_path = (
                call.data.get("file") or call.data.get("voice") or call.data.get("url")
            )
            caption = (
                call.data.get("caption")
                or call.data.get("message")
                or call.data.get("text")
            )
            data = call.data.get("data") or {}
            parse_mode = call.data.get("parse_mode") or data.get("parse_mode", "HTML")
            inline_keyboard = call.data.get("inline_keyboard") or data.get(
                "inline_keyboard"
            )
            keyboard = call.data.get("keyboard") or data.get("keyboard")
            reply_markup = call.data.get("reply_markup") or data.get("reply_markup")
            disable_notification = call.data.get(
                "disable_notification", data.get("disable_notification", False)
            )
            reply_to_message_id = call.data.get("reply_to_message_id") or data.get(
                "reply_to_message_id"
            )
            message_thread_id = call.data.get("message_thread_id") or data.get(
                "message_thread_id"
            )
            bot = _resolve_bot(call)

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
                    bot_id=bot,
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
            bot = _resolve_bot(call)

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
                    bot_id=bot,
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
            bot = _resolve_bot(call)

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
                    bot_id=bot,
                )

        async def handle_stop_poll(call: ServiceCall) -> None:
            """Handle stop_poll service call."""
            targets = _resolve_target(call)
            message_id = call.data["message_id"]
            reply_markup = call.data.get("reply_markup")
            bot = _resolve_bot(call)
            for t in targets:
                await coordinator.api.async_telegram_stop_poll(
                    chat_id=t,
                    message_id=message_id,
                    reply_markup=reply_markup,
                    bot_id=bot,
                )

        async def handle_edit_message(call: ServiceCall) -> None:
            """Handle edit_message / edit_message_text service call."""
            targets = _resolve_target(call)
            message_id = call.data["message_id"]
            text = call.data.get("message") or call.data.get("text", "")
            parse_mode = call.data.get("parse_mode", "HTML")
            inline_keyboard = call.data.get("inline_keyboard")
            reply_markup = call.data.get("reply_markup")
            bot = _resolve_bot(call)

            for t in targets:
                await coordinator.api.async_telegram_edit_message_text(
                    chat_id=t,
                    message_id=message_id,
                    text=text,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup,
                    inline_keyboard=inline_keyboard,
                    bot_id=bot,
                )

        async def handle_edit_caption(call: ServiceCall) -> None:
            """Handle edit_caption service call."""
            targets = _resolve_target(call)
            message_id = call.data["message_id"]
            caption = call.data["caption"]
            parse_mode = call.data.get("parse_mode", "HTML")
            inline_keyboard = call.data.get("inline_keyboard")
            reply_markup = call.data.get("reply_markup")
            bot = _resolve_bot(call)

            for t in targets:
                await coordinator.api.async_telegram_edit_message_caption(
                    chat_id=t,
                    message_id=message_id,
                    caption=caption,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup,
                    inline_keyboard=inline_keyboard,
                    bot_id=bot,
                )

        async def handle_edit_replymarkup(call: ServiceCall) -> None:
            """Handle edit_replymarkup service call."""
            targets = _resolve_target(call)
            message_id = call.data["message_id"]
            inline_keyboard = call.data.get("inline_keyboard")
            reply_markup = call.data.get("reply_markup")
            bot = _resolve_bot(call)

            for t in targets:
                await coordinator.api.async_telegram_edit_message_reply_markup(
                    chat_id=t,
                    message_id=message_id,
                    reply_markup=reply_markup,
                    inline_keyboard=inline_keyboard,
                    bot_id=bot,
                )

        async def handle_delete_message(call: ServiceCall) -> None:
            """Handle delete_message service call."""
            targets = _resolve_target(call)
            message_id = call.data["message_id"]
            bot = _resolve_bot(call)
            for t in targets:
                await coordinator.api.async_telegram_delete_message(
                    chat_id=t, message_id=message_id, bot_id=bot
                )

        async def handle_answer_callback_query(call: ServiceCall) -> None:
            """Handle answer_callback_query service call."""
            cb_id = call.data["callback_query_id"]
            text = call.data.get("message") or call.data.get("text")
            show_alert = call.data.get("show_alert", False)
            url = call.data.get("url")
            cache_time = call.data.get("cache_time")
            bot = _resolve_bot(call)
            await coordinator.api.async_telegram_answer_callback_query(
                callback_query_id=cb_id,
                text=text,
                show_alert=show_alert,
                url=url,
                cache_time=cache_time,
                bot_id=bot,
            )

        async def handle_send_audio(call: ServiceCall) -> None:
            """Handle send_audio service call."""
            targets = _resolve_target(call)
            audio = (
                call.data.get("file") or call.data.get("url") or call.data.get("audio")
            )
            caption = (
                call.data.get("caption")
                or call.data.get("message")
                or call.data.get("text")
            )
            data = call.data.get("data") or {}
            parse_mode = call.data.get("parse_mode") or data.get("parse_mode", "HTML")
            duration = call.data.get("duration") or data.get("duration")
            performer = call.data.get("performer") or data.get("performer")
            title = call.data.get("title") or data.get("title")
            inline_keyboard = call.data.get("inline_keyboard") or data.get(
                "inline_keyboard"
            )
            keyboard = call.data.get("keyboard") or data.get("keyboard")
            reply_markup = call.data.get("reply_markup") or data.get("reply_markup")
            disable_notification = call.data.get(
                "disable_notification", data.get("disable_notification", False)
            )
            reply_to_message_id = call.data.get("reply_to_message_id") or data.get(
                "reply_to_message_id"
            )
            message_thread_id = call.data.get("message_thread_id") or data.get(
                "message_thread_id"
            )
            bot = _resolve_bot(call)

            for t in targets:
                await coordinator.api.async_telegram_send_audio(
                    chat_id=t,
                    audio=audio,
                    caption=caption,
                    parse_mode=parse_mode,
                    duration=duration,
                    performer=performer,
                    title=title,
                    reply_markup=reply_markup,
                    inline_keyboard=inline_keyboard,
                    keyboard=keyboard,
                    disable_notification=disable_notification,
                    reply_to_message_id=reply_to_message_id,
                    message_thread_id=message_thread_id,
                    bot_id=bot,
                )

        async def handle_send_sticker(call: ServiceCall) -> None:
            """Handle send_sticker service call."""
            targets = _resolve_target(call)
            sticker = (
                call.data.get("file")
                or call.data.get("url")
                or call.data.get("sticker")
            )
            data = call.data.get("data") or {}
            inline_keyboard = call.data.get("inline_keyboard") or data.get(
                "inline_keyboard"
            )
            keyboard = call.data.get("keyboard") or data.get("keyboard")
            reply_markup = call.data.get("reply_markup") or data.get("reply_markup")
            disable_notification = call.data.get(
                "disable_notification", data.get("disable_notification", False)
            )
            reply_to_message_id = call.data.get("reply_to_message_id") or data.get(
                "reply_to_message_id"
            )
            message_thread_id = call.data.get("message_thread_id") or data.get(
                "message_thread_id"
            )
            bot = _resolve_bot(call)

            for t in targets:
                await coordinator.api.async_telegram_send_sticker(
                    chat_id=t,
                    sticker=sticker,
                    reply_markup=reply_markup,
                    inline_keyboard=inline_keyboard,
                    keyboard=keyboard,
                    disable_notification=disable_notification,
                    reply_to_message_id=reply_to_message_id,
                    message_thread_id=message_thread_id,
                    bot_id=bot,
                )

        async def handle_send_chat_action(call: ServiceCall) -> None:
            """Handle send_chat_action / send_action service call."""
            targets = _resolve_target(call)
            action = call.data.get("action", "typing")
            data = call.data.get("data") or {}
            message_thread_id = call.data.get("message_thread_id") or data.get(
                "message_thread_id"
            )
            bot = _resolve_bot(call)

            for t in targets:
                await coordinator.api.async_telegram_send_chat_action(
                    chat_id=t,
                    action=action,
                    message_thread_id=message_thread_id,
                    bot_id=bot,
                )

        async def handle_send_video_note(call: ServiceCall) -> None:
            """Handle send_video_note service call."""
            targets = _resolve_target(call)
            video_note = (
                call.data.get("file")
                or call.data.get("url")
                or call.data.get("video_note")
            )
            data = call.data.get("data") or {}
            duration = call.data.get("duration") or data.get("duration")
            length = call.data.get("length") or data.get("length")
            inline_keyboard = call.data.get("inline_keyboard") or data.get(
                "inline_keyboard"
            )
            keyboard = call.data.get("keyboard") or data.get("keyboard")
            reply_markup = call.data.get("reply_markup") or data.get("reply_markup")
            disable_notification = call.data.get(
                "disable_notification", data.get("disable_notification", False)
            )
            reply_to_message_id = call.data.get("reply_to_message_id") or data.get(
                "reply_to_message_id"
            )
            message_thread_id = call.data.get("message_thread_id") or data.get(
                "message_thread_id"
            )
            bot = _resolve_bot(call)

            for t in targets:
                await coordinator.api.async_telegram_send_video_note(
                    chat_id=t,
                    video_note=video_note,
                    duration=duration,
                    length=length,
                    reply_markup=reply_markup,
                    inline_keyboard=inline_keyboard,
                    keyboard=keyboard,
                    disable_notification=disable_notification,
                    reply_to_message_id=reply_to_message_id,
                    message_thread_id=message_thread_id,
                    bot_id=bot,
                )

        async def handle_send_dice(call: ServiceCall) -> None:
            """Handle send_dice service call."""
            targets = _resolve_target(call)
            emoji = call.data.get("emoji", "🎲")
            data = call.data.get("data") or {}
            inline_keyboard = call.data.get("inline_keyboard") or data.get(
                "inline_keyboard"
            )
            keyboard = call.data.get("keyboard") or data.get("keyboard")
            reply_markup = call.data.get("reply_markup") or data.get("reply_markup")
            disable_notification = call.data.get(
                "disable_notification", data.get("disable_notification", False)
            )
            reply_to_message_id = call.data.get("reply_to_message_id") or data.get(
                "reply_to_message_id"
            )
            message_thread_id = call.data.get("message_thread_id") or data.get(
                "message_thread_id"
            )
            bot = _resolve_bot(call)

            for t in targets:
                await coordinator.api.async_telegram_send_dice(
                    chat_id=t,
                    emoji=emoji,
                    reply_markup=reply_markup,
                    inline_keyboard=inline_keyboard,
                    keyboard=keyboard,
                    disable_notification=disable_notification,
                    reply_to_message_id=reply_to_message_id,
                    message_thread_id=message_thread_id,
                    bot_id=bot,
                )

        async def handle_send_venue(call: ServiceCall) -> None:
            """Handle send_venue service call."""
            targets = _resolve_target(call)
            latitude = float(call.data["latitude"])
            longitude = float(call.data["longitude"])
            title = call.data["title"]
            address = call.data["address"]
            foursquare_id = call.data.get("foursquare_id")
            google_place_id = call.data.get("google_place_id")
            data = call.data.get("data") or {}
            inline_keyboard = call.data.get("inline_keyboard") or data.get(
                "inline_keyboard"
            )
            keyboard = call.data.get("keyboard") or data.get("keyboard")
            reply_markup = call.data.get("reply_markup") or data.get("reply_markup")
            disable_notification = call.data.get(
                "disable_notification", data.get("disable_notification", False)
            )
            reply_to_message_id = call.data.get("reply_to_message_id") or data.get(
                "reply_to_message_id"
            )
            message_thread_id = call.data.get("message_thread_id") or data.get(
                "message_thread_id"
            )
            bot = _resolve_bot(call)

            for t in targets:
                await coordinator.api.async_telegram_send_venue(
                    chat_id=t,
                    latitude=latitude,
                    longitude=longitude,
                    title=title,
                    address=address,
                    foursquare_id=foursquare_id,
                    google_place_id=google_place_id,
                    reply_markup=reply_markup,
                    inline_keyboard=inline_keyboard,
                    keyboard=keyboard,
                    disable_notification=disable_notification,
                    reply_to_message_id=reply_to_message_id,
                    message_thread_id=message_thread_id,
                    bot_id=bot,
                )

        async def handle_send_contact(call: ServiceCall) -> None:
            """Handle send_contact service call."""
            targets = _resolve_target(call)
            phone_number = call.data["phone_number"]
            first_name = call.data["first_name"]
            last_name = call.data.get("last_name")
            vcard = call.data.get("vcard")
            data = call.data.get("data") or {}
            inline_keyboard = call.data.get("inline_keyboard") or data.get(
                "inline_keyboard"
            )
            keyboard = call.data.get("keyboard") or data.get("keyboard")
            reply_markup = call.data.get("reply_markup") or data.get("reply_markup")
            disable_notification = call.data.get(
                "disable_notification", data.get("disable_notification", False)
            )
            reply_to_message_id = call.data.get("reply_to_message_id") or data.get(
                "reply_to_message_id"
            )
            message_thread_id = call.data.get("message_thread_id") or data.get(
                "message_thread_id"
            )
            bot = _resolve_bot(call)

            for t in targets:
                await coordinator.api.async_telegram_send_contact(
                    chat_id=t,
                    phone_number=phone_number,
                    first_name=first_name,
                    last_name=last_name,
                    vcard=vcard,
                    reply_markup=reply_markup,
                    inline_keyboard=inline_keyboard,
                    keyboard=keyboard,
                    disable_notification=disable_notification,
                    reply_to_message_id=reply_to_message_id,
                    message_thread_id=message_thread_id,
                    bot_id=bot,
                )

        async def handle_edit_message_media(call: ServiceCall) -> None:
            """Handle edit_message_media service call."""
            targets = _resolve_target(call)
            message_id = call.data["message_id"]
            media = (
                call.data.get("file") or call.data.get("url") or call.data.get("media")
            )
            media_type = call.data.get("media_type", "photo")
            caption = call.data.get("caption") or call.data.get("message")
            parse_mode = call.data.get("parse_mode", "HTML")
            inline_keyboard = call.data.get("inline_keyboard")
            reply_markup = call.data.get("reply_markup")
            bot = _resolve_bot(call)

            for t in targets:
                await coordinator.api.async_telegram_edit_message_media(
                    chat_id=t,
                    message_id=message_id,
                    media=media,
                    media_type=media_type,
                    caption=caption,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup,
                    inline_keyboard=inline_keyboard,
                    bot_id=bot,
                )

        async def handle_edit_live_location(call: ServiceCall) -> None:
            """Handle edit_live_location service call."""
            targets = _resolve_target(call)
            message_id = call.data["message_id"]
            latitude = float(call.data["latitude"])
            longitude = float(call.data["longitude"])
            inline_keyboard = call.data.get("inline_keyboard")
            reply_markup = call.data.get("reply_markup")
            bot = _resolve_bot(call)

            for t in targets:
                await coordinator.api.async_telegram_edit_live_location(
                    chat_id=t,
                    message_id=message_id,
                    latitude=latitude,
                    longitude=longitude,
                    reply_markup=reply_markup,
                    inline_keyboard=inline_keyboard,
                    bot_id=bot,
                )

        async def handle_stop_live_location(call: ServiceCall) -> None:
            """Handle stop_live_location service call."""
            targets = _resolve_target(call)
            message_id = call.data["message_id"]
            inline_keyboard = call.data.get("inline_keyboard")
            reply_markup = call.data.get("reply_markup")
            bot = _resolve_bot(call)

            for t in targets:
                await coordinator.api.async_telegram_stop_live_location(
                    chat_id=t,
                    message_id=message_id,
                    reply_markup=reply_markup,
                    inline_keyboard=inline_keyboard,
                    bot_id=bot,
                )

        async def handle_set_message_reaction(call: ServiceCall) -> None:
            """Handle set_message_reaction service call."""
            targets = _resolve_target(call)
            message_id = call.data["message_id"]
            reaction = call.data.get("reaction", "👍")
            is_big = call.data.get("is_big", False)
            bot = _resolve_bot(call)

            for t in targets:
                await coordinator.api.async_telegram_set_message_reaction(
                    chat_id=t,
                    message_id=message_id,
                    reaction=reaction,
                    is_big=is_big,
                    bot_id=bot,
                )

        async def handle_forward_message(call: ServiceCall) -> None:
            """Handle forward_message service call."""
            targets = _resolve_target(call)
            from_chat_id = call.data["from_chat_id"]
            message_id = call.data["message_id"]
            disable_notification = call.data.get("disable_notification", False)
            message_thread_id = call.data.get("message_thread_id")
            bot = _resolve_bot(call)

            for t in targets:
                await coordinator.api.async_telegram_forward_message(
                    chat_id=t,
                    from_chat_id=from_chat_id,
                    message_id=message_id,
                    disable_notification=disable_notification,
                    message_thread_id=message_thread_id,
                    bot_id=bot,
                )

        async def handle_copy_message(call: ServiceCall) -> None:
            """Handle copy_message service call."""
            targets = _resolve_target(call)
            from_chat_id = call.data["from_chat_id"]
            message_id = call.data["message_id"]
            caption = call.data.get("caption") or call.data.get("message")
            parse_mode = call.data.get("parse_mode", "HTML")
            inline_keyboard = call.data.get("inline_keyboard")
            keyboard = call.data.get("keyboard")
            reply_markup = call.data.get("reply_markup")
            disable_notification = call.data.get("disable_notification", False)
            message_thread_id = call.data.get("message_thread_id")
            bot = _resolve_bot(call)

            for t in targets:
                await coordinator.api.async_telegram_copy_message(
                    chat_id=t,
                    from_chat_id=from_chat_id,
                    message_id=message_id,
                    caption=caption,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup,
                    inline_keyboard=inline_keyboard,
                    keyboard=keyboard,
                    disable_notification=disable_notification,
                    message_thread_id=message_thread_id,
                    bot_id=bot,
                )

        async def handle_pin_message(call: ServiceCall) -> None:
            """Handle pin_message service call."""
            targets = _resolve_target(call)
            message_id = call.data["message_id"]
            disable_notification = call.data.get("disable_notification", False)
            bot = _resolve_bot(call)

            for t in targets:
                await coordinator.api.async_telegram_pin_message(
                    chat_id=t,
                    message_id=message_id,
                    disable_notification=disable_notification,
                    bot_id=bot,
                )

        async def handle_unpin_message(call: ServiceCall) -> None:
            """Handle unpin_message service call."""
            targets = _resolve_target(call)
            message_id = call.data.get("message_id")
            bot = _resolve_bot(call)

            for t in targets:
                await coordinator.api.async_telegram_unpin_message(
                    chat_id=t, message_id=message_id, bot_id=bot
                )

        async def handle_unpin_all_messages(call: ServiceCall) -> None:
            """Handle unpin_all_messages service call."""
            targets = _resolve_target(call)
            bot = _resolve_bot(call)

            for t in targets:
                await coordinator.api.async_telegram_unpin_all_messages(
                    chat_id=t, bot_id=bot
                )

        async def handle_create_forum_topic(call: ServiceCall) -> None:
            """Handle create_forum_topic service call."""
            targets = _resolve_target(call)
            name = call.data["name"]
            icon_color = call.data.get("icon_color")
            icon_custom_emoji_id = call.data.get("icon_custom_emoji_id")
            bot = _resolve_bot(call)

            for t in targets:
                await coordinator.api.async_telegram_create_forum_topic(
                    chat_id=t,
                    name=name,
                    icon_color=icon_color,
                    icon_custom_emoji_id=icon_custom_emoji_id,
                    bot_id=bot,
                )

        async def handle_edit_forum_topic(call: ServiceCall) -> None:
            """Handle edit_forum_topic service call."""
            targets = _resolve_target(call)
            message_thread_id = call.data["message_thread_id"]
            name = call.data.get("name")
            icon_custom_emoji_id = call.data.get("icon_custom_emoji_id")
            bot = _resolve_bot(call)

            for t in targets:
                await coordinator.api.async_telegram_edit_forum_topic(
                    chat_id=t,
                    message_thread_id=message_thread_id,
                    name=name,
                    icon_custom_emoji_id=icon_custom_emoji_id,
                    bot_id=bot,
                )

        async def handle_close_forum_topic(call: ServiceCall) -> None:
            """Handle close_forum_topic service call."""
            targets = _resolve_target(call)
            message_thread_id = call.data["message_thread_id"]
            bot = _resolve_bot(call)

            for t in targets:
                await coordinator.api.async_telegram_close_forum_topic(
                    chat_id=t, message_thread_id=message_thread_id, bot_id=bot
                )

        async def handle_reopen_forum_topic(call: ServiceCall) -> None:
            """Handle reopen_forum_topic service call."""
            targets = _resolve_target(call)
            message_thread_id = call.data["message_thread_id"]
            bot = _resolve_bot(call)

            for t in targets:
                await coordinator.api.async_telegram_reopen_forum_topic(
                    chat_id=t, message_thread_id=message_thread_id, bot_id=bot
                )

        async def handle_delete_forum_topic(call: ServiceCall) -> None:
            """Handle delete_forum_topic service call."""
            targets = _resolve_target(call)
            message_thread_id = call.data["message_thread_id"]
            bot = _resolve_bot(call)

            for t in targets:
                await coordinator.api.async_telegram_delete_forum_topic(
                    chat_id=t, message_thread_id=message_thread_id, bot_id=bot
                )

        async def handle_set_chat_title(call: ServiceCall) -> None:
            """Handle set_chat_title service call."""
            targets = _resolve_target(call)
            title = call.data["title"]
            bot = _resolve_bot(call)

            for t in targets:
                await coordinator.api.async_telegram_set_chat_title(
                    chat_id=t, title=title, bot_id=bot
                )

        async def handle_set_chat_description(call: ServiceCall) -> None:
            """Handle set_chat_description service call."""
            targets = _resolve_target(call)
            description = call.data["description"]
            bot = _resolve_bot(call)

            for t in targets:
                await coordinator.api.async_telegram_set_chat_description(
                    chat_id=t, description=description, bot_id=bot
                )

        async def handle_leave_chat(call: ServiceCall) -> None:
            """Handle leave_chat service call."""
            targets = _resolve_target(call)
            bot = _resolve_bot(call)
            for t in targets:
                await coordinator.api.async_telegram_leave_chat(chat_id=t, bot_id=bot)

        hass.services.async_register(DOMAIN, "send_message", handle_send_message)
        hass.services.async_register(DOMAIN, "send_photo", handle_send_photo)
        hass.services.async_register(DOMAIN, "send_video", handle_send_video)
        hass.services.async_register(DOMAIN, "send_document", handle_send_document)
        hass.services.async_register(DOMAIN, "send_animation", handle_send_animation)
        hass.services.async_register(DOMAIN, "send_voice", handle_send_voice)
        hass.services.async_register(DOMAIN, "send_audio", handle_send_audio)
        hass.services.async_register(DOMAIN, "send_sticker", handle_send_sticker)
        hass.services.async_register(
            DOMAIN, "send_chat_action", handle_send_chat_action
        )
        hass.services.async_register(DOMAIN, "send_video_note", handle_send_video_note)
        hass.services.async_register(DOMAIN, "send_dice", handle_send_dice)
        hass.services.async_register(DOMAIN, "send_location", handle_send_location)
        hass.services.async_register(DOMAIN, "send_venue", handle_send_venue)
        hass.services.async_register(DOMAIN, "send_contact", handle_send_contact)
        hass.services.async_register(DOMAIN, "send_poll", handle_send_poll)
        hass.services.async_register(DOMAIN, "stop_poll", handle_stop_poll)
        hass.services.async_register(DOMAIN, "edit_message", handle_edit_message)
        hass.services.async_register(DOMAIN, "edit_caption", handle_edit_caption)
        hass.services.async_register(
            DOMAIN, "edit_replymarkup", handle_edit_replymarkup
        )
        hass.services.async_register(
            DOMAIN, "edit_message_media", handle_edit_message_media
        )
        hass.services.async_register(
            DOMAIN, "edit_live_location", handle_edit_live_location
        )
        hass.services.async_register(
            DOMAIN, "stop_live_location", handle_stop_live_location
        )
        hass.services.async_register(
            DOMAIN, "set_message_reaction", handle_set_message_reaction
        )
        hass.services.async_register(DOMAIN, "forward_message", handle_forward_message)
        hass.services.async_register(DOMAIN, "copy_message", handle_copy_message)
        hass.services.async_register(DOMAIN, "pin_message", handle_pin_message)
        hass.services.async_register(DOMAIN, "unpin_message", handle_unpin_message)
        hass.services.async_register(
            DOMAIN, "unpin_all_messages", handle_unpin_all_messages
        )
        hass.services.async_register(
            DOMAIN, "create_forum_topic", handle_create_forum_topic
        )
        hass.services.async_register(
            DOMAIN, "edit_forum_topic", handle_edit_forum_topic
        )
        hass.services.async_register(
            DOMAIN, "close_forum_topic", handle_close_forum_topic
        )
        hass.services.async_register(
            DOMAIN, "reopen_forum_topic", handle_reopen_forum_topic
        )
        hass.services.async_register(
            DOMAIN, "delete_forum_topic", handle_delete_forum_topic
        )
        hass.services.async_register(DOMAIN, "set_chat_title", handle_set_chat_title)
        hass.services.async_register(
            DOMAIN, "set_chat_description", handle_set_chat_description
        )
        hass.services.async_register(DOMAIN, "delete_message", handle_delete_message)
        hass.services.async_register(
            DOMAIN, "answer_callback_query", handle_answer_callback_query
        )
        hass.services.async_register(DOMAIN, "leave_chat", handle_leave_chat)

    # Legacy & Bot Administration Services
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

    # Register admin services
    hass.services.async_register(DOMAIN, "ban_user", handle_ban_user)
    hass.services.async_register(DOMAIN, "unban_user", handle_unban_user)
    hass.services.async_register(DOMAIN, "mute_user", handle_mute_user)
    hass.services.async_register(DOMAIN, "warn_user", handle_warn_user)
    hass.services.async_register(DOMAIN, "broadcast", handle_broadcast)
    hass.services.async_register(DOMAIN, "adjust_reputation", handle_adjust_reputation)
    hass.services.async_register(DOMAIN, "apply_preset", handle_apply_preset)
    hass.services.async_register(DOMAIN, "sync_filters", handle_sync_filters)
    hass.services.async_register(
        DOMAIN, "maintenance_vacuum", handle_maintenance_vacuum
    )
    hass.services.async_register(
        DOMAIN, "maintenance_cleanup", handle_maintenance_cleanup
    )
    hass.services.async_register(DOMAIN, "maintenance_purge", handle_maintenance_purge)
    hass.services.async_register(
        DOMAIN, "maintenance_live_test", handle_maintenance_live_test
    )
    hass.services.async_register(
        DOMAIN, "mark_notifications_read", handle_mark_notifications_read
    )
    hass.services.async_register(DOMAIN, "whatsapp_action", handle_whatsapp_action)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    webhook_id = entry.data.get(CONF_WEBHOOK_ID) or f"{DOMAIN}_{entry.entry_id}"
    try:
        webhook.async_unregister(hass, webhook_id)
    except Exception:
        pass

    enable_telegram_proxy = entry.options.get(
        CONF_ENABLE_TELEGRAM_PROXY,
        entry.data.get(CONF_ENABLE_TELEGRAM_PROXY, True),
    )
    platforms = list(CORE_PLATFORMS)
    if enable_telegram_proxy:
        platforms.append(Platform.NOTIFY)

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, platforms):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
