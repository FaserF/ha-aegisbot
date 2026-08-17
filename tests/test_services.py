"""Tests for AegisBot Home Assistant services."""

from unittest.mock import AsyncMock, patch
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.aegisbot.const import DOMAIN


async def test_telegram_services_execution(hass):
    """Test all Telegram service calls registered by AegisBot."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"url": "http://127.0.0.1:8077", "api_key": "test_key"},
        entry_id="test_services_entry",
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.aegisbot.coordinator.AegisBotApiClient.async_get_data",
        return_value={"status": "healthy"},
    ), patch(
        "custom_components.aegisbot.coordinator.AegisBotApiClient.async_get_stats",
        return_value={"data": {}},
    ), patch(
        "custom_components.aegisbot.coordinator.AegisBotApiClient.async_get_all_locks",
        return_value=[],
    ), patch(
        "custom_components.aegisbot.coordinator.AegisBotApiClient.async_get_group_health",
        return_value=[],
    ), patch(
        "custom_components.aegisbot.coordinator.AegisBotApiClient.async_get_security_intel",
        return_value={},
    ), patch(
        "custom_components.aegisbot.coordinator.AegisBotApiClient.async_register_ha_webhook",
        return_value={"success": True},
    ), patch(
        "custom_components.aegisbot.coordinator.AegisBotApiClient.async_telegram_get_allowed_chats",
        return_value=[-100123],
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    coordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.api.async_telegram_send_message = AsyncMock(return_value={"success": True})
    coordinator.api.async_telegram_send_photo = AsyncMock(return_value={"success": True})
    coordinator.api.async_telegram_send_poll = AsyncMock(return_value={"success": True})
    coordinator.api.async_telegram_stop_poll = AsyncMock(return_value={"success": True})
    coordinator.api.async_telegram_delete_message = AsyncMock(return_value={"success": True})

    # 1. Test send_message
    await hass.services.async_call(
        DOMAIN,
        "send_message",
        {"target": -100123, "message": "Test service message"},
        blocking=True,
    )
    coordinator.api.async_telegram_send_message.assert_called_once()

    # 2. Test send_photo
    await hass.services.async_call(
        DOMAIN,
        "send_photo",
        {"target": -100123, "file": "http://example.com/pic.jpg", "caption": "Nice photo"},
        blocking=True,
    )
    coordinator.api.async_telegram_send_photo.assert_called_once()

    # 3. Test send_poll
    await hass.services.async_call(
        DOMAIN,
        "send_poll",
        {"target": -100123, "question": "Where to eat?", "options": ["Pizza", "Burger"], "category": "meal"},
        blocking=True,
    )
    coordinator.api.async_telegram_send_poll.assert_called_once()

    # 4. Test delete_message with bot parameter
    await hass.services.async_call(
        DOMAIN,
        "delete_message",
        {"target": -100123, "message_id": 999, "bot": "BotBeta"},
        blocking=True,
    )
    coordinator.api.async_telegram_delete_message.assert_called_once_with(
        chat_id=-100123, message_id=999, bot_id="BotBeta"
    )
