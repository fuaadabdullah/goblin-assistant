"""Security controls on the node control plane.

These cover the three things that make the difference between "a registry"
and "an SSRF primitive that also happens to track GPUs".
"""

from __future__ import annotations

import time
from dataclasses import replace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.nodes import auth as auth_mod
from api.nodes.config import node_settings
from api.nodes.endpoint_policy import InvalidEndpoint, validate_endpoint
from api.nodes.registry import node_registry
from api.nodes.router import router

SECRET = "correct-horse-battery-staple"
AUTH = {"Authorization": "Bearer " + SECRET}

HEARTBEAT = {
    "node_id": "node-001",
    "node_type": "inference",
    "status": "online",
    "backend": "ollama",
    "gpu": "RTX 3060 12GB",
    "models": ["llama3.1:8b"],
    "active_jobs": 0,
    "max_concurrency": 1,
    "endpoint": "https://node-001.tailnet:8090",
}


@pytest.fixture
def app_client(monkeypatch):
    monkeypatch.setattr(
        auth_mod, "node_settings", replace(node_settings, registration_secret=SECRET)
    )
    node_registry.clear()
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as c:
        yield c
    node_registry.clear()


# --- heartbeat authentication --------------------------------------------


def test_heartbeat_without_credentials_is_rejected(app_client):
    resp = app_client.post("/nodes/heartbeat", json=HEARTBEAT)
    assert resp.status_code == 401
    assert node_registry.get("node-001") is None, "must not register an unauthenticated node"


def test_heartbeat_with_wrong_secret_is_rejected(app_client):
    resp = app_client.post(
        "/nodes/heartbeat", json=HEARTBEAT, headers={"Authorization": "Bearer wrong"}
    )
    assert resp.status_code == 401
    assert node_registry.get("node-001") is None


def test_heartbeat_with_correct_secret_is_accepted(app_client):
    assert app_client.post("/nodes/heartbeat", json=HEARTBEAT, headers=AUTH).status_code == 200
    assert node_registry.get("node-001") is not None


def test_unconfigured_secret_fails_closed(monkeypatch):
    """No secret configured must mean no registration, not open registration."""
    monkeypatch.setattr(
        auth_mod, "node_settings", replace(node_settings, registration_secret="")
    )
    node_registry.clear()
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as c:
        resp = c.post("/nodes/heartbeat", json=HEARTBEAT, headers=AUTH)
    assert resp.status_code == 503
    assert node_registry.get("node-001") is None


def test_operator_routes_require_authentication(app_client):
    """Listing and eviction are not anonymous operations."""
    app_client.post("/nodes/heartbeat", json=HEARTBEAT, headers=AUTH)
    assert app_client.get("/nodes").status_code == 401
    assert app_client.get("/nodes/node-001").status_code == 401
    assert app_client.delete("/nodes/node-001").status_code == 401
    assert node_registry.get("node-001") is not None, "unauthorized DELETE must not evict"


# --- endpoint policy (SSRF / prompt exfiltration) -------------------------


def test_without_an_allowlist_a_valid_url_to_any_host_is_accepted(app_client):
    """Documents the residual risk rather than pretending it away.

    With no GOBLIN_NODE_ENDPOINT_ALLOWLIST set, a structurally valid https URL
    to an arbitrary host IS accepted. Authentication is what stops an attacker
    reaching this point at all -- but if the registration secret leaks, only
    the allowlist prevents the leak becoming prompt exfiltration. Hence the
    deployment guidance to always set it.
    """
    evil = {**HEARTBEAT, "endpoint": "https://evil.example.com/collect"}
    resp = app_client.post("/nodes/heartbeat", json=evil, headers=AUTH)
    assert resp.status_code == 200
    assert node_registry.get("node-001").endpoint == "https://evil.example.com/collect"


def test_with_an_allowlist_the_attacker_host_is_refused(app_client, monkeypatch):
    """The control that actually closes the exfiltration path."""
    monkeypatch.setattr(
        "api.nodes.endpoint_policy.node_settings",
        replace(node_settings, endpoint_allowlist=("node-001.tailnet",)),
    )
    evil = {**HEARTBEAT, "endpoint": "https://evil.example.com/collect"}
    resp = app_client.post("/nodes/heartbeat", json=evil, headers=AUTH)
    assert resp.status_code == 422
    assert node_registry.get("node-001") is None


