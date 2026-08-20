"""HTTP contract for /nodes — the surface goblin-node-agent actually calls."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.nodes.config import node_settings
from api.nodes.registry import node_registry
from api.nodes.router import router

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


SECRET = "test-node-secret"
AUTH = {"Authorization": "Bearer " + SECRET}


@pytest.fixture
def client(monkeypatch):
    from dataclasses import replace

    from api.nodes import auth as auth_mod

    monkeypatch.setattr(
        auth_mod, "node_settings", replace(node_settings, registration_secret=SECRET)
    )
    node_registry.clear()
    app = FastAPI()
    app.include_router(router)
    # Operator routes sit behind the normal authenticated-user dependency;
    # stand in a fake user so these tests exercise the route, not the login.
    # api.nodes.__init__ re-exports the APIRouter as `router`, shadowing the
    # submodule attribute, so reach the module itself via importlib.
    import importlib

    nodes_router_mod = importlib.import_module("api.nodes.router")
    if nodes_router_mod._get_current_user is not None:
        app.dependency_overrides[nodes_router_mod._get_current_user] = lambda: {"id": "tester"}
    with TestClient(app) as c:
        yield c
    node_registry.clear()


def test_heartbeat_accepts_the_agent_payload(client):
    resp = client.post("/nodes/heartbeat", json=HEARTBEAT, headers=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["node_id"] == "node-001"
    assert body["registered"] is True


def test_second_heartbeat_is_a_refresh_not_a_registration(client):
    client.post("/nodes/heartbeat", json=HEARTBEAT, headers=AUTH)
    body = client.post("/nodes/heartbeat", json=HEARTBEAT, headers=AUTH).json()
    assert body["registered"] is False
    assert len(client.get("/nodes").json()) == 1


def test_heartbeat_rejects_a_payload_with_no_node_id(client):
    bad = {k: v for k, v in HEARTBEAT.items() if k != "node_id"}
    assert client.post("/nodes/heartbeat", json=bad, headers=AUTH).status_code == 422


def test_heartbeat_rejects_an_unknown_status(client):
    assert client.post(
        "/nodes/heartbeat", json={**HEARTBEAT, "status": "vibing"}, headers=AUTH
    ).status_code == 422


def test_heartbeat_rejects_negative_active_jobs(client):
    assert client.post(
        "/nodes/heartbeat", json={**HEARTBEAT, "active_jobs": -1}, headers=AUTH
    ).status_code == 422


def test_list_nodes_exposes_what_the_router_sees(client):
    client.post("/nodes/heartbeat", json=HEARTBEAT, headers=AUTH)
    node = client.get("/nodes").json()[0]
    assert node["node_id"] == "node-001"
    assert node["status"] == "online"
    assert node["eligible"] is True
    assert node["age_seconds"] < 5


def test_saturated_node_is_listed_but_not_eligible(client):
    client.post("/nodes/heartbeat", json={**HEARTBEAT, "active_jobs": 1}, headers=AUTH)
    node = client.get("/nodes").json()[0]
    assert node["status"] == "online", "still healthy, just busy"
    assert node["eligible"] is False


def test_get_unknown_node_is_404(client):
    assert client.get("/nodes/node-999").status_code == 404


def test_node_can_be_forgotten_immediately(client):
    client.post("/nodes/heartbeat", json=HEARTBEAT, headers=AUTH)
    assert client.delete("/nodes/node-001").status_code == 200
    assert client.get("/nodes").json() == []
    assert client.delete("/nodes/node-001").status_code == 404


def test_agent_payload_shape_is_accepted_verbatim(client):
    """Guards the wire contract against drift in either repo.

    This is the literal document goblin-node-agent publishes; if this test
    fails, deployed nodes have stopped being able to register.
    """
    agent_payload = {
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
    assert client.post("/nodes/heartbeat", json=agent_payload, headers=AUTH).status_code == 200
