"""AegisBot API Client."""

from __future__ import annotations

import socket
from typing import Any

import aiohttp
import async_timeout


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
    # Telegram Bot API Proxy Methods (1:1 with telegram_bot)
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

        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/send_message",
            data=payload,
        )

    async def async_telegram_send_photo(
        self,
        chat_id: int | str,
        file: str,
        caption: str | None = None,
        parse_mode: str | None = "HTML",
        reply_markup: Any = None,
        inline_keyboard: Any = None,
        keyboard: Any = None,
        disable_notification: bool = False,
        reply_to_message_id: int | None = None,
        message_thread_id: int | None = None,
    ) -> dict[str, Any]:
        """Send a photo via Telegram."""
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

        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/send_photo",
            data=payload,
        )

    async def async_telegram_send_video(
        self,
        chat_id: int | str,
        file: str,
        caption: str | None = None,
        parse_mode: str | None = "HTML",
        reply_markup: Any = None,
        inline_keyboard: Any = None,
        keyboard: Any = None,
        disable_notification: bool = False,
        reply_to_message_id: int | None = None,
        message_thread_id: int | None = None,
    ) -> dict[str, Any]:
        """Send a video via Telegram."""
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

        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/send_video",
            data=payload,
        )

    async def async_telegram_send_document(
        self,
        chat_id: int | str,
        file: str,
        caption: str | None = None,
        parse_mode: str | None = "HTML",
        reply_markup: Any = None,
        inline_keyboard: Any = None,
        keyboard: Any = None,
        disable_notification: bool = False,
        reply_to_message_id: int | None = None,
        message_thread_id: int | None = None,
    ) -> dict[str, Any]:
        """Send a document/file via Telegram."""
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

        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/send_document",
            data=payload,
        )

    async def async_telegram_send_animation(
        self,
        chat_id: int | str,
        file: str,
        caption: str | None = None,
        parse_mode: str | None = "HTML",
        reply_markup: Any = None,
        inline_keyboard: Any = None,
        keyboard: Any = None,
        disable_notification: bool = False,
        reply_to_message_id: int | None = None,
        message_thread_id: int | None = None,
    ) -> dict[str, Any]:
        """Send an animation (GIF) via Telegram."""
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

        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/send_animation",
            data=payload,
        )

    async def async_telegram_send_voice(
        self,
        chat_id: int | str,
        file: str,
        caption: str | None = None,
        parse_mode: str | None = "HTML",
        reply_markup: Any = None,
        inline_keyboard: Any = None,
        keyboard: Any = None,
        disable_notification: bool = False,
        reply_to_message_id: int | None = None,
        message_thread_id: int | None = None,
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
    ) -> dict[str, Any]:
        """Stop an active Telegram poll and return final results."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup

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

        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/edit_message_reply_markup",
            data=payload,
        )

    async def async_telegram_delete_message(
        self,
        chat_id: int | str,
        message_id: int,
    ) -> dict[str, Any]:
        """Delete a message from a chat."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
        }
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

        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/answer_callback_query",
            data=payload,
        )

    async def async_telegram_leave_chat(
        self,
        chat_id: int | str,
    ) -> dict[str, Any]:
        """Leave a group or channel."""
        payload: dict[str, Any] = {"chat_id": chat_id}
        return await self._api_wrapper(
            method="post",
            url=f"{self._url}/api/v1/telegram/leave_chat",
            data=payload,
        )

    async def async_telegram_get_me(self) -> dict[str, Any]:
        """Get Telegram bot profile details."""
        return await self._api_wrapper(
            method="get",
            url=f"{self._url}/api/v1/telegram/get_me",
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
            async with async_timeout.timeout(10):
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
