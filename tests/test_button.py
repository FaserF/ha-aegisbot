"""Tests for AegisBot buttons."""

from unittest.mock import patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.aegisbot.const import DOMAIN


async def test_buttons(hass, mock_api):
    """Test button platform."""
    with patch(
        "custom_components.aegisbot.coordinator.AegisBotApiClient",
        return_value=mock_api,
    ):
        mock_api.async_get_data.return_value = {"status": "healthy"}
        mock_api.async_get_stats.return_value = {"data": {}}
        mock_api.async_get_group_health.return_value = []
        mock_api.async_get_all_locks.return_value = []
        mock_api.async_get_security_intel.return_value = {"data": {"stats": {}}}
        mock_api.async_get_maintenance_status.return_value = {"data": {}}
        mock_api.async_get_whatsapp_status.return_value = {"data": {}}

        entry = MockConfigEntry(
            domain=DOMAIN,
            data={"url": "http://example.com", "api_key": "api_key"},
            entry_id="test_entry",
        )
        entry.add_to_hass(hass)

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        # Test sync_filters button press
        await hass.services.async_call(
            "button",
            "press",
            {"entity_id": "button.aegisbot_system_sync_global_filters"},
            blocking=True,
        )
        mock_api.async_sync_filters.assert_called_once()

        # Test maintenance_vacuum button press
        await hass.services.async_call(
            "button",
            "press",
            {"entity_id": "button.aegisbot_system_vacuum_database"},
            blocking=True,
        )
        mock_api.async_maintenance_vacuum.assert_called_once()

        # Test maintenance_live_test button press
        await hass.services.async_call(
            "button",
            "press",
            {"entity_id": "button.aegisbot_system_run_maintenance_live_test"},
            blocking=True,
        )
        mock_api.async_maintenance_live_test.assert_called_once()
