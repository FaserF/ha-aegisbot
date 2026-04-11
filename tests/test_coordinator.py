from unittest.mock import patch

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.aegisbot.api import AegisBotApiClientError
from custom_components.aegisbot.const import CONF_API_KEY, CONF_URL, DOMAIN
from custom_components.aegisbot.coordinator import AegisBotDataCoordinator


@pytest.fixture
def mock_config_entry():
    """Mock a config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={CONF_URL: "http://example.com", CONF_API_KEY: "api_key"},
        entry_id="test_entry",
    )


async def test_coordinator_update_data(hass, mock_api, mock_config_entry):
    """Test coordinator update data."""
    with patch(
        "custom_components.aegisbot.coordinator.AegisBotApiClient",
        return_value=mock_api,
    ):
        coordinator = AegisBotDataCoordinator(hass, mock_config_entry)

        mock_api.async_get_data.return_value = {"status": "healthy"}
        mock_api.async_get_stats.return_value = {"data": {"protected_groups": 5}}
        mock_api.async_get_group_health.return_value = [
            {"group_id": 1, "title": "Test Group"}
        ]
        mock_api.async_get_all_locks.return_value = [
            {"group_id": 1, "locks": ["lock1"]}
        ]
        mock_api.async_get_security_intel.return_value = {"data": {"total_alerts": 10}}

        data = await coordinator._async_update_data()

        assert data["health"] == {"status": "healthy"}
        assert data["stats"] == {"protected_groups": 5}
        assert data["groups"][1]["title"] == "Test Group"
        assert data["locks"][1] == ["lock1"]
        assert data["intel"] == {"total_alerts": 10}


async def test_coordinator_update_failed(hass, mock_api, mock_config_entry):
    """Test coordinator update failed."""
    with patch(
        "custom_components.aegisbot.coordinator.AegisBotApiClient",
        return_value=mock_api,
    ):
        coordinator = AegisBotDataCoordinator(hass, mock_config_entry)
        mock_api.async_get_data.side_effect = AegisBotApiClientError("Error")

        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
