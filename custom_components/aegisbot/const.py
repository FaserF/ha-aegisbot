"""Constants for the AegisBot integration."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "aegisbot"

CONF_URL = "url"
CONF_API_KEY = "api_key"

DEFAULT_UPDATE_INTERVAL = 30
