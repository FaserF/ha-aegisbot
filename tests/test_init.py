"""Tests for AegisBot setup."""

from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.aegisbot.const import DOMAIN


async def test_setup_unload_entry(hass, mock_api):
    """Test setup and unload of the config entry."""
    with patch(
        "custom_components.aegisbot.coordinator.AegisBotApiClient",
        return_value=mock_api,
    ):
        mock_api.async_get_data.return_value = {"status": "healthy"}
        mock_api.async_get_stats.return_value = {"data": {}}
        mock_api.async_get_group_health.return_value = []
        mock_api.async_get_all_locks.return_value = []
        mock_api.async_get_security_intel.return_value = {"data": {"stats": {}}}

        entry = MockConfigEntry(
            domain=DOMAIN,
            data={"url": "http://example.com", "api_key": "api_key"},
            entry_id="test_entry",
        )
        entry.add_to_hass(hass)

        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        assert DOMAIN in hass.data
        assert entry.entry_id in hass.data[DOMAIN]

        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()

        assert entry.entry_id not in hass.data[DOMAIN]


async def test_services_registration(hass, mock_api):
    """Test service registration."""
    with patch(
        "custom_components.aegisbot.coordinator.AegisBotApiClient",
        return_value=mock_api,
    ):
        mock_api.async_get_data.return_value = {"status": "healthy"}
        mock_api.async_get_stats.return_value = {"data": {}}
        mock_api.async_get_group_health.return_value = []
        mock_api.async_get_all_locks.return_value = []
        mock_api.async_get_security_intel.return_value = {"data": {"stats": {}}}

        entry = MockConfigEntry(
            domain=DOMAIN,
            data={"url": "http://example.com", "api_key": "api_key"},
            entry_id="test_entry",
        )
        entry.add_to_hass(hass)

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        assert hass.services.has_service(DOMAIN, "send_message")
        assert hass.services.has_service(DOMAIN, "ban_user")
        assert hass.services.has_service(DOMAIN, "unban_user")
        assert hass.services.has_service(DOMAIN, "mute_user")
        assert hass.services.has_service(DOMAIN, "warn_user")
