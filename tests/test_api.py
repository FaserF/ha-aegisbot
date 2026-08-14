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


async def test_api_broadcast(hass, aioclient_mock):
    """Test broadcast."""
    aioclient_mock.post(
        "http://example.com/api/v1/broadcast",
        json={"success": True},
    )
    api = AegisBotApiClient(
        "http://example.com", "api_key", async_get_clientsession(hass)
    )
    res = await api.async_broadcast("Hello", [123], "telegram")
    assert res == {"success": True}


async def test_api_reputation(hass, aioclient_mock):
    """Test reputation methods."""
    aioclient_mock.get(
        "http://example.com/api/v1/reputation/12345?group_id=-100",
        json={"score": 80},
    )
    aioclient_mock.post(
        "http://example.com/api/v1/reputation/12345/adjust",
        json={"success": True, "score": 90},
    )
    api = AegisBotApiClient(
        "http://example.com", "api_key", async_get_clientsession(hass)
    )
    rep = await api.async_get_reputation(12345, group_id=-100)
    assert rep == {"score": 80}

    adj = await api.async_adjust_reputation(
        12345, delta=10, reason="test", group_id=-100
    )
    assert adj == {"success": True, "score": 90}


async def test_api_presets_and_governance(hass, aioclient_mock):
    """Test apply_preset and get_governance_report."""
    aioclient_mock.post(
        "http://example.com/api/v1/groups/-100/presets/strict",
        json={"applied": True},
    )
    aioclient_mock.get(
        "http://example.com/api/v1/governance/report/-100",
        json={"report": "clean"},
    )
    aioclient_mock.get(
        "http://example.com/api/v1/governance/report",
        json={"report": "global"},
    )
    api = AegisBotApiClient(
        "http://example.com", "api_key", async_get_clientsession(hass)
    )
    preset_res = await api.async_apply_preset(-100, "strict")
    assert preset_res == {"applied": True}

    gov_grp = await api.async_get_governance_report(-100)
    assert gov_grp == {"report": "clean"}

    gov_all = await api.async_get_governance_report()
    assert gov_all == {"report": "global"}


async def test_api_maintenance_and_whatsapp(hass, aioclient_mock):
    """Test maintenance and whatsapp methods."""
    aioclient_mock.post(
        "http://example.com/api/v1/maintenance/vacuum", json={"vacuumed": True}
    )
    aioclient_mock.post(
        "http://example.com/api/v1/maintenance/cleanup", json={"cleaned": True}
    )
    aioclient_mock.post(
        "http://example.com/api/v1/maintenance/purge/-100", json={"purged": True}
    )
    aioclient_mock.post(
        "http://example.com/api/v1/maintenance/live-test", json={"passed": True}
    )
    aioclient_mock.get(
        "http://example.com/api/v1/maintenance/status", json={"db_size_mb": 15}
    )
    aioclient_mock.get(
        "http://example.com/api/v1/whatsapp/status", json={"status": "connected"}
    )
    aioclient_mock.post(
        "http://example.com/api/v1/whatsapp/action", json={"result": "ok"}
    )
    aioclient_mock.post(
        "http://example.com/api/v1/notifications/mark-read", json={"marked": True}
    )

    api = AegisBotApiClient(
        "http://example.com", "api_key", async_get_clientsession(hass)
    )
    assert await api.async_maintenance_vacuum() == {"vacuumed": True}
    assert await api.async_maintenance_cleanup(30) == {"cleaned": True}
    assert await api.async_maintenance_purge(-100) == {"purged": True}
    assert await api.async_maintenance_live_test() == {"passed": True}
    assert await api.async_get_maintenance_status() == {"db_size_mb": 15}
    assert await api.async_get_whatsapp_status() == {"status": "connected"}
    assert await api.async_whatsapp_action("reconnect", {"force": True}) == {
        "result": "ok"
    }
    assert await api.async_mark_notifications_read(["1"]) == {"marked": True}
