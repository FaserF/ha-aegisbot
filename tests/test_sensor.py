"""Tests for AegisBot sensors."""

from unittest.mock import patch

import pytest

from custom_components.aegisbot.const import DOMAIN


async def test_sensors(hass, mock_api):
    """Test standard sensors."""
    with patch(
        "custom_components.aegisbot.coordinator.AegisBotApiClient",
        return_value=mock_api,
    ):
        mock_api.async_get_data.return_value = {"status": "healthy"}
        mock_api.async_get_stats.return_value = {
            "data": {"protected_groups": 5, "active_warnings": 2}
        }
        mock_api.async_get_group_health.return_value = [
            {"group_id": 1, "title": "Test Group", "health_score": 90}
        ]
        mock_api.async_get_all_locks.return_value = [{"group_id": 1, "locks": []}]
        mock_api.async_get_security_intel.return_value = {
            "data": {"stats": {"total_alerts": 3, "sync_points": 1}}
        }

        entry = pytest.MockConfigEntry(
            domain=DOMAIN,
            data={"url": "http://example.com", "api_key": "api_key"},
            entry_id="test_entry",
        )
        entry.add_to_hass(hass)

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        # Check global sensors
        state = hass.states.get("sensor.aegisbot_system_protected_groups")
        assert state
        assert state.state == "5"

        state = hass.states.get("sensor.aegisbot_system_active_warnings")
        assert state
        assert state.state == "2"

        # Check group sensors
        state = hass.states.get("sensor.group_test_group_health_score")
        assert state
        assert state.state == "90"
