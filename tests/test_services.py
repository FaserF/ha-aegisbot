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
            return_value=[-100123],
        ),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    coordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.api.async_telegram_send_message = AsyncMock(
        return_value={"success": True}
    )
    coordinator.api.async_telegram_send_photo = AsyncMock(
        return_value={"success": True}
    )
    coordinator.api.async_telegram_send_poll = AsyncMock(return_value={"success": True})
    coordinator.api.async_telegram_stop_poll = AsyncMock(return_value={"success": True})
    coordinator.api.async_telegram_delete_message = AsyncMock(
        return_value={"success": True}
    )

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
        {
            "target": -100123,
            "file": "http://example.com/pic.jpg",
            "caption": "Nice photo",
        },
        blocking=True,
    )
    coordinator.api.async_telegram_send_photo.assert_called_once()

    # 3. Test send_poll
    await hass.services.async_call(
        DOMAIN,
        "send_poll",
        {
            "target": -100123,
            "question": "Where to eat?",
            "options": ["Pizza", "Burger"],
            "category": "meal",
        },
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

    # 5. Test modern services (Audio, Dice, Venue, Contact, Reaction, Pin, Forum Topic)
    coordinator.api.async_telegram_send_audio = AsyncMock(
        return_value={"success": True}
    )
    coordinator.api.async_telegram_send_dice = AsyncMock(return_value={"success": True})
    coordinator.api.async_telegram_send_venue = AsyncMock(
        return_value={"success": True}
    )
    coordinator.api.async_telegram_send_contact = AsyncMock(
        return_value={"success": True}
    )
    coordinator.api.async_telegram_edit_message_media = AsyncMock(
        return_value={"success": True}
    )
    coordinator.api.async_telegram_set_message_reaction = AsyncMock(
        return_value={"success": True}
    )
    coordinator.api.async_telegram_pin_message = AsyncMock(
        return_value={"success": True}
    )
    coordinator.api.async_telegram_create_forum_topic = AsyncMock(
        return_value={"success": True}
    )

    await hass.services.async_call(
        DOMAIN,
        "send_audio",
        {
            "target": -100123,
            "file": "/music/tune.mp3",
            "title": "Theme",
            "performer": "Artist",
        },
        blocking=True,
    )
    coordinator.api.async_telegram_send_audio.assert_called_once()

    await hass.services.async_call(
        DOMAIN,
        "send_dice",
        {"target": -100123, "emoji": "🎯"},
        blocking=True,
    )
    coordinator.api.async_telegram_send_dice.assert_called_once()

    await hass.services.async_call(
        DOMAIN,
        "send_venue",
        {
            "target": -100123,
            "latitude": 52.52,
            "longitude": 13.405,
            "title": "Berlin Center",
            "address": "Berlin, Germany",
        },
        blocking=True,
    )
    coordinator.api.async_telegram_send_venue.assert_called_once()

    await hass.services.async_call(
        DOMAIN,
        "send_contact",
        {
            "target": -100123,
            "phone_number": "+4912345",
            "first_name": "Max",
            "last_name": "Mustermann",
        },
        blocking=True,
    )
    coordinator.api.async_telegram_send_contact.assert_called_once()

    await hass.services.async_call(
        DOMAIN,
        "edit_message_media",
        {
            "target": -100123,
            "message_id": 555,
            "file": "http://example.com/cam.jpg",
            "media_type": "photo",
        },
        blocking=True,
    )
    coordinator.api.async_telegram_edit_message_media.assert_called_once()

    await hass.services.async_call(
        DOMAIN,
        "set_message_reaction",
        {"target": -100123, "message_id": 777, "reaction": "🔥"},
        blocking=True,
    )
    coordinator.api.async_telegram_set_message_reaction.assert_called_once()

    await hass.services.async_call(
        DOMAIN,
        "pin_message",
        {"target": -100123, "message_id": 888, "disable_notification": True},
        blocking=True,
    )
    coordinator.api.async_telegram_pin_message.assert_called_once()

    await hass.services.async_call(
        DOMAIN,
        "create_forum_topic",
        {"target": -100123, "name": "Security Incidents"},
        blocking=True,
    )
    coordinator.api.async_telegram_create_forum_topic.assert_called_once()

    # 6. Test remaining media & telegram operations
    coordinator.api.async_telegram_send_video = AsyncMock(
        return_value={"success": True}
    )
    coordinator.api.async_telegram_send_document = AsyncMock(
        return_value={"success": True}
    )
    coordinator.api.async_telegram_send_animation = AsyncMock(
        return_value={"success": True}
    )
    coordinator.api.async_telegram_send_voice = AsyncMock(
        return_value={"success": True}
    )
    coordinator.api.async_telegram_send_location = AsyncMock(
        return_value={"success": True}
    )
    coordinator.api.async_telegram_send_sticker = AsyncMock(
        return_value={"success": True}
    )
    coordinator.api.async_telegram_send_chat_action = AsyncMock(
        return_value={"success": True}
    )
    coordinator.api.async_telegram_send_video_note = AsyncMock(
        return_value={"success": True}
    )
    coordinator.api.async_telegram_edit_message_text = AsyncMock(
        return_value={"success": True}
    )
    coordinator.api.async_telegram_edit_message_caption = AsyncMock(
        return_value={"success": True}
    )
    coordinator.api.async_telegram_edit_message_reply_markup = AsyncMock(
        return_value={"success": True}
    )
    coordinator.api.async_telegram_edit_live_location = AsyncMock(
        return_value={"success": True}
    )
    coordinator.api.async_telegram_stop_live_location = AsyncMock(
        return_value={"success": True}
    )
    coordinator.api.async_telegram_forward_message = AsyncMock(
        return_value={"success": True}
    )
    coordinator.api.async_telegram_copy_message = AsyncMock(
        return_value={"success": True}
    )
    coordinator.api.async_telegram_unpin_message = AsyncMock(
        return_value={"success": True}
    )
    coordinator.api.async_telegram_unpin_all_messages = AsyncMock(
        return_value={"success": True}
    )
    coordinator.api.async_telegram_edit_forum_topic = AsyncMock(
        return_value={"success": True}
    )
    coordinator.api.async_telegram_close_forum_topic = AsyncMock(
        return_value={"success": True}
    )
    coordinator.api.async_telegram_reopen_forum_topic = AsyncMock(
        return_value={"success": True}
    )
    coordinator.api.async_telegram_delete_forum_topic = AsyncMock(
        return_value={"success": True}
    )
    coordinator.api.async_telegram_set_chat_title = AsyncMock(
        return_value={"success": True}
    )
    coordinator.api.async_telegram_set_chat_description = AsyncMock(
        return_value={"success": True}
    )
    coordinator.api.async_telegram_leave_chat = AsyncMock(
        return_value={"success": True}
    )
    coordinator.api.async_telegram_answer_callback_query = AsyncMock(
        return_value={"success": True}
    )

    await hass.services.async_call(
        DOMAIN, "send_video", {"target": -100123, "file": "/tmp/v.mp4"}, blocking=True
    )
    coordinator.api.async_telegram_send_video.assert_called_once()

    await hass.services.async_call(
        DOMAIN,
        "send_document",
        {"target": -100123, "file": "/tmp/doc.pdf"},
        blocking=True,
    )
    coordinator.api.async_telegram_send_document.assert_called_once()

    await hass.services.async_call(
        DOMAIN,
        "send_animation",
        {"target": -100123, "file": "/tmp/anim.gif"},
        blocking=True,
    )
    coordinator.api.async_telegram_send_animation.assert_called_once()

    await hass.services.async_call(
        DOMAIN, "send_voice", {"target": -100123, "file": "/tmp/v.ogg"}, blocking=True
    )
    coordinator.api.async_telegram_send_voice.assert_called_once()

    await hass.services.async_call(
        DOMAIN,
        "send_location",
        {"target": -100123, "latitude": 48.0, "longitude": 11.0},
        blocking=True,
    )
    coordinator.api.async_telegram_send_location.assert_called_once()

    await hass.services.async_call(
        DOMAIN,
        "send_sticker",
        {"target": -100123, "file": "sticker_id_123"},
        blocking=True,
    )
    coordinator.api.async_telegram_send_sticker.assert_called_once()

    await hass.services.async_call(
        DOMAIN,
        "send_chat_action",
        {"target": -100123, "action": "typing"},
        blocking=True,
    )
    coordinator.api.async_telegram_send_chat_action.assert_called_once()

    await hass.services.async_call(
        DOMAIN,
        "send_video_note",
        {"target": -100123, "file": "/tmp/note.mp4"},
        blocking=True,
    )
    coordinator.api.async_telegram_send_video_note.assert_called_once()

    await hass.services.async_call(
        DOMAIN, "stop_poll", {"target": -100123, "message_id": 333}, blocking=True
    )
    coordinator.api.async_telegram_stop_poll.assert_called_once()

    await hass.services.async_call(
        DOMAIN,
        "edit_message",
        {"target": -100123, "message_id": 444, "message": "Updated"},
        blocking=True,
    )
    coordinator.api.async_telegram_edit_message_text.assert_called_once()

    await hass.services.async_call(
        DOMAIN,
        "edit_caption",
        {"target": -100123, "message_id": 444, "caption": "New caption"},
        blocking=True,
    )
    coordinator.api.async_telegram_edit_message_caption.assert_called_once()

    await hass.services.async_call(
        DOMAIN,
        "edit_replymarkup",
        {"target": -100123, "message_id": 444, "inline_keyboard": [["OK:ok"]]},
        blocking=True,
    )
    coordinator.api.async_telegram_edit_message_reply_markup.assert_called_once()

    await hass.services.async_call(
        DOMAIN,
        "edit_live_location",
        {"target": -100123, "message_id": 444, "latitude": 48.1, "longitude": 11.1},
        blocking=True,
    )
    coordinator.api.async_telegram_edit_live_location.assert_called_once()

    await hass.services.async_call(
        DOMAIN,
        "stop_live_location",
        {"target": -100123, "message_id": 444},
        blocking=True,
    )
    coordinator.api.async_telegram_stop_live_location.assert_called_once()

    await hass.services.async_call(
        DOMAIN,
        "forward_message",
        {"target": -100123, "from_chat_id": -100999, "message_id": 111},
        blocking=True,
    )
    coordinator.api.async_telegram_forward_message.assert_called_once()

    await hass.services.async_call(
        DOMAIN,
        "copy_message",
        {"target": -100123, "from_chat_id": -100999, "message_id": 111},
        blocking=True,
    )
    coordinator.api.async_telegram_copy_message.assert_called_once()

    await hass.services.async_call(
        DOMAIN, "unpin_message", {"target": -100123, "message_id": 888}, blocking=True
    )
    coordinator.api.async_telegram_unpin_message.assert_called_once()

    await hass.services.async_call(
        DOMAIN, "unpin_all_messages", {"target": -100123}, blocking=True
    )
    coordinator.api.async_telegram_unpin_all_messages.assert_called_once()

    await hass.services.async_call(
        DOMAIN,
        "edit_forum_topic",
        {"target": -100123, "message_thread_id": 12, "name": "Renamed"},
        blocking=True,
    )
    coordinator.api.async_telegram_edit_forum_topic.assert_called_once()

    await hass.services.async_call(
        DOMAIN,
        "close_forum_topic",
        {"target": -100123, "message_thread_id": 12},
        blocking=True,
    )
    coordinator.api.async_telegram_close_forum_topic.assert_called_once()

    await hass.services.async_call(
        DOMAIN,
        "reopen_forum_topic",
        {"target": -100123, "message_thread_id": 12},
        blocking=True,
    )
    coordinator.api.async_telegram_reopen_forum_topic.assert_called_once()

    await hass.services.async_call(
        DOMAIN,
        "delete_forum_topic",
        {"target": -100123, "message_thread_id": 12},
        blocking=True,
    )
    coordinator.api.async_telegram_delete_forum_topic.assert_called_once()

    await hass.services.async_call(
        DOMAIN,
        "set_chat_title",
        {"target": -100123, "title": "New Title"},
        blocking=True,
    )
    coordinator.api.async_telegram_set_chat_title.assert_called_once()

    await hass.services.async_call(
        DOMAIN,
        "set_chat_description",
        {"target": -100123, "description": "New Desc"},
        blocking=True,
    )
    coordinator.api.async_telegram_set_chat_description.assert_called_once()

    await hass.services.async_call(
        DOMAIN, "leave_chat", {"target": -100123}, blocking=True
    )
    coordinator.api.async_telegram_leave_chat.assert_called_once()

    await hass.services.async_call(
        DOMAIN,
        "answer_callback_query",
        {"callback_query_id": "cb_999", "message": "Done"},
        blocking=True,
    )
    coordinator.api.async_telegram_answer_callback_query.assert_called_once()
