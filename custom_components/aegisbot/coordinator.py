"""DataUpdateCoordinator for AegisBot."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AegisBotApiClient, AegisBotApiClientError
from .const import CONF_API_KEY, CONF_URL, DEFAULT_UPDATE_INTERVAL, DOMAIN, LOGGER


class AegisBotDataCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching AegisBot data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_UPDATE_INTERVAL),
        )
        self.entry = entry
        self.api = AegisBotApiClient(
            url=entry.data[CONF_URL],
            api_key=entry.data[CONF_API_KEY],
            session=async_get_clientsession(hass),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        try:
            # Fetch all required data in parallel
            (
                health,
                stats,
                groups,
                locks,
                intel,
                maintenance,
                whatsapp,
            ) = await asyncio.gather(
                self.api.async_get_data(),
                self.api.async_get_stats(),
                self.api.async_get_group_health(),
                self.api.async_get_all_locks(),
                self.api.async_get_security_intel(),
                self.api.async_get_maintenance_status(),
                self.api.async_get_whatsapp_status(),
                return_exceptions=True,
            )

            # Re-raise if critical endpoint failed with error
            if isinstance(health, Exception):
                raise health

            lock_map = {}
            if isinstance(locks, list):
                lock_map = {
                    lock_data["group_id"]: lock_data["locks"] for lock_data in locks
                }

            return {
                "health": health if isinstance(health, dict) else {},
                "stats": stats.get("data", {}) if isinstance(stats, dict) else {},
                "groups": {
                    (
                        int(g["group_id"])
                        if str(g.get("group_id", "")).lstrip("-").isdigit()
                        else g.get("group_id")
                    ): g
                    for g in (groups if isinstance(groups, list) else [])
                    if isinstance(g, dict) and "group_id" in g
                },
                "locks": lock_map,
                "intel": intel.get("data", {}) if isinstance(intel, dict) else {},
                "maintenance": (
                    maintenance.get("data", {})
                    if isinstance(maintenance, dict) and "data" in maintenance
                    else (maintenance if isinstance(maintenance, dict) else {})
                ),
                "whatsapp": (
                    whatsapp.get("data", {})
                    if isinstance(whatsapp, dict) and "data" in whatsapp
                    else (whatsapp if isinstance(whatsapp, dict) else {})
                ),
            }
        except AegisBotApiClientError as error:
            raise UpdateFailed(f"Error communicating with API: {error}") from error
        except Exception as error:
            raise UpdateFailed(f"Unexpected error: {error}") from error
