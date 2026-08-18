"""Tests for api.routes.routing_analytics."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes.routing_analytics import router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
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
        response = client.get("/api/v1/routing/health")

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
        response = client.get("/api/v1/routing/health/openai")

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
        response = client.get("/api/v1/routing/health/missing")

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
        response = client.get("/api/v1/routing/costs")

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
        response = client.get("/api/v1/routing/status")

    assert response.status_code == 200
    data = response.json()
    assert data["available"] is True
    assert data["strategy"] == "balanced"
    assert data["providers"] == fake_inventory


def test_list_routing_strategies_returns_all_strategies():
    client = _client()

    response = client.get("/api/v1/routing/strategies")

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
        response = client.get("/api/v1/routing/providers/analytics")

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
        response = client.post("/api/v1/routing/test/openai")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_test_provider_not_found():
    client = _client()

    with patch(
        "api.routes.routing_analytics.health_monitor.probe_provider",
        new_callable=AsyncMock,
        return_value={"error": "missing"},
    ):
        response = client.post("/api/v1/routing/test/missing")

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
        response = client.get("/api/v1/routing/audit?limit=5000")

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["current_cost_weight"] == 0.35


def test_get_routing_observability_composes_dashboard_payload():
    client = _client()

    fake_registry = MagicMock()
    fake_registry.metrics_snapshot.return_value = {
        "providers": {
            "openai": {
                "ewma_latency_ms": 120.0,
                "latency_percentiles_ms": {"p50": 100.0, "p90": 140.0, "p95": 150.0, "p99": 160.0},
                "latency_sample_count": 5,
                "total_cost_usd": 0.42,
                "success_rate": 0.98,
                "ewma_tokens_per_sec": 42.0,
            }
        },
        "current_hour_bucket": "2026071812",
        "current_hour_spend": {"openai": 0.12},
        "current_hour_spend_total": 0.12,
    }
    fake_registry.get_audit_trail.return_value = [
        {
            "event": "outcome",
            "request_id": "route-1",
            "provider_id": "openai",
            "timestamp": 10.0,
            "selected_model": "gpt-4o-mini",
            "actual_latency_ms": 123.0,
            "actual_cost_usd": 0.01,
            "latency_ms": 123,
            "cost_usd": 0.01,
            "visible_outcome": "success",
            "fallback_reason": "provider_fallback",
            "alternatives_considered": ["openai", "anthropic"],
            "context_sources": ["context_assembly", "tools"],
            "tool_usage": {"count": 2, "tool_names": ["search_web", "summarize"]},
        }
    ]
    fake_decisions = [
        {
            "routing_id": "route-1",
            "created_at": 9.0,
            "task_type": "coding",
            "chosen_provider": "openai",
            "selection_reason": "openai ranked first; confidence=0.60, margin=0.20.",
            "ml_confidence": {
                "selected_confidence": 0.6,
                "runner_up_confidence": 0.4,
                "selection_margin": 0.2,
            },
            "prompt_classification": {
                "task_type": "coding",
                "intent": "coding",
                "intent_confidence": 0.9,
            },
            "fallback_reasons": [
                {"provider_id": "anthropic", "reason": "ranked_below_selected_provider"}
            ],
            "candidates": [
                {"provider_id": "openai", "score": 0.9, "pct": 60},
                {"provider_id": "anthropic", "score": 0.7, "pct": 40},
            ],
            "routing_waterfall": [
                {"stage": "prompt", "duration_ms": 1.0, "attributes": {"source": "prompt"}},
                {"stage": "selection", "duration_ms": 2.0, "attributes": {}},
            ],
        }
    ]

    with (
        patch(
            "api.routes.routing_analytics.health_monitor.refresh",
            new_callable=AsyncMock,
        ),
        patch(
            "api.routes.routing_analytics.health_monitor.get_all_status",
            return_value={
                "openai": {
                    "avg_latency_ms": 110.0,
                    "latency_percentiles_ms": {
                        "p50": 100.0,
                        "p90": 120.0,
                        "p95": 130.0,
                        "p99": 140.0,
                    },
                    "latency_sample_count": 4,
                }
            },
        ),
        patch("api.routes.routing_analytics.registry", fake_registry),
        patch(
            "api.routes.routing_analytics.get_recent_explanations",
            return_value=fake_decisions,
        ),
    ):
        response = client.get("/api/v1/routing/observability")

    assert response.status_code == 200
    data = response.json()
    assert data["routing_waterfall"]["stage_summary"]["prompt"]["avg_ms"] == 1.0
    assert data["provider_timelines"]["openai"][0]["event"] == "outcome"
    assert data["provider_timelines"]["openai"][0]["selected_model"] == "gpt-4o-mini"
    assert data["provider_timelines"]["openai"][0]["visible_outcome"] == "success"
    assert data["provider_timelines"]["openai"][0]["context_sources"] == [
        "context_assembly",
        "tools",
    ]
    assert data["cost_dashboard"]["current_hour_spend_total"] == 0.12
    assert data["selection_reasons"][0]["chosen_provider"] == "openai"
    assert data["fallback_reasons"][0]["reasons"][0]["provider_id"] == "anthropic"
    assert data["prompt_classification"][0]["intent"] == "coding"
    assert data["ml_confidence"][0]["selection_margin"] == 0.2
    assert (
        data["latency_percentiles"]["providers"]["openai"]["dispatch"]["latency_sample_count"] == 5
    )


def test_get_routing_weight_returns_cost_and_latency_split():
    client = _client()

    fake_hybrid = MagicMock()
    fake_hybrid.cost_weight = 0.25

    with patch(
        "api.routes.routing_analytics.hybrid_router",
        fake_hybrid,
    ):
        response = client.get("/api/v1/routing/weight")

    assert response.status_code == 200
    data = response.json()
    assert data["cost_weight"] == 0.25
    assert data["latency_weight"] == 0.75