@pytest.mark.parametrize(
    "bad",
    [
        "file:///etc/passwd",
        "gopher://internal:70/",
        "ftp://internal/",
        "https://user:pass@node.internal:8090",
        "https://node.internal:8090/?exfil=1",
        "https://node.internal:8090/#frag",
        "http://198.51.100.7:8090",
        "",
        "   ",
        "not-a-url",
    ],
)
def test_dangerous_endpoints_are_rejected(bad):
    with pytest.raises(InvalidEndpoint):
        validate_endpoint(bad)


def test_http_is_allowed_to_loopback_only():
    assert validate_endpoint("http://127.0.0.1:8090") == "http://127.0.0.1:8090"
    assert validate_endpoint("http://localhost:8090") == "http://localhost:8090"
    with pytest.raises(InvalidEndpoint):
        validate_endpoint("http://10.0.0.5:8090")


def test_https_endpoint_is_accepted_and_normalised():
    assert validate_endpoint("https://node-001.tailnet:8090/") == "https://node-001.tailnet:8090"


def test_allowlist_blocks_unlisted_hosts():
    cfg = replace(node_settings, endpoint_allowlist=("node-001.tailnet",))
    assert validate_endpoint("https://node-001.tailnet:8090", settings=cfg)
    with pytest.raises(InvalidEndpoint):
        validate_endpoint("https://evil.example.com", settings=cfg)


def test_heartbeat_rejects_a_bad_endpoint_with_422(app_client):
    bad = {**HEARTBEAT, "endpoint": "https://user:pass@node.internal:8090"}
    resp = app_client.post("/nodes/heartbeat", json=bad, headers=AUTH)
    assert resp.status_code == 422
    assert "rejected endpoint" in resp.json()["detail"]
    assert node_registry.get("node-001") is None


@pytest.mark.asyncio
async def test_dispatch_revalidates_endpoint_against_current_policy(monkeypatch):
    """A node registered under looser rules must not bypass a later allowlist."""
    from api.nodes.dispatch import try_local_compute
    from api.nodes.models import NodeHeartbeat
    from api.nodes.registry import NodeRegistry

    reg = NodeRegistry()
    reg.upsert(
        NodeHeartbeat(
            node_id="node-001",
            models=["llama3.1:8b"],
            max_concurrency=1,
            endpoint="https://sneaky.example.com:8090",
        )
    )
    monkeypatch.setattr(
        "api.nodes.dispatch.node_settings", replace(node_settings, enabled=True)
    )
    monkeypatch.setattr(
        "api.nodes.endpoint_policy.node_settings",
        replace(node_settings, endpoint_allowlist=("node-001.tailnet",)),
    )

    result = await try_local_compute(
        "chat", {"prompt": "secret", "model": "llama3.1:8b"}, registry=reg
    )
    assert result is None, "must refuse to dial a now-disallowed host"


# --- default posture -------------------------------------------------------


def test_local_compute_ships_disabled():
    """The tier is a deployment gate, not a default."""
    import os

    if "GOBLIN_LOCAL_NODES_ENABLED" in os.environ:
        pytest.skip("environment overrides the default")
    assert node_settings.enabled is False


# --- timeout policy --------------------------------------------------------


def test_connect_timeout_is_much_tighter_than_read():
    """Finding out a node is absent must be fast; generating may be slow."""
    assert node_settings.connect_timeout_seconds <= 5
    assert node_settings.read_timeout_seconds >= 60
    assert node_settings.connect_timeout_seconds < node_settings.read_timeout_seconds


@pytest.mark.asyncio
async def test_blackholed_network_falls_back_within_the_connect_budget(monkeypatch):
    """A firewall that drops packets must not cost the user a long stall.

    198.51.100.0/24 is TEST-NET-2 (RFC 5737): reserved for documentation and
    guaranteed not routable, so the SYN goes nowhere rather than being
    refused -- which is exactly the blackhole case a killed process does not
    reproduce.
    """
    from api.nodes.client import NodeUnavailable, invoke_node, reset_ssl_context

    monkeypatch.setattr(
        "api.nodes.client.node_settings",
        replace(node_settings, connect_timeout_seconds=2.0, read_timeout_seconds=300.0),
    )
    reset_ssl_context()

    started = time.perf_counter()
    with pytest.raises(NodeUnavailable):
        await invoke_node(
            endpoint="https://198.51.100.7:8090",
            model="llama3.1:8b",
            prompt="hi",
        )
    elapsed = time.perf_counter() - started
    reset_ssl_context()

    assert elapsed < 10, (
        "blackholed node took {:.1f}s to fail; a tight connect timeout is the "
        "whole point".format(elapsed)
    )
