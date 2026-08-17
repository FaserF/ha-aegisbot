"""Constants for the AegisBot integration."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "aegisbot"

CONF_URL = "url"
CONF_API_KEY = "api_key"
CONF_ALLOWED_CHAT_IDS = "allowed_chat_ids"
CONF_WEBHOOK_ID = "webhook_id"
CONF_CHAT_ID = "chat_id"

DEFAULT_UPDATE_INTERVAL = 30

# Events
EVENT_AEGISBOT_COMMAND = "aegisbot_command"
EVENT_AEGISBOT_TEXT = "aegisbot_text"
EVENT_AEGISBOT_CALLBACK = "aegisbot_callback"
EVENT_AEGISBOT_POLL_ANSWER = "aegisbot_poll_answer"
EVENT_AEGISBOT_POLL_UPDATE = "aegisbot_poll_update"
EVENT_AEGISBOT_POLL_RESULT = "aegisbot_poll_result"

