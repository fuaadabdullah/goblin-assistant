from unittest.mock import AsyncMock, patch

import pytest

from api.routes import oracle_mcp


@pytest.mark.asyncio
async def test_tailnet_ping_reports_missing_runtime(monkeypatch):
    monkeypatch.setattr(oracle_mcp.os.path, "exists", lambda _path: False)

    result = await oracle_mcp._tailnet_ping("http://100.107.126.121:8081")

    assert result["tailnet_peer_reachable"] is False
    assert result["tailnet_ping"] == "tailnet socket unavailable"


@pytest.mark.asyncio
async def test_tailnet_ping_uses_tailscale_socket(monkeypatch):
    monkeypatch.setattr(oracle_mcp.os.path, "exists", lambda _path: True)
    proc = AsyncMock()
    proc.returncode = 0
    proc.communicate = AsyncMock(
        return_value=(b"pong from oracle-node (100.107.126.121) via DERP(iad) in 20ms", None)
    )

    with patch(
        "api.routes.oracle_mcp.asyncio.create_subprocess_exec",
        new=AsyncMock(return_value=proc),
    ) as spawn:
        result = await oracle_mcp._tailnet_ping("http://100.107.126.121:8081")

    assert result["tailnet_peer_reachable"] is True
    assert "pong from oracle-node" in result["tailnet_ping"]
    assert spawn.await_args.args[:3] == (
        "tailscale",
        "--socket=/tmp/tailscaled.sock",
        "ping",
    )
