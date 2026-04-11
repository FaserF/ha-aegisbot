"""Fixtures for AegisBot tests."""

from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(hass):
    """Enable custom integrations in Home Assistant."""
    hass.data.pop("custom_components", None)
    yield


@pytest.fixture
def mock_api():
    """Mock the AegisBot API client."""
    with patch("custom_components.aegisbot.api.AegisBotApiClient") as mock:
        yield mock
