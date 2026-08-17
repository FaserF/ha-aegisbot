"""Tests for the AegisBot notify platform."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.aegisbot.notify import AegisBotNotificationService


@pytest.fixture
def mock_coordinator():
    coord = MagicMock()
    coord.api = MagicMock()
    coord.api.async_telegram_send_message = AsyncMock()
    coord.api.async_telegram_send_photo = AsyncMock()
    coord.api.async_telegram_send_video = AsyncMock()
    coord.api.async_telegram_send_document = AsyncMock()
    coord.api.async_telegram_send_animation = AsyncMock()
    coord.api.async_telegram_send_voice = AsyncMock()
    coord.api.async_telegram_send_location = AsyncMock()
    coord.api.async_telegram_send_poll = AsyncMock()
    return coord


async def test_notify_send_text_message(mock_coordinator):
    service = AegisBotNotificationService(mock_coordinator, default_chat_ids=[-100123])
    await service.async_send_message(
        message="Hello World",
        title="Alert",
        data={"inline_keyboard": [["Btn:cb_data"]]},
    )

    mock_coordinator.api.async_telegram_send_message.assert_called_once_with(
        chat_id=-100123,
        text="<b>Alert</b>\nHello World",
        parse_mode="HTML",
        reply_markup=None,
        inline_keyboard=[["Btn:cb_data"]],
        keyboard=None,
        disable_notification=False,
        reply_to_message_id=None,
        message_thread_id=None,
        bot_id=None,
    )


async def test_notify_send_photo(mock_coordinator):
    service = AegisBotNotificationService(mock_coordinator)
    await service.async_send_message(
        message="Motion detected",
        target=[-100999],
        data={"photo": "http://example.com/door.jpg"},
    )

    mock_coordinator.api.async_telegram_send_photo.assert_called_once_with(
        chat_id=-100999,
        file="http://example.com/door.jpg",
        caption="Motion detected",
        parse_mode="HTML",
        reply_markup=None,
        inline_keyboard=None,
        keyboard=None,
        disable_notification=False,
        reply_to_message_id=None,
        message_thread_id=None,
        bot_id=None,
    )


async def test_notify_send_poll(mock_coordinator):
    service = AegisBotNotificationService(mock_coordinator, default_chat_ids=[-100555])
    await service.async_send_message(
        message="",
        data={
            "poll": {
                "question": "Was gibt es zu essen?",
                "options": ["Pizza", "Pasta", "Salat"],
                "category": "meal",
            }
        },
    )

    mock_coordinator.api.async_telegram_send_poll.assert_called_once_with(
        chat_id=-100555,
        question="Was gibt es zu essen?",
        options=["Pizza", "Pasta", "Salat"],
        is_anonymous=True,
        poll_type="regular",
        allows_multiple_answers=False,
        correct_option_id=None,
        explanation=None,
        category="meal",
        reply_markup=None,
        disable_notification=False,
        reply_to_message_id=None,
        message_thread_id=None,
        bot_id=None,
    )


async def test_notify_send_location(mock_coordinator):
    service = AegisBotNotificationService(mock_coordinator, default_chat_ids=[-100777], default_bot_id=42)
    await service.async_send_message(
        message="",
        data={"latitude": 48.137, "longitude": 11.576},
    )

    mock_coordinator.api.async_telegram_send_location.assert_called_once_with(
        chat_id=-100777,
        latitude=48.137,
        longitude=11.576,
        live_period=None,
        reply_markup=None,
        inline_keyboard=None,
        disable_notification=False,
        reply_to_message_id=None,
        message_thread_id=None,
        bot_id=42,
    )


async def test_notify_send_with_custom_bot(mock_coordinator):
    service = AegisBotNotificationService(mock_coordinator, default_chat_ids=[-100777])
    await service.async_send_message(
        message="Alert from Bot B",
        data={"bot": "SecurityBot"},
    )

    mock_coordinator.api.async_telegram_send_message.assert_called_once_with(
        chat_id=-100777,
        text="Alert from Bot B",
        parse_mode="HTML",
        reply_markup=None,
        inline_keyboard=None,
        keyboard=None,
        disable_notification=False,
        reply_to_message_id=None,
        message_thread_id=None,
        bot_id="SecurityBot",
    )

