"""Tests for AegisBot API client."""

import aiohttp
import pytest
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.aegisbot.api import (
    AegisBotApiClient,
    AegisBotApiClientAuthenticationError,
    AegisBotApiClientCommunicationError,
)


async def test_api_get_data(hass, aioclient_mock):
    """Test get_data."""
    aioclient_mock.get(
        "http://example.com/api/v1/health",
        json={"status": "healthy"},
    )
    api = AegisBotApiClient(
        "http://example.com", "api_key", async_get_clientsession(hass)
    )
    response = await api.async_get_data()
    assert response == {"status": "healthy"}


async def test_api_auth_error(hass, aioclient_mock):
    """Test auth error."""
    aioclient_mock.get("http://example.com/api/v1/health", status=401)
    api = AegisBotApiClient(
        "http://example.com", "api_key", async_get_clientsession(hass)
    )
    with pytest.raises(AegisBotApiClientAuthenticationError):
        await api.async_get_data()


async def test_api_comm_error(hass, aioclient_mock):
    """Test communication error."""
    # To simulate a communication error with aioclient_mock, we use exc
    aioclient_mock.get("http://example.com/api/v1/health", exc=aiohttp.ClientError)
    api = AegisBotApiClient(
        "http://example.com", "api_key", async_get_clientsession(hass)
    )
    with pytest.raises(AegisBotApiClientCommunicationError):
        await api.async_get_data()


async def test_api_get_stats(hass, aioclient_mock):
    """Test get_stats."""
    aioclient_mock.get(
        "http://example.com/api/v1/stats",
        json={"data": {"protected_groups": 10}},
    )
    api = AegisBotApiClient(
        "http://example.com", "api_key", async_get_clientsession(hass)
    )
    response = await api.async_get_stats()
    assert response == {"data": {"protected_groups": 10}}


async def test_api_get_all_locks(hass, aioclient_mock):
    """Test get_all_locks."""
    aioclient_mock.get(
        "http://example.com/api/v1/locks/overview",
        json={"data": [{"group_id": 1, "locks": []}]},
    )
    api = AegisBotApiClient(
        "http://example.com", "api_key", async_get_clientsession(hass)
    )
    response = await api.async_get_all_locks()
    assert response == [{"group_id": 1, "locks": []}]
