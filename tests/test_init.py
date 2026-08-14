"""Tests for AegisBot setup."""

from unittest.mock import patch

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
        assert hass.services.has_service(DOMAIN, "broadcast")
        assert hass.services.has_service(DOMAIN, "adjust_reputation")
        assert hass.services.has_service(DOMAIN, "apply_preset")
        assert hass.services.has_service(DOMAIN, "maintenance_cleanup")
        assert hass.services.has_service(DOMAIN, "maintenance_purge")
        assert hass.services.has_service(DOMAIN, "mark_notifications_read")
        assert hass.services.has_service(DOMAIN, "whatsapp_action")

        # Test calling services
        await hass.services.async_call(
            DOMAIN,
            "broadcast",
            {"text": "test broadcast", "group_ids": [1], "platform": "telegram"},
            blocking=True,
        )
        mock_api.async_broadcast.assert_called_once_with(
            text="test broadcast", group_ids=[1], platform="telegram"
        )

        await hass.services.async_call(
            DOMAIN,
            "adjust_reputation",
            {"user_id": 123, "delta": 5, "reason": "good", "group_id": 1},
            blocking=True,
        )
        mock_api.async_adjust_reputation.assert_called_once_with(
            user_id=123, delta=5, reason="good", group_id=1
        )

        await hass.services.async_call(
            DOMAIN,
            "apply_preset",
            {"group_id": 1, "preset_name": "strict"},
            blocking=True,
        )
        mock_api.async_apply_preset.assert_called_once_with(
            group_id=1, preset_name="strict"
        )

        await hass.services.async_call(
            DOMAIN,
            "maintenance_cleanup",
            {"days": 30},
            blocking=True,
        )
        mock_api.async_maintenance_cleanup.assert_called_once_with(days=30)

        await hass.services.async_call(
            DOMAIN,
            "maintenance_purge",
            {"group_id": 1},
            blocking=True,
        )
        mock_api.async_maintenance_purge.assert_called_once_with(group_id=1)

        await hass.services.async_call(
            DOMAIN,
            "mark_notifications_read",
            {"notification_ids": ["n1"]},
            blocking=True,
        )
        mock_api.async_mark_notifications_read.assert_called_once_with(
            notification_ids=["n1"]
        )

        await hass.services.async_call(
            DOMAIN,
            "whatsapp_action",
            {"action": "reconnect", "data": {"force": True}},
            blocking=True,
        )
        mock_api.async_whatsapp_action.assert_called_once_with(
            action="reconnect", data={"force": True}
        )
