"""Fixtures for AegisBot tests."""
import os
import sys
from unittest.mock import patch

import pytest

# Ensure the project root is in the path so that custom_components can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


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
