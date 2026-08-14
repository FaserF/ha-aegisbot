"""Config flow for AegisBot integration."""

from __future__ import annotations

import asyncio
import os
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_URL
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

try:
    from homeassistant.helpers.service_info.hassio import HassioServiceInfo
except ImportError:
    from homeassistant.components.hassio import (  # type: ignore[no-redef,assignment,attr-defined]
        HassioServiceInfo,
    )

try:
    from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
except ImportError:
    try:
        from homeassistant.components.zeroconf import (  # type: ignore[no-redef,assignment,attr-defined]
            ZeroconfServiceInfo,
        )
    except (ImportError, ModuleNotFoundError):
        from unittest.mock import MagicMock

        ZeroconfServiceInfo = MagicMock()  # type: ignore[misc,assignment]

try:
    from homeassistant.helpers import selector
except ImportError:
    from unittest.mock import MagicMock

    selector = MagicMock()  # type: ignore[assignment]

from .api import (
    AegisBotApiClient,
    AegisBotApiClientAuthenticationError,
    AegisBotApiClientCommunicationError,
    AegisBotApiClientError,
)
from .const import CONF_API_KEY, DOMAIN, LOGGER

DEFAULT_PORT = 8077
ADDON_STABLE_SLUG = "edfe50eb_aegisbot"
ADDON_EDGE_SLUG = "edfe50eb_aegisbot_edge"
ADDON_NAME = "AegisBot"

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
        self.discovery_info: dict[str, Any] = {}
        self._addon_slug: str | None = None
        self._url: str | None = None

    async def _async_get_addon_manager(self, slug: str) -> Any:
        """Return the addon manager."""
        try:
            from homeassistant.components.hassio import (
                AddonManager,  # type: ignore[attr-defined]
            )

            return AddonManager(self.hass, LOGGER, slug, ADDON_NAME)
        except (ImportError, AttributeError):
            return None

    async def _async_prefill_addon_info(self, slug: str) -> None:
        """Pre-fill addon info from Supervisor."""
        addon_manager = await self._async_get_addon_manager(slug)
        try:
            if addon_manager is None:
                return
            addon_info = await addon_manager.async_get_addon_info()
            host = slug.replace("_", "-")
            port = DEFAULT_PORT

            if addon_info.network:
                for internal, external in addon_info.network.items():
                    if internal.startswith(f"{DEFAULT_PORT}/"):
                        port = external
                        break

            self.discovery_info[CONF_URL] = f"http://{host}:{port}"
            self._url = self.discovery_info[CONF_URL]
            self._addon_slug = slug

            # Check if token exists in /data/.api_token
            self._try_read_local_token()

            LOGGER.debug("Pre-filled AegisBot addon info: %s", self.discovery_info)
        except Exception as e:  # noqa: BLE001
            LOGGER.warning("Could not pre-fill addon info: %s", e)

    def _try_read_local_token(self) -> None:
        """Attempt to read API token from persistent storage file."""
        if not self.discovery_info.get(CONF_API_KEY):
            try:
                data_dir = "/data" if os.name != "nt" else os.path.abspath("data")
                token_file = os.path.join(data_dir, ".api_token")
                if os.path.exists(token_file):
                    with open(token_file, encoding="utf-8") as f:
                        tok = f.read().strip()
                        if tok:
                            self.discovery_info[CONF_API_KEY] = tok
            except Exception:  # noqa: BLE001
                pass

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        is_hassio_env = "hassio" in getattr(self.hass.config, "components", set())

        if (
            user_input is None
            and is_hassio_env
            and not self.context.get("hassio_checked")
            and not self.discovery_info.get(CONF_URL)
        ):
            self.context["hassio_checked"] = True  # type: ignore[typeddict-unknown-key]
            return await self.async_step_hassio()

        errors: dict[str, str] = {}

        suggested_url = (
            self.discovery_info.get(CONF_URL) or f"http://localhost:{DEFAULT_PORT}"
        )

        if user_input is None and not self.discovery_info.get(CONF_URL):
            candidates = [
                "localhost",
                "edfe50eb-aegisbot",
                "edfe50eb-aegisbot-edge",
                "local-aegisbot",
                "aegisbot",
            ]
            for candidate in candidates:
                try:
                    _, writer = await asyncio.wait_for(
                        asyncio.open_connection(candidate, DEFAULT_PORT),
                        timeout=0.3,
                    )
                    writer.close()
                    await writer.wait_closed()
                    suggested_url = f"http://{candidate}:{DEFAULT_PORT}"
                    break
                except Exception:
                    continue

        self._try_read_local_token()

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

        prefilled_key = self.discovery_info.get(CONF_API_KEY, "")

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_URL,
                        default=user_input.get(CONF_URL)
                        if user_input
                        else suggested_url,
                    ): str,
                    vol.Required(
                        CONF_API_KEY,
                        default=user_input.get(CONF_API_KEY)
                        if user_input
                        else prefilled_key,
                    ): str,
                }
            ),
            errors=errors,
        )

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Handle zeroconf discovery."""
        host = discovery_info.host
        port = discovery_info.port
        properties = discovery_info.properties

        def decode_property(key: str) -> str | None:
            value = properties.get(key)
            if isinstance(value, bytes):
                return value.decode("utf-8")
            return str(value) if value is not None else None

        system_id = decode_property("system_id")
        api_key = decode_property("api_key")

        suggested_url = f"http://{host}:{port}"
        self.discovery_info[CONF_URL] = suggested_url
        self.discovery_info["system_id"] = system_id
        if api_key:
            self.discovery_info[CONF_API_KEY] = api_key

        unique_id = system_id or f"{host}:{port}"
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured(updates={CONF_URL: suggested_url})

        self.context.update(
            {
                "title_placeholders": {"url": suggested_url},
                "hassio_checked": True,
            }  # type: ignore[typeddict-item]
        )

        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm discovery."""
        url = self.discovery_info.get(CONF_URL, "")
        self._try_read_local_token()
        api_key = self.discovery_info.get(CONF_API_KEY, "")

        if user_input is not None:
            final_api_key = user_input.get(CONF_API_KEY) or api_key
            return await self.async_step_user(
                {
                    CONF_URL: url,
                    CONF_API_KEY: final_api_key,
                }
            )

        if api_key:
            # Token is known: simple 1-click confirmation dialog
            return self.async_show_form(
                step_id="discovery_confirm",
                description_placeholders={"url": url},
            )

        # Token is unknown: show input field for API Key
        return self.async_show_form(
            step_id="discovery_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY, default=""): str,
                }
            ),
            description_placeholders={"url": url},
        )


    async def async_step_hassio(
        self, discovery_info: HassioServiceInfo | None = None
    ) -> ConfigFlowResult:
        """Handle supervisor discovery or addon check."""
        if discovery_info is not None:
            slug = getattr(discovery_info, "slug", None)
            if slug:
                for supported in [
                    "aegisbot",
                    "aegisbot-edge",
                    ADDON_STABLE_SLUG,
                    ADDON_EDGE_SLUG,
                ]:
                    if slug == supported or slug.endswith(f"_{supported}"):
                        await self._async_prefill_addon_info(slug)
                        return await self.async_step_user()

        try:
            from homeassistant.components.hassio import (
                AddonState,  # type: ignore[attr-defined]
            )
        except (ImportError, AttributeError):
            return await self.async_step_user()

        for slug in [ADDON_STABLE_SLUG, ADDON_EDGE_SLUG, "local_aegisbot", "aegisbot"]:
            addon_manager = await self._async_get_addon_manager(slug)
            if addon_manager is None:
                continue
            try:
                addon_info = await addon_manager.async_get_addon_info()
                if addon_info.state != AddonState.NOT_INSTALLED:
                    await self._async_prefill_addon_info(slug)
                    return await self.async_step_user()
            except Exception:  # noqa: BLE001
                continue

        return await self.async_step_hassio_confirm()

    async def async_step_hassio_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm installation of the official addon."""
        errors: dict[str, str] = {}
        if user_input is not None:
            slug = ADDON_STABLE_SLUG
            addon_manager = await self._async_get_addon_manager(slug)
            try:
                if addon_manager:
                    await addon_manager.async_install_addon()
                    await addon_manager.async_start_addon()
            except Exception as e:  # noqa: BLE001
                LOGGER.error("Failed to install AegisBot addon (%s): %s", slug, e)
                errors["base"] = "addon_install_error"
                return self.async_show_form(
                    step_id="hassio_confirm",
                    errors=errors,
                    description_placeholders={"addon": ADDON_NAME},
                )
            await self._async_prefill_addon_info(slug)
            return await self.async_step_user()

        return self.async_show_form(
            step_id="hassio_confirm",
            data_schema=vol.Schema({}),
            description_placeholders={"addon": ADDON_NAME},
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OptionsFlow:
        """Create the options flow."""
        return AegisBotOptionsFlowHandler(config_entry)


class AegisBotOptionsFlowHandler(OptionsFlow):
    """Handle options for AegisBot."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "scan_interval",
                        default=self.config_entry.options.get("scan_interval", 30),
                    ): vol.All(vol.Coerce(int), vol.Range(min=5, max=300)),
                }
            ),
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
