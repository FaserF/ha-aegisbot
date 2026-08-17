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
    service = AegisBotNotificationService(
        mock_coordinator, default_chat_ids=[-100777], default_bot_id=42
    )
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


async def test_notify_send_all_media_variants(mock_coordinator):
    mock_coordinator.api.async_telegram_send_audio = AsyncMock()
    mock_coordinator.api.async_telegram_send_voice = AsyncMock()
    mock_coordinator.api.async_telegram_send_video = AsyncMock()
    mock_coordinator.api.async_telegram_send_document = AsyncMock()
    mock_coordinator.api.async_telegram_send_animation = AsyncMock()
    mock_coordinator.api.async_telegram_send_sticker = AsyncMock()
    mock_coordinator.api.async_telegram_send_video_note = AsyncMock()
    mock_coordinator.api.async_telegram_send_dice = AsyncMock()
    mock_coordinator.api.async_telegram_send_venue = AsyncMock()
    mock_coordinator.api.async_telegram_send_contact = AsyncMock()

    service = AegisBotNotificationService(mock_coordinator, default_chat_ids=[-100123])

    # Audio
    await service.async_send_message(
        message="Soundtrack",
        data={"audio": "/music/song.mp3", "title": "Song", "performer": "Band"},
    )
    mock_coordinator.api.async_telegram_send_audio.assert_called_once()

    # Voice
    await service.async_send_message(message="", data={"voice": "/tmp/voice.ogg"})
    mock_coordinator.api.async_telegram_send_voice.assert_called_once()

    # Video
    await service.async_send_message(message="Clip", data={"video": "/tmp/video.mp4"})
    mock_coordinator.api.async_telegram_send_video.assert_called_once()

    # Document
    await service.async_send_message(
        message="Report", data={"document": "/tmp/report.pdf"}
    )
    mock_coordinator.api.async_telegram_send_document.assert_called_once()

    # Animation
    await service.async_send_message(
        message="Fun", data={"animation": "/tmp/funny.gif"}
    )
    mock_coordinator.api.async_telegram_send_animation.assert_called_once()

    # Sticker
    await service.async_send_message(message="", data={"sticker": "CAACAgIAAxkBAAI..."})
    mock_coordinator.api.async_telegram_send_sticker.assert_called_once()

    # Video note
    await service.async_send_message(message="", data={"video_note": "/tmp/round.mp4"})
    mock_coordinator.api.async_telegram_send_video_note.assert_called_once()

    # Dice
    await service.async_send_message(message="", data={"dice": True, "emoji": "🎲"})
    mock_coordinator.api.async_telegram_send_dice.assert_called_once()

    # Venue
    await service.async_send_message(
        message="",
        data={
            "venue": {
                "latitude": 48.856,
                "longitude": 2.352,
                "title": "Paris",
                "address": "France",
            }
        },
    )
    mock_coordinator.api.async_telegram_send_venue.assert_called_once()

    # Contact
    await service.async_send_message(
        message="", data={"contact": {"phone_number": "+12345", "first_name": "Alice"}}
    )
    mock_coordinator.api.async_telegram_send_contact.assert_called_once()
