"""Notify platform for AegisBot (1:1 Telegram compatible)."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.notify import (
    ATTR_DATA,
    ATTR_MESSAGE,
    ATTR_TARGET,
    ATTR_TITLE,
    BaseNotificationService,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import CONF_ALLOWED_CHAT_IDS, DOMAIN
from .coordinator import AegisBotDataCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_get_service(
    hass: HomeAssistant,
    config: ConfigType,
    discovery_info: DiscoveryInfoType | None = None,
) -> BaseNotificationService | None:
    """Get the AegisBot notification service."""
    if discovery_info is None:
        return None

    entry_id = discovery_info.get("entry_id")
    coordinator: AegisBotDataCoordinator = hass.data[DOMAIN].get(entry_id)
    if not coordinator:
        return None

    default_chat_ids = discovery_info.get(CONF_ALLOWED_CHAT_IDS, [])
    return AegisBotNotificationService(coordinator, default_chat_ids)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: Any,
) -> None:
    """Set up the notify platform for AegisBot."""
    # ConfigEntry notify setup is handled through async_get_service / forward setups
    pass


class AegisBotNotificationService(BaseNotificationService):
    """Implement the notification service for AegisBot."""

    def __init__(
        self,
        coordinator: AegisBotDataCoordinator,
        default_chat_ids: list[Any] | None = None,
    ) -> None:
        """Initialize the service."""
        self.coordinator = coordinator
        self.api = coordinator.api
        self.default_chat_ids = default_chat_ids or []

    async def async_send_message(
        self,
        message: str = "",
        **kwargs: Any,
    ) -> None:
        """Send a message to one or multiple Telegram targets."""
        targets = kwargs.get(ATTR_TARGET) or self.default_chat_ids
        if not targets:
            _LOGGER.warning("No target chat_id specified for AegisBot notification.")
            return

        if not isinstance(targets, list):
            targets = [targets]

        title = kwargs.get(ATTR_TITLE)
        data = kwargs.get(ATTR_DATA) or {}

        # Merge title and message if title present
        full_text = f"<b>{title}</b>\n{message}" if title else message

        parse_mode = data.get("parse_mode", "HTML")
        inline_keyboard = data.get("inline_keyboard")
        keyboard = data.get("keyboard")
        reply_markup = data.get("reply_markup")
        disable_notification = data.get("disable_notification", False)
        reply_to_message_id = data.get("reply_to_message_id")
        message_thread_id = data.get("message_thread_id")

        for target in targets:
            try:
                # 1. Photo
                if "photo" in data or "url" in data and any(data.get("url", "").endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                    photo_url = data.get("photo") or data.get("url")
                    caption = data.get("caption", full_text)
                    await self.api.async_telegram_send_photo(
                        chat_id=target,
                        file=photo_url,
                        caption=caption,
                        parse_mode=parse_mode,
                        reply_markup=reply_markup,
                        inline_keyboard=inline_keyboard,
                        keyboard=keyboard,
                        disable_notification=disable_notification,
                        reply_to_message_id=reply_to_message_id,
                        message_thread_id=message_thread_id,
                    )
                # 2. Video
                elif "video" in data:
                    await self.api.async_telegram_send_video(
                        chat_id=target,
                        file=data["video"],
                        caption=data.get("caption", full_text),
                        parse_mode=parse_mode,
                        reply_markup=reply_markup,
                        inline_keyboard=inline_keyboard,
                        keyboard=keyboard,
                        disable_notification=disable_notification,
                        reply_to_message_id=reply_to_message_id,
                        message_thread_id=message_thread_id,
                    )
                # 3. Document / File
                elif "document" in data or "file" in data:
                    doc_file = data.get("document") or data.get("file")
                    await self.api.async_telegram_send_document(
                        chat_id=target,
                        file=doc_file,
                        caption=data.get("caption", full_text),
                        parse_mode=parse_mode,
                        reply_markup=reply_markup,
                        inline_keyboard=inline_keyboard,
                        keyboard=keyboard,
                        disable_notification=disable_notification,
                        reply_to_message_id=reply_to_message_id,
                        message_thread_id=message_thread_id,
                    )
                # 4. Animation / GIF
                elif "animation" in data:
                    await self.api.async_telegram_send_animation(
                        chat_id=target,
                        file=data["animation"],
                        caption=data.get("caption", full_text),
                        parse_mode=parse_mode,
                        reply_markup=reply_markup,
                        inline_keyboard=inline_keyboard,
                        keyboard=keyboard,
                        disable_notification=disable_notification,
                        reply_to_message_id=reply_to_message_id,
                        message_thread_id=message_thread_id,
                    )
                # 5. Location
                elif "location" in data or ("latitude" in data and "longitude" in data):
                    lat = data.get("latitude") or data.get("location", {}).get("latitude")
                    lon = data.get("longitude") or data.get("location", {}).get("longitude")
                    await self.api.async_telegram_send_location(
                        chat_id=target,
                        latitude=float(lat),
                        longitude=float(lon),
                        live_period=data.get("live_period"),
                        reply_markup=reply_markup,
                        inline_keyboard=inline_keyboard,
                        disable_notification=disable_notification,
                        reply_to_message_id=reply_to_message_id,
                        message_thread_id=message_thread_id,
                    )
                # 6. Poll
                elif "poll" in data:
                    poll_cfg = data["poll"]
                    await self.api.async_telegram_send_poll(
                        chat_id=target,
                        question=poll_cfg.get("question", full_text),
                        options=poll_cfg.get("options", []),
                        is_anonymous=poll_cfg.get("is_anonymous", True),
                        poll_type=poll_cfg.get("type", "regular"),
                        allows_multiple_answers=poll_cfg.get("allows_multiple_answers", False),
                        correct_option_id=poll_cfg.get("correct_option_id"),
                        explanation=poll_cfg.get("explanation"),
                        category=poll_cfg.get("category", "general"),
                        reply_markup=reply_markup,
                        disable_notification=disable_notification,
                        reply_to_message_id=reply_to_message_id,
                        message_thread_id=message_thread_id,
                    )
                # 7. Standard Text Message
                else:
                    await self.api.async_telegram_send_message(
                        chat_id=target,
                        text=full_text,
                        parse_mode=parse_mode,
                        reply_markup=reply_markup,
                        inline_keyboard=inline_keyboard,
                        keyboard=keyboard,
                        disable_notification=disable_notification,
                        reply_to_message_id=reply_to_message_id,
                        message_thread_id=message_thread_id,
                    )
            except Exception as err:
                _LOGGER.error("Failed to deliver AegisBot notification to %s: %s", target, err)
