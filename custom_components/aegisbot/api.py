"""AegisBot API Client."""

from __future__ import annotations

import socket
from typing import Any

import aiohttp

try:
    from asyncio import timeout as asyncio_timeout
except ImportError:
    from async_timeout import timeout as asyncio_timeout  # type: ignore[no-redef]


class AegisBotApiClientError(Exception):
    """Exception to indicate a general API error."""


class AegisBotApiClientCommunicationError(AegisBotApiClientError):
    """Exception to indicate a communication error."""


class AegisBotApiClientAuthenticationError(AegisBotApiClientError):
    """Exception to indicate an authentication error."""


class AegisBotApiClient:
    """API Client for AegisBot."""

    def __init__(
        self,
        url: str,
        api_key: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """Sample API Client."""
        self._url = url.rstrip("/")
        self._api_key = api_key
        self._session = session

    async def async_get_data(self) -> dict:
        """Get data from the API."""
        return await self._api_wrapper(method="get", url=f"{self._url}/api/v1/health")

    async def async_get_all_locks(self) -> list[dict[str, Any]]:
        """Get all locks for all groups."""
        response = await self._api_wrapper(
            method="get", url=f"{self._url}/api/v1/locks/overview"
        )
        return response.get("data", [])

    async def async_get_security_intel(self) -> dict[str, Any]:
        """Get global security intelligence (threat map)."""
        return await self._api_wrapper(
            method="get", url=f"{self._url}/api/v1/groups/security/threat-map"
        )

    async def async_get_group_health(self) -> list[dict[str, Any]]:
        """Get health info for all groups."""
        response = await self._api_wrapper(
            method="get", url=f"{self._url}/api/v1/stats/analytics/group-health"
        )
        return response.get("data", [])

    async def async_get_stats(self) -> dict[str, Any]:
        """Get global statistics."""
        return await self._api_wrapper(
            method="get", url=f"{self._url}/api/v1/stats/overview"
        )

    async def async_get_locks(self, group_id: int) -> list[dict[str, Any]]:
        """Get locks for a group."""
        response = await self._api_wrapper(
            method="get", url=f"{self._url}/api/v1/locks/{group_id}"
        )
        return response.get("data", [])

    async def async_toggle_lock(
        self, group_id: int, lock_type: str, is_locked: bool
    ) -> dict:
        """Toggle a lock for a group."""
        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/locks/{group_id}/toggle",
            data={"lock_type": lock_type, "is_locked": is_locked},
        )

    async def async_sync_filters(self) -> dict:
        """Trigger global filter sync."""
        return await self._api_wrapper(
            method="post", url=f"{self._url}/api/v1/settings/sync"
        )

    async def async_send_message(
        self, group_id: int, text: str, message_thread_id: int | None = None
    ) -> dict:
        """Send a message to a group."""
        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/groups/{group_id}/message",
            data={"text": text, "message_thread_id": message_thread_id},
        )

    async def async_ban_user(
        self,
        group_id: int,
        user_id: int,
        duration: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Ban a user from a group."""
        data: dict[str, Any] = {"user_id": user_id}
        if duration:
            data["duration"] = duration
        if reason:
            data["reason"] = reason
        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/groups/{group_id}/ban",
            data=data,
        )

    async def async_unban_user(self, group_id: int, user_id: int) -> dict:
        """Unban a user from a group."""
        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/groups/{group_id}/unban",
            data={"user_id": user_id},
        )

    async def async_mute_user(
        self, group_id: int, user_id: int, duration: str, reason: str | None = None
    ) -> dict[str, Any]:
        """Mute a user in a group."""
        data: dict[str, Any] = {"user_id": user_id, "duration": duration}
        if reason:
            data["reason"] = reason
        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/groups/{group_id}/mute",
            data=data,
        )

    async def async_warn_user(self, group_id: int, user_id: int, reason: str) -> dict:
        """Warn a user in a group."""
        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/groups/{group_id}/warn",
            data={"user_id": user_id, "reason": reason},
        )

    async def async_broadcast(
        self,
        text: str,
        group_ids: list[int] | None = None,
        platform: str | None = None,
    ) -> dict[str, Any]:
        """Broadcast a message to multiple or all groups."""
        data: dict[str, Any] = {"text": text}
        if group_ids is not None:
            data["group_ids"] = group_ids
        if platform is not None:
            data["platform"] = platform
        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/broadcast",
            data=data,
        )

    async def async_get_reputation(self, user_id: int, group_id: int) -> dict[str, Any]:
        """Get reputation information for a user."""
        url = f"{self._url}/api/v1/reputation/{group_id}/member/{user_id}"
        return await self._api_wrapper(method="get", url=url)

    async def async_adjust_reputation(
        self,
        user_id: int,
        delta: int,
        reason: str | None = None,
        group_id: int | None = None,
    ) -> dict[str, Any]:
        """Adjust reputation score for a user."""
        gid = group_id or 0
        data: dict[str, Any] = {"score_delta": delta, "xp_delta": delta}
        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/reputation/{gid}/adjust/{user_id}",
            data=data,
        )

    async def async_apply_preset(
        self, group_id: int, preset_name: str
    ) -> dict[str, Any]:
        """Apply a security preset to a group."""
        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/templates/presets/apply/{preset_name}/{group_id}",
        )

    async def async_get_governance_report(
        self, group_id: int | None = None
    ) -> dict[str, Any]:
        """Get governance report."""
        gid = group_id or 1
        url = f"{self._url}/api/v1/report/governance/{gid}"
        return await self._api_wrapper(method="get", url=url)

    async def async_mark_notifications_read(
        self, notification_ids: list[str] | None = None
    ) -> dict[str, Any]:
        """Mark notifications as read."""
        if notification_ids:
            for notif_id in notification_ids:
                await self._api_wrapper(
                    method="post",
                    url=f"{self._url}/api/v1/notifications/{notif_id}/read",
                )
            return {"status": "success"}
        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/notifications/read-all",
        )

    async def async_maintenance_vacuum(self) -> dict[str, Any]:
        """Trigger database vacuum."""
        return await self._api_wrapper(
            method="post", url=f"{self._url}/api/v1/maintenance/vacuum"
        )

    async def async_maintenance_cleanup(
        self, days: int | None = None
    ) -> dict[str, Any]:
        """Trigger log and group cleanup."""
        data: dict[str, Any] = {}
        if days is not None:
            data["days"] = days
        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/maintenance/cleanup-groups",
            data=data if data else None,
        )

    async def async_maintenance_purge(self, group_id: int) -> dict[str, Any]:
        """Purge logs."""
        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/maintenance/purge-logs",
        )

    async def async_maintenance_live_test(self) -> dict[str, Any]:
        """Run maintenance live test suite."""
        return await self._api_wrapper(
            method="post", url=f"{self._url}/api/v1/maintenance/live-test-suite"
        )

    async def async_get_maintenance_status(self) -> dict[str, Any]:
        """Get maintenance status and database hygiene metrics."""
        return await self._api_wrapper(
            method="get", url=f"{self._url}/api/v1/maintenance/status"
        )

    async def async_get_whatsapp_status(self) -> dict[str, Any]:
        """Get WhatsApp integration status."""
        return await self._api_wrapper(
            method="get", url=f"{self._url}/api/v1/whatsapp/status"
        )

    async def async_whatsapp_action(
        self, action: str, data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Trigger a WhatsApp bridge action."""
        payload: dict[str, Any] = {"action": action}
        if data:
            payload["data"] = data
        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/whatsapp/action",
            data=payload,
        )

    # ------------------------------------------------------------------
    # Telegram Proxy API (1:1 telegram_bot parity + Modern Features)
    # ------------------------------------------------------------------

    async def async_telegram_send_message(
        self,
        chat_id: int | str,
        text: str,
        parse_mode: str | None = "HTML",
        reply_markup: Any = None,
        inline_keyboard: Any = None,
        keyboard: Any = None,
        disable_notification: bool = False,
        reply_to_message_id: int | None = None,
        message_thread_id: int | None = None,
        bot_id: int | str | None = None,
    ) -> dict[str, Any]:
        """Send a text message via Telegram."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_notification": disable_notification,
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        if inline_keyboard is not None:
            payload["inline_keyboard"] = inline_keyboard
        if keyboard is not None:
            payload["keyboard"] = keyboard
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        if message_thread_id is not None:
            payload["message_thread_id"] = message_thread_id
        if bot_id is not None:
            payload["bot_id"] = bot_id

        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/send_message",
            data=payload,
        )

    async def async_telegram_send_photo(
        self,
        chat_id: int | str,
        file: Any,
        caption: str | None = None,
        parse_mode: str | None = "HTML",
        reply_markup: Any = None,
        inline_keyboard: Any = None,
        keyboard: Any = None,
        disable_notification: bool = False,
        reply_to_message_id: int | None = None,
        message_thread_id: int | None = None,
        bot_id: int | str | None = None,
    ) -> dict[str, Any]:
        """Send a photo via Telegram."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "file": file,
            "disable_notification": disable_notification,
        }
        if caption is not None:
            payload["caption"] = caption
        if parse_mode is not None:
            payload["parse_mode"] = parse_mode
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        if inline_keyboard is not None:
            payload["inline_keyboard"] = inline_keyboard
        if keyboard is not None:
            payload["keyboard"] = keyboard
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        if message_thread_id is not None:
            payload["message_thread_id"] = message_thread_id
        if bot_id is not None:
            payload["bot_id"] = bot_id

        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/send_photo",
            data=payload,
        )

    async def async_telegram_send_video(
        self,
        chat_id: int | str,
        file: Any,
        caption: str | None = None,
        parse_mode: str | None = "HTML",
        reply_markup: Any = None,
        inline_keyboard: Any = None,
        keyboard: Any = None,
        disable_notification: bool = False,
        reply_to_message_id: int | None = None,
        message_thread_id: int | None = None,
        bot_id: int | str | None = None,
    ) -> dict[str, Any]:
        """Send a video via Telegram."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "file": file,
            "disable_notification": disable_notification,
        }
        if caption is not None:
            payload["caption"] = caption
        if parse_mode is not None:
            payload["parse_mode"] = parse_mode
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        if inline_keyboard is not None:
            payload["inline_keyboard"] = inline_keyboard
        if keyboard is not None:
            payload["keyboard"] = keyboard
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        if message_thread_id is not None:
            payload["message_thread_id"] = message_thread_id
        if bot_id is not None:
            payload["bot_id"] = bot_id

        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/send_video",
            data=payload,
        )

    async def async_telegram_send_document(
        self,
        chat_id: int | str,
        file: Any,
        caption: str | None = None,
        parse_mode: str | None = "HTML",
        reply_markup: Any = None,
        inline_keyboard: Any = None,
        keyboard: Any = None,
        disable_notification: bool = False,
        reply_to_message_id: int | None = None,
        message_thread_id: int | None = None,
        bot_id: int | str | None = None,
    ) -> dict[str, Any]:
        """Send a document/file via Telegram."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "file": file,
            "disable_notification": disable_notification,
        }
        if caption is not None:
            payload["caption"] = caption
        if parse_mode is not None:
            payload["parse_mode"] = parse_mode
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        if inline_keyboard is not None:
            payload["inline_keyboard"] = inline_keyboard
        if keyboard is not None:
            payload["keyboard"] = keyboard
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        if message_thread_id is not None:
            payload["message_thread_id"] = message_thread_id
        if bot_id is not None:
            payload["bot_id"] = bot_id

        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/send_document",
            data=payload,
        )

    async def async_telegram_send_animation(
        self,
        chat_id: int | str,
        file: Any,
        caption: str | None = None,
        parse_mode: str | None = "HTML",
        reply_markup: Any = None,
        inline_keyboard: Any = None,
        keyboard: Any = None,
        disable_notification: bool = False,
        reply_to_message_id: int | None = None,
        message_thread_id: int | None = None,
        bot_id: int | str | None = None,
    ) -> dict[str, Any]:
        """Send an animation (GIF) via Telegram."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "file": file,
            "disable_notification": disable_notification,
        }
        if caption is not None:
            payload["caption"] = caption
        if parse_mode is not None:
            payload["parse_mode"] = parse_mode
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        if inline_keyboard is not None:
            payload["inline_keyboard"] = inline_keyboard
        if keyboard is not None:
            payload["keyboard"] = keyboard
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        if message_thread_id is not None:
            payload["message_thread_id"] = message_thread_id
        if bot_id is not None:
            payload["bot_id"] = bot_id

        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/send_animation",
            data=payload,
        )

    async def async_telegram_send_voice(
        self,
        chat_id: int | str,
        file: Any,
        caption: str | None = None,
        parse_mode: str | None = "HTML",
        reply_markup: Any = None,
        inline_keyboard: Any = None,
        keyboard: Any = None,
        disable_notification: bool = False,
        reply_to_message_id: int | None = None,
        message_thread_id: int | None = None,
        bot_id: int | str | None = None,
    ) -> dict[str, Any]:
        """Send a voice audio message via Telegram."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "file": file,
            "caption": caption,
            "parse_mode": parse_mode,
            "disable_notification": disable_notification,
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        if inline_keyboard is not None:
            payload["inline_keyboard"] = inline_keyboard
        if keyboard is not None:
            payload["keyboard"] = keyboard
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        if message_thread_id is not None:
            payload["message_thread_id"] = message_thread_id
        if bot_id is not None:
            payload["bot_id"] = bot_id

        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/send_voice",
            data=payload,
        )

    async def async_telegram_send_location(
        self,
        chat_id: int | str,
        latitude: float,
        longitude: float,
        live_period: int | None = None,
        reply_markup: Any = None,
        inline_keyboard: Any = None,
        disable_notification: bool = False,
        reply_to_message_id: int | None = None,
        message_thread_id: int | None = None,
        bot_id: int | str | None = None,
    ) -> dict[str, Any]:
        """Send a location coordinate via Telegram."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "latitude": latitude,
            "longitude": longitude,
            "disable_notification": disable_notification,
        }
        if live_period is not None:
            payload["live_period"] = live_period
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        if inline_keyboard is not None:
            payload["inline_keyboard"] = inline_keyboard
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        if message_thread_id is not None:
            payload["message_thread_id"] = message_thread_id
        if bot_id is not None:
            payload["bot_id"] = bot_id

        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/send_location",
            data=payload,
        )

    async def async_telegram_send_poll(
        self,
        chat_id: int | str,
        question: str,
        options: list[str],
        is_anonymous: bool = True,
        poll_type: str = "regular",
        allows_multiple_answers: bool = False,
        correct_option_id: int | None = None,
        explanation: str | None = None,
        open_period: int | None = None,
        close_date: int | None = None,
        is_closed: bool | None = None,
        category: str = "general",
        reply_markup: Any = None,
        disable_notification: bool = False,
        reply_to_message_id: int | None = None,
        message_thread_id: int | None = None,
        bot_id: int | str | None = None,
    ) -> dict[str, Any]:
        """Send a native Telegram Poll with smart tracking."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "question": question,
            "options": options,
            "is_anonymous": is_anonymous,
            "poll_type": poll_type,
            "allows_multiple_answers": allows_multiple_answers,
            "category": category,
            "disable_notification": disable_notification,
        }
        if correct_option_id is not None:
            payload["correct_option_id"] = correct_option_id
        if explanation is not None:
            payload["explanation"] = explanation
        if open_period is not None:
            payload["open_period"] = open_period
        if close_date is not None:
            payload["close_date"] = close_date
        if is_closed is not None:
            payload["is_closed"] = is_closed
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        if message_thread_id is not None:
            payload["message_thread_id"] = message_thread_id
        if bot_id is not None:
            payload["bot_id"] = bot_id

        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/send_poll",
            data=payload,
        )

    async def async_telegram_stop_poll(
        self,
        chat_id: int | str,
        message_id: int,
        reply_markup: Any = None,
        bot_id: int | str | None = None,
    ) -> dict[str, Any]:
        """Stop an active Telegram poll and return final results."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        if bot_id is not None:
            payload["bot_id"] = bot_id

        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/stop_poll",
            data=payload,
        )

    async def async_telegram_edit_message_text(
        self,
        chat_id: int | str,
        message_id: int,
        text: str,
        parse_mode: str | None = "HTML",
        reply_markup: Any = None,
        inline_keyboard: Any = None,
        bot_id: int | str | None = None,
    ) -> dict[str, Any]:
        """Edit text of an existing message."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        if inline_keyboard is not None:
            payload["inline_keyboard"] = inline_keyboard
        if bot_id is not None:
            payload["bot_id"] = bot_id

        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/edit_message_text",
            data=payload,
        )

    async def async_telegram_edit_message_caption(
        self,
        chat_id: int | str,
        message_id: int,
        caption: str,
        parse_mode: str | None = "HTML",
        reply_markup: Any = None,
        inline_keyboard: Any = None,
        bot_id: int | str | None = None,
    ) -> dict[str, Any]:
        """Edit caption of an existing media message."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
            "caption": caption,
            "parse_mode": parse_mode,
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        if inline_keyboard is not None:
            payload["inline_keyboard"] = inline_keyboard
        if bot_id is not None:
            payload["bot_id"] = bot_id

        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/edit_message_caption",
            data=payload,
        )

    async def async_telegram_edit_message_reply_markup(
        self,
        chat_id: int | str,
        message_id: int,
        reply_markup: Any = None,
        inline_keyboard: Any = None,
        bot_id: int | str | None = None,
    ) -> dict[str, Any]:
        """Edit inline keyboard markup of an existing message."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        if inline_keyboard is not None:
            payload["inline_keyboard"] = inline_keyboard
        if bot_id is not None:
            payload["bot_id"] = bot_id

        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/edit_message_reply_markup",
            data=payload,
        )

    async def async_telegram_delete_message(
        self,
        chat_id: int | str,
        message_id: int,
        bot_id: int | str | None = None,
    ) -> dict[str, Any]:
        """Delete a message from a chat."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
        }
        if bot_id is not None:
            payload["bot_id"] = bot_id
        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/delete_message",
            data=payload,
        )

    async def async_telegram_answer_callback_query(
        self,
        callback_query_id: str,
        text: str | None = None,
        show_alert: bool = False,
        url: str | None = None,
        cache_time: int | None = None,
        bot_id: int | str | None = None,
    ) -> dict[str, Any]:
        """Send an answer to a callback query."""
        payload: dict[str, Any] = {
            "callback_query_id": callback_query_id,
            "show_alert": show_alert,
        }
        if text is not None:
            payload["text"] = text
        if url is not None:
            payload["url"] = url
        if cache_time is not None:
            payload["cache_time"] = cache_time
        if bot_id is not None:
            payload["bot_id"] = bot_id

        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/answer_callback_query",
            data=payload,
        )

    async def async_telegram_leave_chat(
        self,
        chat_id: int | str,
        bot_id: int | str | None = None,
    ) -> dict[str, Any]:
        """Leave a group or channel."""
        payload: dict[str, Any] = {"chat_id": chat_id}
        if bot_id is not None:
            payload["bot_id"] = bot_id
        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/leave_chat",
            data=payload,
        )

    async def async_telegram_get_me(
        self, bot_id: int | str | None = None
    ) -> dict[str, Any]:
        """Get Telegram bot profile details."""
        params = f"?bot_id={bot_id}" if bot_id is not None else ""
        return await self._api_wrapper(
            method="get",
            url=f"{self._url}/api/v1/telegram/get_me{params}",
        )

    async def async_telegram_send_audio(
        self,
        chat_id: int | str,
        audio: Any,
        caption: str | None = None,
        parse_mode: str | None = "HTML",
        duration: int | None = None,
        performer: str | None = None,
        title: str | None = None,
        reply_markup: Any = None,
        inline_keyboard: Any = None,
        keyboard: Any = None,
        disable_notification: bool = False,
        reply_to_message_id: int | None = None,
        message_thread_id: int | None = None,
        bot_id: int | str | None = None,
    ) -> dict[str, Any]:
        """Send audio track via Telegram."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "audio": audio,
            "disable_notification": disable_notification,
        }
        if caption is not None:
            payload["caption"] = caption
        if parse_mode is not None:
            payload["parse_mode"] = parse_mode
        if duration is not None:
            payload["duration"] = duration
        if performer is not None:
            payload["performer"] = performer
        if title is not None:
            payload["title"] = title
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        if inline_keyboard is not None:
            payload["inline_keyboard"] = inline_keyboard
        if keyboard is not None:
            payload["keyboard"] = keyboard
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        if message_thread_id is not None:
            payload["message_thread_id"] = message_thread_id
        if bot_id is not None:
            payload["bot_id"] = bot_id

        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/send_audio",
            data=payload,
        )

    async def async_telegram_send_sticker(
        self,
        chat_id: int | str,
        sticker: Any,
        reply_markup: Any = None,
        inline_keyboard: Any = None,
        keyboard: Any = None,
        disable_notification: bool = False,
        reply_to_message_id: int | None = None,
        message_thread_id: int | None = None,
        bot_id: int | str | None = None,
    ) -> dict[str, Any]:
        """Send sticker via Telegram."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "sticker": sticker,
            "disable_notification": disable_notification,
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        if inline_keyboard is not None:
            payload["inline_keyboard"] = inline_keyboard
        if keyboard is not None:
            payload["keyboard"] = keyboard
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        if message_thread_id is not None:
            payload["message_thread_id"] = message_thread_id
        if bot_id is not None:
            payload["bot_id"] = bot_id

        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/send_sticker",
            data=payload,
        )

    async def async_telegram_send_chat_action(
        self,
        chat_id: int | str,
        action: str = "typing",
        message_thread_id: int | None = None,
        bot_id: int | str | None = None,
    ) -> dict[str, Any]:
        """Send chat action indicator."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "action": action,
        }
        if message_thread_id is not None:
            payload["message_thread_id"] = message_thread_id
        if bot_id is not None:
            payload["bot_id"] = bot_id

        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/send_chat_action",
            data=payload,
        )

    async def async_telegram_send_video_note(
        self,
        chat_id: int | str,
        video_note: Any,
        duration: int | None = None,
        length: int | None = None,
        reply_markup: Any = None,
        inline_keyboard: Any = None,
        keyboard: Any = None,
        disable_notification: bool = False,
        reply_to_message_id: int | None = None,
        message_thread_id: int | None = None,
        bot_id: int | str | None = None,
    ) -> dict[str, Any]:
        """Send circular video note (Telescope)."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "video_note": video_note,
            "disable_notification": disable_notification,
        }
        if duration is not None:
            payload["duration"] = duration
        if length is not None:
            payload["length"] = length
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        if inline_keyboard is not None:
            payload["inline_keyboard"] = inline_keyboard
        if keyboard is not None:
            payload["keyboard"] = keyboard
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        if message_thread_id is not None:
            payload["message_thread_id"] = message_thread_id
        if bot_id is not None:
            payload["bot_id"] = bot_id

        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/send_video_note",
            data=payload,
        )

    async def async_telegram_send_dice(
        self,
        chat_id: int | str,
        emoji: str = "🎲",
        reply_markup: Any = None,
        inline_keyboard: Any = None,
        keyboard: Any = None,
        disable_notification: bool = False,
        reply_to_message_id: int | None = None,
        message_thread_id: int | None = None,
        bot_id: int | str | None = None,
    ) -> dict[str, Any]:
        """Send animated dice/game."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "emoji": emoji,
            "disable_notification": disable_notification,
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        if inline_keyboard is not None:
            payload["inline_keyboard"] = inline_keyboard
        if keyboard is not None:
            payload["keyboard"] = keyboard
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        if message_thread_id is not None:
            payload["message_thread_id"] = message_thread_id
        if bot_id is not None:
            payload["bot_id"] = bot_id

        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/send_dice",
            data=payload,
        )

    async def async_telegram_send_venue(
        self,
        chat_id: int | str,
        latitude: float,
        longitude: float,
        title: str,
        address: str,
        foursquare_id: str | None = None,
        foursquare_type: str | None = None,
        google_place_id: str | None = None,
        google_place_type: str | None = None,
        reply_markup: Any = None,
        inline_keyboard: Any = None,
        keyboard: Any = None,
        disable_notification: bool = False,
        reply_to_message_id: int | None = None,
        message_thread_id: int | None = None,
        bot_id: int | str | None = None,
    ) -> dict[str, Any]:
        """Send venue / POI."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "latitude": latitude,
            "longitude": longitude,
            "title": title,
            "address": address,
            "disable_notification": disable_notification,
        }
        if foursquare_id is not None:
            payload["foursquare_id"] = foursquare_id
        if foursquare_type is not None:
            payload["foursquare_type"] = foursquare_type
        if google_place_id is not None:
            payload["google_place_id"] = google_place_id
        if google_place_type is not None:
            payload["google_place_type"] = google_place_type
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        if inline_keyboard is not None:
            payload["inline_keyboard"] = inline_keyboard
        if keyboard is not None:
            payload["keyboard"] = keyboard
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        if message_thread_id is not None:
            payload["message_thread_id"] = message_thread_id
        if bot_id is not None:
            payload["bot_id"] = bot_id

        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/send_venue",
            data=payload,
        )

    async def async_telegram_send_contact(
        self,
        chat_id: int | str,
        phone_number: str,
        first_name: str,
        last_name: str | None = None,
        vcard: str | None = None,
        reply_markup: Any = None,
        inline_keyboard: Any = None,
        keyboard: Any = None,
        disable_notification: bool = False,
        reply_to_message_id: int | None = None,
        message_thread_id: int | None = None,
        bot_id: int | str | None = None,
    ) -> dict[str, Any]:
        """Send contact / vCard."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "phone_number": phone_number,
            "first_name": first_name,
            "disable_notification": disable_notification,
        }
        if last_name is not None:
            payload["last_name"] = last_name
        if vcard is not None:
            payload["vcard"] = vcard
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        if inline_keyboard is not None:
            payload["inline_keyboard"] = inline_keyboard
        if keyboard is not None:
            payload["keyboard"] = keyboard
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        if message_thread_id is not None:
            payload["message_thread_id"] = message_thread_id
        if bot_id is not None:
            payload["bot_id"] = bot_id

        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/send_contact",
            data=payload,
        )

    async def async_telegram_edit_message_media(
        self,
        chat_id: int | str,
        message_id: int,
        media: Any,
        media_type: str = "photo",
        caption: str | None = None,
        parse_mode: str | None = "HTML",
        reply_markup: Any = None,
        inline_keyboard: Any = None,
        bot_id: int | str | None = None,
    ) -> dict[str, Any]:
        """Edit message media in place (ideal for camera updates)."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
            "media": media,
            "media_type": media_type,
        }
        if caption is not None:
            payload["caption"] = caption
        if parse_mode is not None:
            payload["parse_mode"] = parse_mode
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        if inline_keyboard is not None:
            payload["inline_keyboard"] = inline_keyboard
        if bot_id is not None:
            payload["bot_id"] = bot_id

        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/edit_message_media",
            data=payload,
        )

    async def async_telegram_edit_live_location(
        self,
        chat_id: int | str,
        message_id: int,
        latitude: float,
        longitude: float,
        reply_markup: Any = None,
        inline_keyboard: Any = None,
        bot_id: int | str | None = None,
    ) -> dict[str, Any]:
        """Update live location coordinates."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
            "latitude": latitude,
            "longitude": longitude,
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        if inline_keyboard is not None:
            payload["inline_keyboard"] = inline_keyboard
        if bot_id is not None:
            payload["bot_id"] = bot_id

        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/edit_live_location",
            data=payload,
        )

    async def async_telegram_stop_live_location(
        self,
        chat_id: int | str,
        message_id: int,
        reply_markup: Any = None,
        inline_keyboard: Any = None,
        bot_id: int | str | None = None,
    ) -> dict[str, Any]:
        """Stop live location transmission."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        if inline_keyboard is not None:
            payload["inline_keyboard"] = inline_keyboard
        if bot_id is not None:
            payload["bot_id"] = bot_id

        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/stop_live_location",
            data=payload,
        )

    async def async_telegram_set_message_reaction(
        self,
        chat_id: int | str,
        message_id: int,
        reaction: str | list[str] = "👍",
        is_big: bool = False,
        bot_id: int | str | None = None,
    ) -> dict[str, Any]:
        """Set emoji reaction on message."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
            "reaction": reaction,
            "is_big": is_big,
        }
        if bot_id is not None:
            payload["bot_id"] = bot_id

        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/set_message_reaction",
            data=payload,
        )

    async def async_telegram_forward_message(
        self,
        chat_id: int | str,
        from_chat_id: int | str,
        message_id: int,
        disable_notification: bool = False,
        message_thread_id: int | None = None,
        bot_id: int | str | None = None,
    ) -> dict[str, Any]:
        """Forward message."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "from_chat_id": from_chat_id,
            "message_id": message_id,
            "disable_notification": disable_notification,
        }
        if message_thread_id is not None:
            payload["message_thread_id"] = message_thread_id
        if bot_id is not None:
            payload["bot_id"] = bot_id

        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/forward_message",
            data=payload,
        )

    async def async_telegram_copy_message(
        self,
        chat_id: int | str,
        from_chat_id: int | str,
        message_id: int,
        caption: str | None = None,
        parse_mode: str | None = "HTML",
        reply_markup: Any = None,
        inline_keyboard: Any = None,
        keyboard: Any = None,
        disable_notification: bool = False,
        message_thread_id: int | None = None,
        bot_id: int | str | None = None,
    ) -> dict[str, Any]:
        """Copy message."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "from_chat_id": from_chat_id,
            "message_id": message_id,
            "disable_notification": disable_notification,
        }
        if caption is not None:
            payload["caption"] = caption
        if parse_mode is not None:
            payload["parse_mode"] = parse_mode
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        if inline_keyboard is not None:
            payload["inline_keyboard"] = inline_keyboard
        if keyboard is not None:
            payload["keyboard"] = keyboard
        if message_thread_id is not None:
            payload["message_thread_id"] = message_thread_id
        if bot_id is not None:
            payload["bot_id"] = bot_id

        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/copy_message",
            data=payload,
        )

    async def async_telegram_pin_message(
        self,
        chat_id: int | str,
        message_id: int,
        disable_notification: bool = False,
        bot_id: int | str | None = None,
    ) -> dict[str, Any]:
        """Pin message in chat."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
            "disable_notification": disable_notification,
        }
        if bot_id is not None:
            payload["bot_id"] = bot_id

        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/pin_message",
            data=payload,
        )

    async def async_telegram_unpin_message(
        self,
        chat_id: int | str,
        message_id: int | None = None,
        bot_id: int | str | None = None,
    ) -> dict[str, Any]:
        """Unpin message in chat."""
        payload: dict[str, Any] = {"chat_id": chat_id}
        if message_id is not None:
            payload["message_id"] = message_id
        if bot_id is not None:
            payload["bot_id"] = bot_id

        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/unpin_message",
            data=payload,
        )

    async def async_telegram_unpin_all_messages(
        self,
        chat_id: int | str,
        bot_id: int | str | None = None,
    ) -> dict[str, Any]:
        """Unpin all messages in chat."""
        payload: dict[str, Any] = {"chat_id": chat_id}
        if bot_id is not None:
            payload["bot_id"] = bot_id

        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/unpin_all_messages",
            data=payload,
        )

    async def async_telegram_create_forum_topic(
        self,
        chat_id: int | str,
        name: str,
        icon_color: int | None = None,
        icon_custom_emoji_id: str | None = None,
        bot_id: int | str | None = None,
    ) -> dict[str, Any]:
        """Create forum topic in supergroup."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "name": name,
        }
        if icon_color is not None:
            payload["icon_color"] = icon_color
        if icon_custom_emoji_id is not None:
            payload["icon_custom_emoji_id"] = icon_custom_emoji_id
        if bot_id is not None:
            payload["bot_id"] = bot_id

        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/forum_topic/create",
            data=payload,
        )

    async def async_telegram_edit_forum_topic(
        self,
        chat_id: int | str,
        message_thread_id: int,
        name: str | None = None,
        icon_custom_emoji_id: str | None = None,
        bot_id: int | str | None = None,
    ) -> dict[str, Any]:
        """Edit forum topic."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "message_thread_id": message_thread_id,
        }
        if name is not None:
            payload["name"] = name
        if icon_custom_emoji_id is not None:
            payload["icon_custom_emoji_id"] = icon_custom_emoji_id
        if bot_id is not None:
            payload["bot_id"] = bot_id

        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/forum_topic/edit",
            data=payload,
        )

    async def async_telegram_close_forum_topic(
        self,
        chat_id: int | str,
        message_thread_id: int,
        bot_id: int | str | None = None,
    ) -> dict[str, Any]:
        """Close forum topic."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "message_thread_id": message_thread_id,
        }
        if bot_id is not None:
            payload["bot_id"] = bot_id

        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/forum_topic/close",
            data=payload,
        )

    async def async_telegram_reopen_forum_topic(
        self,
        chat_id: int | str,
        message_thread_id: int,
        bot_id: int | str | None = None,
    ) -> dict[str, Any]:
        """Reopen forum topic."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "message_thread_id": message_thread_id,
        }
        if bot_id is not None:
            payload["bot_id"] = bot_id

        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/forum_topic/reopen",
            data=payload,
        )

    async def async_telegram_delete_forum_topic(
        self,
        chat_id: int | str,
        message_thread_id: int,
        bot_id: int | str | None = None,
    ) -> dict[str, Any]:
        """Delete forum topic."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "message_thread_id": message_thread_id,
        }
        if bot_id is not None:
            payload["bot_id"] = bot_id

        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/forum_topic/delete",
            data=payload,
        )

    async def async_telegram_set_chat_title(
        self,
        chat_id: int | str,
        title: str,
        bot_id: int | str | None = None,
    ) -> dict[str, Any]:
        """Set chat title."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "title": title,
        }
        if bot_id is not None:
            payload["bot_id"] = bot_id

        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/chat/set_title",
            data=payload,
        )

    async def async_telegram_set_chat_description(
        self,
        chat_id: int | str,
        description: str,
        bot_id: int | str | None = None,
    ) -> dict[str, Any]:
        """Set chat description."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "description": description,
        }
        if bot_id is not None:
            payload["bot_id"] = bot_id

        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/chat/set_description",
            data=payload,
        )

    async def async_get_telegram_bots(self) -> list[dict[str, Any]]:
        """Get all configured Telegram bots from AegisBot."""
        res = await self._api_wrapper(
            method="get",
            url=f"{self._url}/api/v1/telegram/bots",
        )
        return res.get("bots", [])

    async def async_sync_commands(
        self, commands: list[dict[str, str]], bot_id: int | str | None = None
    ) -> dict[str, Any]:
        """Sync commands to Telegram bot."""
        payload: dict[str, Any] = {"commands": commands}
        if bot_id is not None:
            payload["bot_id"] = bot_id
        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/sync_commands",
            data=payload,
        )

    async def async_telegram_get_allowed_chats(self) -> list[Any]:
        """Get allowed chat IDs from AegisBot."""
        res = await self._api_wrapper(
            method="get",
            url=f"{self._url}/api/v1/telegram/allowed_chats",
        )
        return res.get("allowed_chat_ids", [])

    async def async_telegram_set_allowed_chats(
        self, allowed_chat_ids: list[Any] | str
    ) -> dict[str, Any]:
        """Sync allowed chat IDs to AegisBot."""
        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/allowed_chats",
            data={"allowed_chat_ids": allowed_chat_ids},
        )

    async def async_register_ha_webhook(
        self,
        webhook_id: str,
        ha_url: str | None = None,
        allowed_chat_ids: list[Any] | str | None = None,
    ) -> dict[str, Any]:
        """Register Home Assistant Webhook ID with AegisBot for real-time event push."""
        payload: dict[str, Any] = {"webhook_id": webhook_id}
        if ha_url:
            payload["ha_url"] = ha_url
        if allowed_chat_ids is not None:
            payload["allowed_chat_ids"] = allowed_chat_ids

        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/register_webhook",
            data=payload,
        )

    async def _api_wrapper(
        self,
        method: str,
        url: str,
        data: dict | None = None,
        headers: dict | None = None,
    ) -> Any:
        """Get information from the API."""
        if headers is None:
            headers = {}
        headers["Authorization"] = f"Bearer {self._api_key}"

        try:
            # Use asyncio_timeout for modern Python / Home Assistant compatibility
            async with asyncio_timeout(10):
                response = await self._session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data,
                )
                if response.status in (401, 403):
                    raise AegisBotApiClientAuthenticationError(
                        "Invalid credentials",
                    )
                response.raise_for_status()
                return await response.json()

        except TimeoutError as exception:
            raise AegisBotApiClientCommunicationError(
                "Timeout error fetching information from API",
            ) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            raise AegisBotApiClientCommunicationError(
                "Error fetching information from API",
            ) from exception
        except AegisBotApiClientError:
            raise
        except Exception as exception:  # pylint: disable=broad-except
            raise AegisBotApiClientError(
                f"Unexpected error: {exception}"
            ) from exception
