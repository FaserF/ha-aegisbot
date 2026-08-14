import asyncio
import os
import sys
import types
from typing import Any
from unittest.mock import AsyncMock, patch

if sys.platform == "win32" and "fcntl" not in sys.modules:
    sys.modules["fcntl"] = types.ModuleType("fcntl")

import pytest

# Ensure the project root is in the path so that custom_components can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def pytest_sessionstart(session: Any) -> None:  # noqa: ARG001
    """Called after Session creation."""
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        import pytest_socket

        pytest_socket.enable_sockets()
    except Exception:
        pass


def _ensure_sockets() -> None:
    import socket

    try:
        import pytest_socket

        if hasattr(pytest_socket, "enable_socket"):
            pytest_socket.enable_socket()
        elif hasattr(pytest_socket, "enable_sockets"):
            pytest_socket.enable_sockets()
        if hasattr(pytest_socket, "_true_socket"):
            socket.socket = pytest_socket._true_socket

        orig_socketpair = getattr(socket, "socketpair", None)
        if orig_socketpair and hasattr(pytest_socket, "_true_socket"):

            def _safe_socketpair(*args: Any, **kwargs: Any) -> Any:
                old_sock = socket.socket
                socket.socket = pytest_socket._true_socket
                try:
                    return orig_socketpair(*args, **kwargs)
                finally:
                    socket.socket = old_sock

            socket.socketpair = _safe_socketpair
    except Exception:
        pass


def pytest_runtest_setup(item: Any) -> None:  # noqa: ARG001
    """Hook running before each test item setup."""
    _ensure_sockets()


def pytest_runtest_teardown(item: Any) -> None:  # noqa: ARG001
    """Hook running after each test item execution."""
    _ensure_sockets()


@pytest.fixture(autouse=True)
def enable_socket() -> Any:
    """Enable socket access during testing."""
    _ensure_sockets()
    yield
    _ensure_sockets()


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(request):
    """Enable custom integrations in Home Assistant if hass fixture is present."""
    _ensure_sockets()
    if "hass" in request.fixturenames:
        hass = request.getfixturevalue("hass")
        hass.data.pop("custom_components", None)
        hass.config.components.add("hassio")
    yield
    _ensure_sockets()


@pytest.fixture
def mock_api():
    """Mock the AegisBot API client."""
    with patch(
        "custom_components.aegisbot.api.AegisBotApiClient", autospec=True
    ) as mock:
        client = mock.return_value
        client.async_get_data = AsyncMock()
        client.async_get_all_locks = AsyncMock()
        client.async_get_security_intel = AsyncMock()
        client.async_get_group_health = AsyncMock()
        client.async_get_stats = AsyncMock()
        client.async_get_locks = AsyncMock()
        client.async_toggle_lock = AsyncMock()
        client.async_sync_filters = AsyncMock()
        client.async_send_message = AsyncMock()
        client.async_ban_user = AsyncMock()
        client.async_unban_user = AsyncMock()
        client.async_mute_user = AsyncMock()
        client.async_warn_user = AsyncMock()
        client.async_broadcast = AsyncMock()
        client.async_get_reputation = AsyncMock()
        client.async_adjust_reputation = AsyncMock()
        client.async_apply_preset = AsyncMock()
        client.async_get_governance_report = AsyncMock()
        client.async_mark_notifications_read = AsyncMock()
        client.async_maintenance_vacuum = AsyncMock()
        client.async_maintenance_cleanup = AsyncMock()
        client.async_maintenance_purge = AsyncMock()
        client.async_maintenance_live_test = AsyncMock()
        client.async_get_maintenance_status = AsyncMock()
        client.async_get_whatsapp_status = AsyncMock()
        client.async_whatsapp_action = AsyncMock()
        yield client
