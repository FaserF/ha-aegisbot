"""Tests for AegisBot binary sensors."""

from unittest.mock import patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.aegisbot.const import DOMAIN


async def test_binary_sensors(hass, mock_api):
    """Test binary sensors."""
    with patch(
        "custom_components.aegisbot.coordinator.AegisBotApiClient",
        return_value=mock_api,
    ):
        mock_api.async_get_data.return_value = {
            "status": "healthy",
            "infrastructure": {"database": "healthy"},
        }
        mock_api.async_get_stats.return_value = {"data": {}}
        mock_api.async_get_group_health.return_value = [
            {"group_id": 1, "title": "Test Group", "platform": "telegram"}
        ]
        mock_api.async_get_all_locks.return_value = [{"group_id": 1, "locks": []}]
        mock_api.async_get_security_intel.return_value = {
            "data": {"stats": {"active_raids": 0}}
        }

        entry = MockConfigEntry(
            domain=DOMAIN,
            data={"url": "http://example.com", "api_key": "api_key"},
            entry_id="test_entry",
        )
        entry.add_to_hass(hass)

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        # Check global binary sensors
        state = hass.states.get("binary_sensor.aegisbot_system_global_status")
        assert state
        assert state.state == "on"

        state = hass.states.get("binary_sensor.aegisbot_system_active_raid_detected")
        assert state
        assert state.state == "off"

        # Check group binary sensors
        state = hass.states.get("binary_sensor.group_test_group_group_active")
        assert state
        assert state.state == "on"
