"""Tests for AegisBot config flow."""

from unittest.mock import patch

from homeassistant import data_entry_flow
from homeassistant.const import CONF_URL
from pytest_homeassistant_custom_component.common import MockConfigEntry

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
