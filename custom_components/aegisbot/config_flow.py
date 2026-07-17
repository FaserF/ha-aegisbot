"""Config flow for AegisBot integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.service_info.hassio import HassioServiceInfo

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

    def __init__(self) -> None:
        """Initialize the flow."""
        self._addon_slug: str | None = None
        self._url: str | None = None

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

    async def async_step_hassio(
        self, discovery_info: HassioServiceInfo
    ) -> ConfigFlowResult:
        """Handle supervisor discovery."""
        slug = getattr(discovery_info, "slug", None)
        if not slug:
            return self.async_abort(reason="not_supported")

        matched_slug = None
        for supported in ["aegisbot", "aegisbot-edge"]:
            if slug == supported or slug.endswith(f"_{supported}"):
                matched_slug = slug
                break

        if not matched_slug:
            return self.async_abort(reason="not_supported")

        self._addon_slug = matched_slug
        host = matched_slug.replace("_", "-")
        self._url = f"http://{host}:8077"

        await self.async_set_unique_id(f"{matched_slug}_8077")
        self._abort_if_unique_id_configured()

        return await self.async_step_hassio_confirm()

    async def async_step_hassio_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm hassio discovery."""
        errors: dict[str, str] = {}
        if user_input is not None:
            user_input[CONF_URL] = self._url
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="hassio_confirm",
            data_schema=vol.Schema({vol.Required(CONF_API_KEY): str}),
            errors=errors,
            description_placeholders={"addon": self._addon_slug or ""},
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
