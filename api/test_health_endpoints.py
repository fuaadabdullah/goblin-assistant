"""Tests for health endpoints"""

from typing import Dict


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "components" in data


def test_health_all(client):
    resp = client.get("/health/all")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "components" in data
    assert "chroma" in data["components"]


def test_component_endpoints(client):
    for path in [
        "/health/chroma/status",
        "/health/mcp/status",
        "/health/raptor/status",
        "/health/sandbox/status",
        "/health/cost-tracking",
    ]:
        resp = client.get(path)
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data or "total_cost" in data


def test_latency_and_errors(client):
    resp = client.get("/health/latency-history/raptor")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "raptor"

    resp = client.get("/health/service-errors/raptor")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "raptor"


def test_retest(client):
    resp = client.post("/health/retest/raptor")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "raptor"
    assert data["retest"] == "scheduled"
