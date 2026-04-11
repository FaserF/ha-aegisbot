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
            method="get", url=f"{self._url}/api/v1/admin/groups/security/threat-map"
        )

    async def async_get_group_health(self) -> list[dict[str, Any]]:
        """Get health info for all groups."""
        response = await self._api_wrapper(
            method="get", url=f"{self._url}/api/v1/stats/analytics/group-health"
        )
        return response.get("data", [])

    async def async_get_stats(self) -> dict[str, Any]:
        """Get global statistics."""
        return await self._api_wrapper(method="get", url=f"{self._url}/api/v1/stats")

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
        except Exception as exception:  # pylint: disable=broad-except
            raise AegisBotApiClientError(
                "Something really wrong happened!"
            ) from exception
