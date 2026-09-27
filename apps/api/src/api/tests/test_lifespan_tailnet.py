import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from api import lifespan as lifespan_module


@pytest.mark.asyncio
async def test_tailnet_proxy_is_noop_without_auth_key(monkeypatch):
    monkeypatch.delenv("TAILSCALE_AUTHKEY", raising=False)
    lifespan_module._tailscaled_process = None

    with patch(
        "api.lifespan.asyncio.create_subprocess_exec",
        new_callable=AsyncMock,
    ) as spawn:
        await lifespan_module._ensure_tailnet_proxy()

    spawn.assert_not_awaited()


@pytest.mark.asyncio
async def test_tailnet_proxy_reuses_existing_socket(monkeypatch):
    monkeypatch.setenv("TAILSCALE_AUTHKEY", "test-auth-key")
    monkeypatch.setattr(lifespan_module.os.path, "exists", lambda _path: True)
    lifespan_module._tailscaled_process = None

    with patch(
        "api.lifespan.asyncio.create_subprocess_exec",
        new_callable=AsyncMock,
    ) as spawn:
        await lifespan_module._ensure_tailnet_proxy()

    spawn.assert_not_awaited()


@pytest.mark.asyncio
async def test_tailnet_proxy_starts_userspace_daemon_and_authenticates(monkeypatch):
    monkeypatch.setenv("TAILSCALE_AUTHKEY", "test-auth-key")
    monkeypatch.setenv("TAILSCALE_HOSTNAME", "test-render")
    monkeypatch.setattr(lifespan_module.os.path, "exists", lambda _path: False)
    monkeypatch.setattr(lifespan_module.asyncio, "sleep", AsyncMock())

    daemon = AsyncMock()
    daemon.terminate = lambda: None
    daemon.wait = AsyncMock(return_value=0)

    login = AsyncMock()
    login.returncode = 0
    login.communicate = AsyncMock(return_value=(b"", b""))

    lifespan_module._tailscaled_process = None
    with patch(
        "api.lifespan.asyncio.create_subprocess_exec",
        new=AsyncMock(side_effect=[daemon, login]),
    ) as spawn:
        await lifespan_module._ensure_tailnet_proxy()

    assert spawn.await_count == 2
    daemon_args = spawn.await_args_list[0].args
    login_args = spawn.await_args_list[1].args
    assert daemon_args[:2] == ("tailscaled", "--tun=userspace-networking")
    assert "--socks5-server=localhost:1055" in daemon_args
    assert "--outbound-http-proxy-listen=localhost:1055" in daemon_args
    assert login_args[:3] == (
        "tailscale",
        f"--socket={lifespan_module._TAILSCALE_SOCKET}",
        "up",
    )
    assert "--auth-key=test-auth-key" in login_args
    assert "--hostname=test-render" in login_args

    await lifespan_module._stop_tailnet_proxy()
    assert lifespan_module._tailscaled_process is None
