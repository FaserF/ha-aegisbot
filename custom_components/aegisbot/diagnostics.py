"""Diagnostics support for AegisBot."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_API_KEY, DOMAIN
from .coordinator import AegisBotDataCoordinator

REDACT_CONFIG = {CONF_API_KEY}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: AegisBotDataCoordinator = hass.data[DOMAIN][entry.entry_id]

    return {
        "config_entry": async_redact_data(entry.as_dict(), REDACT_CONFIG),
        "coordinator_data": coordinator.data,
    }
