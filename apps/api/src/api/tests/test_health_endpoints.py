"""Tests for health endpoints"""

import os
from importlib import import_module
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    os.environ.setdefault("LOCAL_LLM_API_KEY", "test-local-llm-key")
    mod = import_module("api.main")
    app = getattr(mod, "app")
    with TestClient(app) as test_client:
        yield test_client


def _health_patches():
    return (
        patch("api.health.check_routing_health", new=AsyncMock(return_value={"status": "healthy"})),
        patch("api.health.check_db_health", new=AsyncMock(return_value={"status": "healthy"})),
        patch("api.health.check_redis_health", new=AsyncMock(return_value={"status": "healthy"})),
        patch("api.health.check_api_health", new=AsyncMock(return_value={"status": "healthy"})),
        patch("api.health._check_chroma", new=AsyncMock(return_value={"status": "healthy"})),
        patch("api.health._check_mcp", new=AsyncMock(return_value={"status": "healthy"})),
        patch("api.health._check_raptor", new=AsyncMock(return_value={"status": "healthy"})),
        patch("api.health._check_sandbox", new=AsyncMock(return_value={"status": "healthy"})),
        patch(
            "api.health._check_cost_tracking",
            new=AsyncMock(return_value={"status": "healthy", "total_cost": 0.0}),
        ),
        patch(
            "api.services.provider_health.health_monitor.get_all_status",
            return_value={"openai": {"status": "healthy"}},
        ),
        patch("api.security_config.SecurityConfig.validate_config", return_value=[]),
        patch("api.security_config.SecurityConfig.DEBUG", False),
        patch("api.security_config.SecurityConfig.ALLOWED_ORIGINS", ["https://example.com"]),
    )


def test_health(client):
    patches = _health_patches()
    with (
        patches[0],
        patches[1],
        patches[2],
        patches[3],
        patches[4],
        patches[5],
        patches[6],
        patches[7],
        patches[8],
        patches[9],
        patches[10],
        patches[11],
        patches[12],
    ):
        resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "components" in data


def test_health_uses_cached_provider_status(client):
    patches = _health_patches()
    with (
        patch(
            "api.services.provider_health.health_monitor.refresh",
            new_callable=AsyncMock,
        ) as refresh,
        patch(
            "api.services.provider_health.dispatcher.get_provider_inventory",
            new_callable=AsyncMock,
        ) as inventory,
        patches[0],
        patches[1],
        patches[2],
        patches[3],
        patches[4],
        patches[5],
        patches[6],
        patches[7],
        patches[8],
        patches[9],
        patches[10],
        patches[11],
        patches[12],
    ):
        resp = client.get("/api/v1/health")

    assert resp.status_code == 200
    refresh.assert_not_awaited()
    inventory.assert_not_awaited()


def test_health_all(client):
    resp = client.get("/api/v1/health/all")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "components" in data
    assert "chroma" in data["components"]


def test_component_endpoints(client):
    for path in [
        "/api/v1/health/chroma/status",
        "/api/v1/health/mcp/status",
        "/api/v1/health/raptor/status",
        "/api/v1/health/sandbox/status",
        "/api/v1/health/cost-tracking",
    ]:
        resp = client.get(path)
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data or "total_cost" in data


def test_latency_and_errors(client):
    resp = client.get("/api/v1/health/latency-history/raptor")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "raptor"

    resp = client.get("/api/v1/health/service-errors/raptor")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "raptor"


def test_retest(client):
    resp = client.post("/api/v1/health/retest/raptor")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "raptor"
    assert data["retest"] == "scheduled"


def test_health_providers(client):
    """Live provider probe returns per-provider status and an aggregate."""
    with (
        patch(
            "api.services.provider_health.health_monitor.refresh",
            new_callable=AsyncMock,
        ) as refresh,
        patch(
            "api.services.provider_health.health_monitor.get_all_status",
            return_value={
                "openai": {"status": "healthy", "configured": True},
                "anthropic": {"status": "billing_issue", "configured": True},
            },
        ),
    ):
        resp = client.get("/api/v1/health/providers")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "warnings"
    assert data["providers_checked"] == 2
    assert data["providers_configured"] == 2
    assert data["providers"]["openai"]["status"] == "healthy"
    refresh.assert_awaited_once()


def test_health_providers_degraded_when_none_healthy(client):
    with (
        patch(
            "api.services.provider_health.health_monitor.refresh",
            new_callable=AsyncMock,
        ),
        patch(
            "api.services.provider_health.health_monitor.get_all_status",
            return_value={"openai": {"status": "unhealthy", "configured": True}},
        ),
    ):
        resp = client.get("/api/v1/health/providers")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "degraded"
    assert data["providers_checked"] == 1


def test_health_providers_graceful_on_monitor_failure(client):
    """A failing monitor must degrade the payload, not the endpoint."""
    with patch(
        "api.services.provider_health.health_monitor.refresh",
        new=AsyncMock(side_effect=RuntimeError("monitor exploded")),
    ):
        resp = client.get("/api/v1/health/providers")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "degraded"
    assert "monitor exploded" in data["error"]
    assert data["providers"] == {}


def test_health_providers_not_shadowed_by_component_route(client):
    """/health/providers must resolve to the provider probe, not /health/{component}."""
    with (
        patch(
            "api.services.provider_health.health_monitor.refresh",
            new_callable=AsyncMock,
        ),
        patch(
            "api.services.provider_health.health_monitor.get_all_status",
            return_value={},
        ),
    ):
        resp = client.get("/api/v1/health/providers")

    # The {component} route would 404 on "providers"; the real endpoint answers 200.
    assert resp.status_code == 200
    assert "providers_checked" in resp.json()


def test_health_streaming_not_shadowed_by_component_route(client):
    """/health/streaming is registered before /health/{component} and reachable."""
    resp = client.get("/api/v1/health/streaming")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "streaming"
    assert "status" in data
