"""Tests for AegisBot sensors."""

from unittest.mock import patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.aegisbot.const import DOMAIN


async def test_sensors(hass, mock_api):
    """Test standard sensors."""
    with patch(
        "custom_components.aegisbot.coordinator.AegisBotApiClient",
        return_value=mock_api,
    ):
        mock_api.async_get_data.return_value = {"status": "healthy"}
        mock_api.async_get_stats.return_value = {
            "data": {"protected_groups": 5, "active_warnings": 2, "total_users": 100}
        }
        mock_api.async_get_group_health.return_value = [
            {
                "group_id": 1,
                "title": "Test Group",
                "health_score": 90,
                "platform": "telegram",
                "member_count": 50,
            }
        ]
        mock_api.async_get_all_locks.return_value = [{"group_id": 1, "locks": []}]
        mock_api.async_get_security_intel.return_value = {
            "data": {
                "stats": {
                    "total_alerts": 3,
                    "sync_points": 1,
                    "active_raids": 0,
                    "threat_level": "low",
                }
            }
        }
        mock_api.async_get_maintenance_status.return_value = {
            "data": {"db_size_mb": 42, "event_backlog": 0, "table_count": 10}
        }
        mock_api.async_get_whatsapp_status.return_value = {
            "data": {"status": "connected"}
        }

        entry = MockConfigEntry(
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
        assert state.attributes.get("total_users") == 100

        state = hass.states.get("sensor.aegisbot_system_active_warnings")
        assert state
        assert state.state == "2"

        state = hass.states.get("sensor.aegisbot_system_active_security_signals")
        assert state
        assert state.state == "3"
        assert state.attributes.get("threat_level") == "low"

        # Check group sensors
        state = hass.states.get("sensor.group_test_group_health_score")
        assert state
        assert state.state == "90"
        assert state.attributes.get("platform") == "telegram"
        assert state.attributes.get("member_count") == 50
