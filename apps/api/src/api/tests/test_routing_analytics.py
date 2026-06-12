"""Tests for api.routes.routing_analytics."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes.routing_analytics import router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_get_provider_health_returns_summary():
    client = _client()

    with (
        patch(
            "api.routes.routing_analytics.health_monitor.refresh",
            new_callable=AsyncMock,
        ) as mock_refresh,
        patch(
            "api.routes.routing_analytics.health_monitor.get_all_status",
            return_value={"openai": {"status": "healthy"}},
        ),
        patch(
            "api.routes.routing_analytics.health_monitor.get_healthy_providers",
            return_value=["openai"],
        ),
        patch(
            "api.routes.routing_analytics.health_monitor.get_best_providers",
            return_value=["openai"],
        ),
    ):
        response = client.get("/routing/health")

    assert response.status_code == 200
    assert response.json()["available"] is True
    assert mock_refresh.await_count == 1


def test_get_provider_health_detail_success():
    client = _client()

    with (
        patch(
            "api.routes.routing_analytics.health_monitor.probe_provider",
            new_callable=AsyncMock,
            return_value={"status": "healthy"},
        ),
        patch(
            "api.routes.routing_analytics.health_monitor.get_status",
            return_value={"status": "healthy"},
        ),
    ):
        response = client.get("/routing/health/openai")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_get_provider_health_detail_not_found():
    client = _client()

    with (
        patch(
            "api.routes.routing_analytics.health_monitor.probe_provider",
            new_callable=AsyncMock,
            return_value={"error": "not found"},
        ),
        patch(
            "api.routes.routing_analytics.health_monitor.get_status",
            return_value={"error": "not found"},
        ),
    ):
        response = client.get("/routing/health/missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "not found"


def test_get_cost_tracking_returns_router_status():
    client = _client()

    fake_tracker = MagicMock()
    fake_tracker.get_status.return_value = {"requests": 10}

    with patch(
        "api.routes.routing_analytics.smart_router.cost_tracker",
        fake_tracker,
    ):
        response = client.get("/routing/costs")

    assert response.status_code == 200
    assert response.json()["requests"] == 10


def test_get_routing_status_includes_inventory_and_router_status():
    client = _client()

    fake_inventory = [{"id": "openai", "name": "OpenAI"}]
    fake_router = MagicMock()
    fake_router.get_status.return_value = {"strategy": "balanced"}

    with (
        patch(
            "api.routes.routing_analytics.health_monitor.refresh",
            new_callable=AsyncMock,
        ),
        patch(
            "api.routes.routing_analytics.smart_router",
            fake_router,
        ),
        patch(
            "api.routes.routing_analytics.dispatcher.get_provider_inventory",
            new_callable=AsyncMock,
            return_value=fake_inventory,
        ),
    ):
        response = client.get("/routing/status")

    assert response.status_code == 200
    data = response.json()
    assert data["available"] is True
    assert data["strategy"] == "balanced"
    assert data["providers"] == fake_inventory


def test_list_routing_strategies_returns_all_strategies():
    client = _client()

    response = client.get("/routing/strategies")

    assert response.status_code == 200
    data = response.json()
    assert len(data["strategies"]) >= 5
    assert "default" in data


def test_list_available_providers_maps_provider_data():
    client = _client()

    fake_inventory = [
        {
            "id": "openai",
            "name": "OpenAI",
            "tier": "cloud",
            "capabilities": ["chat"],
            "models": ["gpt-4o-mini"],
        }
    ]
    fake_registry = MagicMock()
    fake_registry.snapshot.return_value = {"openai": {"requests": 3}}

    with (
        patch(
            "api.routes.routing_analytics.health_monitor.refresh",
            new_callable=AsyncMock,
        ),
        patch(
            "api.routes.routing_analytics.dispatcher.get_provider_inventory",
            new_callable=AsyncMock,
            return_value=fake_inventory,
        ),
        patch(
            "api.routes.routing_analytics.registry",
            fake_registry,
        ),
        patch(
            "api.routes.routing_analytics.health_monitor.get_status",
            return_value={"status": "healthy"},
        ),
    ):
        response = client.get("/routing/providers")

    assert response.status_code == 200
    providers = response.json()["providers"]
    assert providers["openai"]["name"] == "OpenAI"
    assert providers["openai"]["routing_stats"] == {"requests": 3}


def test_test_provider_success():
    client = _client()

    with patch(
        "api.routes.routing_analytics.health_monitor.probe_provider",
        new_callable=AsyncMock,
        return_value={"status": "healthy"},
    ):
        response = client.post("/routing/test/openai")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_test_provider_not_found():
    client = _client()

    with patch(
        "api.routes.routing_analytics.health_monitor.probe_provider",
        new_callable=AsyncMock,
        return_value={"error": "missing"},
    ):
        response = client.post("/routing/test/missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "missing"


def test_get_routing_audit_clamps_limit_and_returns_count():
    client = _client()

    fake_registry = MagicMock()
    fake_registry.get_audit_trail.return_value = [{"id": 1}]
    fake_hybrid = MagicMock()
    fake_hybrid.cost_weight = 0.35

    with (
        patch(
            "api.routes.routing_analytics.registry",
            fake_registry,
        ),
        patch(
            "api.routes.routing_analytics.hybrid_router",
            fake_hybrid,
        ),
    ):
        response = client.get("/routing/audit?limit=5000")

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["current_cost_weight"] == 0.35


def test_get_routing_weight_returns_cost_and_latency_split():
    client = _client()

    fake_hybrid = MagicMock()
    fake_hybrid.cost_weight = 0.25

    with patch(
        "api.routes.routing_analytics.hybrid_router",
        fake_hybrid,
    ):
        response = client.get("/routing/weight")

    assert response.status_code == 200
    data = response.json()
    assert data["cost_weight"] == 0.25
    assert data["latency_weight"] == 0.75
