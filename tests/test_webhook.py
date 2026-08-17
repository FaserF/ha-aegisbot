"""Tests for AegisBot Webhook receiver and HA event firing."""

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.components import webhook
from homeassistant.core import callback
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.aegisbot.const import (
    DOMAIN,
    EVENT_AEGISBOT_CALLBACK,
    EVENT_AEGISBOT_COMMAND,
    EVENT_AEGISBOT_POLL_ANSWER,
    EVENT_AEGISBOT_POLL_RESULT,
)


async def test_webhook_event_dispatch(hass):
    """Test receiving webhook event and firing HA events."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"url": "http://127.0.0.1:8077", "api_key": "test_key"},
        entry_id="test_entry_1",
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.aegisbot.coordinator.AegisBotApiClient.async_get_data",
            return_value={"status": "healthy"},
        ),
        patch(
            "custom_components.aegisbot.coordinator.AegisBotApiClient.async_get_stats",
            return_value={"data": {}},
        ),
        patch(
            "custom_components.aegisbot.coordinator.AegisBotApiClient.async_get_all_locks",
            return_value=[],
        ),
        patch(
            "custom_components.aegisbot.coordinator.AegisBotApiClient.async_get_group_health",
            return_value=[],
        ),
        patch(
            "custom_components.aegisbot.coordinator.AegisBotApiClient.async_get_security_intel",
            return_value={},
        ),
        patch(
            "custom_components.aegisbot.coordinator.AegisBotApiClient.async_register_ha_webhook",
            return_value={"success": True},
        ),
        patch(
            "custom_components.aegisbot.coordinator.AegisBotApiClient.async_telegram_get_allowed_chats",
            return_value=[],
        ),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    # Track fired events
    events_command = []
    events_callback = []
    events_poll = []
    events_poll_result = []

    @callback
    def on_cmd(event):
        events_command.append(event.data)

    @callback
    def on_cb(event):
        events_callback.append(event.data)

    @callback
    def on_poll_ans(event):
        events_poll.append(event.data)

    @callback
    def on_poll_res(event):
        events_poll_result.append(event.data)

    hass.bus.async_listen(EVENT_AEGISBOT_COMMAND, on_cmd)
    hass.bus.async_listen(EVENT_AEGISBOT_CALLBACK, on_cb)
    hass.bus.async_listen(EVENT_AEGISBOT_POLL_ANSWER, on_poll_ans)
    hass.bus.async_listen(EVENT_AEGISBOT_POLL_RESULT, on_poll_res)

    webhook_id = f"{DOMAIN}_{entry.entry_id}"

    # 1. Fire command via webhook handler
    mock_request = MagicMock()
    mock_request.method = "POST"
    mock_request.json = AsyncMock(
        return_value={
            "event_type": EVENT_AEGISBOT_COMMAND,
            "event_data": {
                "command": "/meeting",
                "args": ["tomorrow"],
                "chat_id": -100123,
            },
        }
    )
    resp = await webhook.async_handle_webhook(hass, webhook_id, mock_request)
    assert resp.status == 200
    assert len(events_command) == 1
    assert events_command[0]["command"] == "/meeting"

    # 2. Fire callback via webhook handler
    mock_request_cb = MagicMock()
    mock_request_cb.method = "POST"
    mock_request_cb.json = AsyncMock(
        return_value={
            "event_type": EVENT_AEGISBOT_CALLBACK,
            "event_data": {"id": "cb_99", "data": "turn_on_light", "chat_id": -100123},
        }
    )
    resp_cb = await webhook.async_handle_webhook(hass, webhook_id, mock_request_cb)
    assert resp_cb.status == 200
    assert len(events_callback) == 1
    assert events_callback[0]["data"] == "turn_on_light"

    # 3. Fire smart poll answer & result
    mock_request_poll = MagicMock()
    mock_request_poll.method = "POST"
    mock_request_poll.json = AsyncMock(
        return_value={
            "event_type": EVENT_AEGISBOT_POLL_ANSWER,
            "event_data": {"poll_id": "p1", "option_ids": [0], "user_id": 42},
        }
    )
    await webhook.async_handle_webhook(hass, webhook_id, mock_request_poll)
    assert len(events_poll) == 1
    assert events_poll[0]["user_id"] == 42
