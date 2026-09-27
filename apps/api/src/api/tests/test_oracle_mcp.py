from __future__ import annotations

import json

import pytest

from api.routes import oracle_mcp


@pytest.mark.asyncio
async def test_tailnet_diagnostics_reports_matching_online_peer(monkeypatch):
    status = {
        "Peer": {
            "node-key": {
                "HostName": "goblin-core",
                "TailscaleIPs": ["100.107.126.121"],
                "Online": True,
                "Active": True,
            }
        }
    }
    calls: list[tuple[str, ...]] = []

    async def fake_run(*args: str, timeout: float = 6.0):
        calls.append(args)
        if args[:2] == ("status", "--json"):
            return 0, json.dumps(status), ""
        return 0, "pong from goblin-core (100.107.126.121) via DERP(iad) in 40ms", ""

    monkeypatch.setattr(oracle_mcp, "_run_tailscale", fake_run)

    result = await oracle_mcp._tailnet_diagnostics("http://100.107.126.121:8081")

    assert result["peer_found"] is True
    assert result["peer_online"] is True
    assert result["peer_hostname"] == "goblin-core"
    assert result["ping_ok"] is True
    assert ("ping", "--c=1", "--timeout=5s", "100.107.126.121") in calls


@pytest.mark.asyncio
async def test_tailnet_diagnostics_reports_offline_target(monkeypatch):
    status = {
        "Peer": {
            "node-key": {
                "HostName": "goblin-core",
                "TailscaleIPs": ["100.107.126.121"],
                "Online": False,
                "Active": False,
            }
        }
    }

    async def fake_run(*args: str, timeout: float = 6.0):
        if args[:2] == ("status", "--json"):
            return 0, json.dumps(status), ""
        return 1, "", "no reply"

    monkeypatch.setattr(oracle_mcp, "_run_tailscale", fake_run)

    result = await oracle_mcp._tailnet_diagnostics("http://100.107.126.121:8081")

    assert result["peer_found"] is True
    assert result["peer_online"] is False
    assert result["ping_ok"] is False
    assert result["ping_error"] == "no reply"


@pytest.mark.asyncio
async def test_tailnet_diagnostics_rejects_unparseable_endpoint():
    result = await oracle_mcp._tailnet_diagnostics("not-a-url")

    assert result["peer_found"] is False
    assert result["ping_ok"] is False
    assert "error" in result
