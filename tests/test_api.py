"""Tests for AegisBot API client."""

import aiohttp
import pytest
import respx
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.aegisbot.api import (
    AegisBotApiClient,
    AegisBotApiClientAuthenticationError,
    AegisBotApiClientCommunicationError,
)


async def test_api_get_data(hass, respx_mock):
    """Test get_data."""
    respx_mock.get("http://example.com/api/v1/health").respond(
        json={"status": "healthy"}
    )
    api = AegisBotApiClient("http://example.com", "api_key", async_get_clientsession(hass))
    response = await api.async_get_data()
    assert response == {"status": "healthy"}


async def test_api_auth_error(hass, respx_mock):
    """Test auth error."""
    respx_mock.get("http://example.com/api/v1/health").respond(status=401)
    api = AegisBotApiClient("http://example.com", "api_key", async_get_clientsession(hass))
    with pytest.raises(AegisBotApiClientAuthenticationError):
        await api.async_get_data()


async def test_api_comm_error(hass, respx_mock):
    """Test communication error."""
    respx_mock.get("http://example.com/api/v1/health").side_effect = aiohttp.ClientError
    api = AegisBotApiClient("http://example.com", "api_key", async_get_clientsession(hass))
    with pytest.raises(AegisBotApiClientCommunicationError):
        await api.async_get_data()


async def test_api_get_stats(hass, respx_mock):
    """Test get_stats."""
    respx_mock.get("http://example.com/api/v1/stats").respond(
        json={"data": {"protected_groups": 10}}
    )
    api = AegisBotApiClient("http://example.com", "api_key", async_get_clientsession(hass))
    response = await api.async_get_stats()
    assert response == {"data": {"protected_groups": 5}}


async def test_api_get_all_locks(hass, respx_mock):
    """Test get_all_locks."""
    respx_mock.get("http://example.com/api/v1/locks/overview").respond(
        json={"data": [{"group_id": 1, "locks": []}]}
    )
    api = AegisBotApiClient("http://example.com", "api_key", async_get_clientsession(hass))
    response = await api.async_get_all_locks()
    assert response == [{"group_id": 1, "locks": []}]
