"""Config flow for AegisBot integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    AegisBotApiClient,
    AegisBotApiClientAuthenticationError,
    AegisBotApiClientCommunicationError,
    AegisBotApiClientError,
)
from .const import CONF_API_KEY, DOMAIN, LOGGER

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL): str,
        vol.Required(CONF_API_KEY): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    session = async_get_clientsession(hass)
    client = AegisBotApiClient(
        url=data[CONF_URL],
        api_key=data[CONF_API_KEY],
        session=session,
    )

    try:
        await client.async_get_data()
    except AegisBotApiClientAuthenticationError as exception:
        raise InvalidAuth from exception
    except AegisBotApiClientCommunicationError as exception:
        raise CannotConnect from exception
    except AegisBotApiClientError as exception:
        raise exception

    # Return info that you want to store in the config entry.
    return {"title": data[CONF_URL]}


class AegisBotConfigFlow(ConfigFlow, domain=DOMAIN):  # type: ignore
    """Handle a config flow for AegisBot."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
