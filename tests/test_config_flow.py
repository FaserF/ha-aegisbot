"""Tests for AegisBot config flow."""

from unittest.mock import patch

from homeassistant import data_entry_flow
from homeassistant.const import CONF_URL

from custom_components.aegisbot.config_flow import CannotConnect, InvalidAuth
from custom_components.aegisbot.const import CONF_API_KEY, DOMAIN


async def test_flow_user_init(hass):
    """Test the user step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_flow_user_success(hass, mock_api):
    """Test the user step success."""
    with patch(
        "custom_components.aegisbot.config_flow.AegisBotApiClient",
        return_value=mock_api,
    ):
        mock_api.async_get_data.return_value = {"status": "healthy"}

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
            data={CONF_URL: "http://example.com", CONF_API_KEY: "api_key"},
        )
        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result["title"] == "http://example.com"
        assert result["data"] == {
            CONF_URL: "http://example.com",
            CONF_API_KEY: "api_key",
        }


async def test_flow_user_cannot_connect(hass, mock_api):
    """Test the user step failure (cannot connect)."""
    with patch(
        "custom_components.aegisbot.config_flow.validate_input",
        side_effect=CannotConnect,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
            data={CONF_URL: "http://example.com", CONF_API_KEY: "api_key"},
        )
        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["errors"] == {"base": "cannot_connect"}


async def test_flow_user_invalid_auth(hass, mock_api):
    """Test the user step failure (invalid auth)."""
    with patch(
        "custom_components.aegisbot.config_flow.validate_input",
        side_effect=InvalidAuth,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
            data={CONF_URL: "http://example.com", CONF_API_KEY: "api_key"},
        )
        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["errors"] == {"base": "invalid_auth"}


async def test_flow_zeroconf_discovery(hass, mock_api):
    """Test zeroconf discovery step."""
    from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

    discovery_info = ZeroconfServiceInfo(
        ip_address="192.168.1.100",
        ip_addresses=["192.168.1.100"],
        port=8077,
        hostname="aegisbot.local.",
        type="_ha-aegisbot._tcp.local.",
        name="AegisBot Home Assistant API._ha-aegisbot._tcp.local.",
        properties={
            "system_id": "test_sys_id",
            "api_key": "test_api_key",
            "version": "0.6.1",
        },
    )

    with patch(
        "custom_components.aegisbot.config_flow.validate_input",
        return_value={"title": "http://192.168.1.100:8077"},
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "zeroconf"},
            data=discovery_info,
        )
        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "discovery_confirm"

        # Confirm step
        confirm_result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={},
        )
        assert confirm_result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert confirm_result["title"] == "http://192.168.1.100:8077"


async def test_options_flow(hass):
    """Test options flow for AegisBot."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.aegisbot.const import (
        CONF_ALLOWED_CHAT_IDS,
        CONF_AUTO_SYNC_COMMANDS,
        CONF_DEFAULT_BOT_ID,
        CONF_ENABLE_TELEGRAM_PROXY,
        CONF_IGNORED_COMMANDS,
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_URL: "http://example.com", CONF_API_KEY: "api_key"},
        options={CONF_ALLOWED_CHAT_IDS: "-100123, -100456"},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "scan_interval": 60,
            CONF_ENABLE_TELEGRAM_PROXY: True,
            CONF_AUTO_SYNC_COMMANDS: True,
            CONF_DEFAULT_BOT_ID: "MainBot",
            CONF_IGNORED_COMMANDS: "secret_cmd, admin_only",
            CONF_ALLOWED_CHAT_IDS: "-100789, -100999",
        },
    )
    assert result2["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result2["data"]["scan_interval"] == 60
    assert result2["data"][CONF_ENABLE_TELEGRAM_PROXY] is True
    assert result2["data"][CONF_AUTO_SYNC_COMMANDS] is True
    assert result2["data"][CONF_DEFAULT_BOT_ID] == "MainBot"
    assert result2["data"][CONF_IGNORED_COMMANDS] == "secret_cmd, admin_only"
    assert result2["data"][CONF_ALLOWED_CHAT_IDS] == "-100789, -100999"
