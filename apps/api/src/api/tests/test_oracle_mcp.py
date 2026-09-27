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


def test_oci_config_accepts_base64_key_content(monkeypatch):
    import base64

    pem = "-----BEGIN PRIVATE KEY-----\nTEST\n-----END PRIVATE KEY-----\n"
    monkeypatch.setenv("OCI_MCP_TENANCY", "tenancy")
    monkeypatch.setenv("OCI_MCP_USER", "user")
    monkeypatch.setenv("OCI_MCP_FINGERPRINT", "aa:bb")
    monkeypatch.setenv("OCI_MCP_REGION", "us-ashburn-1")
    monkeypatch.setenv(
        "OCI_MCP_PRIVATE_KEY_B64",
        base64.b64encode(pem.encode()).decode(),
    )
    monkeypatch.setattr(oracle_mcp.oci.config, "validate_config", lambda _config: None)

    config = oracle_mcp._oci_config()

    assert config["tenancy"] == "tenancy"
    assert config["user"] == "user"
    assert config["region"] == "us-ashburn-1"
    assert config["key_content"] == pem


@pytest.mark.asyncio
async def test_oci_control_status_reports_safe_readiness(monkeypatch):
    monkeypatch.setattr(
        oracle_mcp,
        "_oci_config",
        lambda: {
            "tenancy": "hidden",
            "user": "hidden",
            "fingerprint": "hidden",
            "region": "us-ashburn-1",
            "key_content": "hidden",
        },
    )
    monkeypatch.setattr(
        oracle_mcp,
        "_safe_instances_sync",
        lambda _config: [{"name": "goblin-core", "state": "RUNNING"}],
    )

    result = await oracle_mcp._oci_control_status()

    assert result == {
        "configured": True,
        "credentials_valid": True,
        "region": "us-ashburn-1",
        "instance_count": 1,
        "write_scope": "restricted_by_oci_iam",
    }
    assert "tenancy" not in result
    assert "user" not in result
    assert "fingerprint" not in result


@pytest.mark.asyncio
async def test_oci_compute_inventory_returns_safe_metadata(monkeypatch):
    monkeypatch.setattr(
        oracle_mcp,
        "_oci_config",
        lambda: {
            "tenancy": "hidden",
            "user": "hidden",
            "fingerprint": "hidden",
            "region": "us-ashburn-1",
            "key_content": "hidden",
        },
    )
    instances = [
        {
            "name": "goblin-core",
            "state": "RUNNING",
            "shape": "VM.Standard.A1.Flex",
            "availability_domain": "AD-1",
            "time_created": "2026-09-27T10:00:00+00:00",
        }
    ]
    monkeypatch.setattr(oracle_mcp, "_safe_instances_sync", lambda _config: instances)

    result = await oracle_mcp._oci_compute_inventory()

    assert result["region"] == "us-ashburn-1"
    assert result["count"] == 1
    assert result["instances"] == instances
