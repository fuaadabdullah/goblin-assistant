"""Engine contract tests — Observability pillar.

These tests assert that the Observability pillar's public contract
(documented in docs/architecture/ENGINE_CONTRACTS.md) is upheld.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import health
from api.routes import routing_analytics


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(health.router, prefix="/api/v1")
    return TestClient(app)


# ── Health Summary Contract ────────────────────────────────────────────


class TestHealthSummaryContract:
    """Contract: GET /api/v1/health returns top-level summary."""

    def test_health_returns_200(self, client):
        """Health endpoint must return 200 (not 500, even if components are degraded)."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_health_has_required_fields(self, client):
        """Health response must contain status and components."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ("healthy", "degraded", "unhealthy")
        assert "version" in data
        assert isinstance(data["version"], str)
        assert "timestamp" in data

    def test_health_components_are_present(self, client):
        """Health response must include critical components."""
        response = client.get("/api/v1/health")
        data = response.json()
        assert "components" in data
        components = data["components"]
        # At minimum, api must be present
        assert "api" in components

    def test_each_component_has_status(self, client):
        """Each component must have a status field."""
        response = client.get("/api/v1/health")
        data = response.json()
        for name, component in data.get("components", {}).items():
            assert "status" in component, f"Component {name} missing status"
            assert component["status"] in (
                "healthy",
                "degraded",
                "unhealthy",
                "unknown",
            )


# ── Health Detail Contract ─────────────────────────────────────────────


class TestHealthDetailContract:
    """Contract: GET /api/v1/health/all returns detailed component status."""

    def test_health_all_returns_200(self, client):
        """Health all endpoint must return 200."""
        response = client.get("/api/v1/health/all")
        assert response.status_code == 200

    def test_health_all_has_status(self, client):
        """Health all response must have status and component details."""
        response = client.get("/api/v1/health/all")
        data = response.json()
        assert "status" in data

    def test_health_all_contains_providers(self, client):
        """Health all should include provider health when available."""
        response = client.get("/api/v1/health/all")
        data = response.json()
        components = data.get("components", {})
        # Components may or may not include providers depending on config
        if "providers" in components:
            assert "status" in components["providers"]
            if "details" in components["providers"]:
                details = components["providers"]["details"]
                assert "configured" in details
                assert "healthy" in details


# ── Component Health Contract ──────────────────────────────────────────


class TestComponentHealthContract:
    """Contract: GET /api/v1/health/{component} returns component-specific status."""

    @pytest.mark.parametrize("component", ["api", "database", "redis", "routing"])
    def test_known_component_returns_200(self, client, component):
        """Known components should return 200."""
        response = client.get(f"/api/v1/health/{component}")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_unknown_component_returns_404(self, client):
        """Unknown component returns 404."""
        response = client.get("/api/v1/health/nonexistent_component")
        assert response.status_code == 404


# ── Readiness / Liveness Contract ──────────────────────────────────────


class TestReadinessLivenessContract:
    """Contract: Readiness and liveness probes return appropriate status."""

    def test_readiness_returns_200(self, client):
        """Readiness probe must return 200 when the service is ready."""
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 200

    def test_liveness_returns_200(self, client):
        """Liveness probe must return 200 when the service is alive."""
        response = client.get("/api/v1/health/live")
        assert response.status_code == 200


# ── Cost Tracking Contract ─────────────────────────────────────────────


class TestCostTrackingContract:
    """Contract: GET /api/v1/health/cost-tracking reports cost system status."""

    def test_cost_tracking_endpoint_exists(self, client):
        """Cost tracking endpoint should respond."""
        response = client.get("/api/v1/health/cost-tracking")
        # 200 = available, 503 = unavailable, 404 = not implemented
        assert response.status_code in (200, 404, 503)
        if response.status_code == 200:
            data = response.json()
            assert "status" in data


# ── Version Contract ───────────────────────────────────────────────────


class TestVersionContract:
    """Contract: Every health response includes a version string."""

    def test_health_has_semver_style_version(self, client):
        """Version should be a non-empty string following semver-ish format."""
        response = client.get("/api/v1/health")
        data = response.json()
        version = data.get("version", "")
        assert isinstance(version, str)
        assert len(version) > 0
        # Should contain at least one dot (x.y or x.y.z)
        assert "." in version


class TestRoutingObservabilityContract:
    """Contract: routing observability includes rich outcome metadata."""

    def test_routing_observability_exposes_rich_request_fields(self):
        app = FastAPI()
        app.include_router(routing_analytics.router, prefix="/api/v1")
        client = TestClient(app)

        fake_registry = MagicMock()
        fake_registry.metrics_snapshot.return_value = {
            "providers": {
                "openai": {
                    "ewma_latency_ms": 120.0,
                    "latency_percentiles_ms": {
                        "p50": 100.0,
                        "p90": 140.0,
                        "p95": 150.0,
                        "p99": 160.0,
                    },
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
                "failure_class": None,
            }
        ]
        fake_decisions = [
            {
                "routing_id": "route-1",
                "created_at": 9.0,
                "task_type": "coding",
                "chosen_provider": "openai",
                "selection_reason": "openai ranked first",
                "ml_confidence": {"selected_confidence": 0.6},
                "prompt_classification": {"intent": "coding"},
                "fallback_reasons": [
                    {"provider_id": "anthropic", "reason": "ranked_below_selected_provider"}
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
        assert data["provider_timelines"]["openai"][0]["selected_model"] == "gpt-4o-mini"
        assert data["provider_timelines"]["openai"][0]["visible_outcome"] == "success"
        assert data["provider_timelines"]["openai"][0]["fallback_reason"] == "provider_fallback"
        assert data["provider_timelines"]["openai"][0]["alternatives_considered"] == [
            "openai",
            "anthropic",
        ]
        assert data["provider_timelines"]["openai"][0]["context_sources"] == [
            "context_assembly",
            "tools",
        ]
        assert data["provider_timelines"]["openai"][0]["tool_usage"] == {
            "count": 2,
            "tool_names": ["search_web", "summarize"],
        }
        assert data["provider_timelines"]["openai"][0]["failure_class"] is None
        assert data["selection_reasons"][0]["chosen_provider"] == "openai"
        assert data["fallback_reasons"][0]["reasons"][0]["provider_id"] == "anthropic"
        assert data["routing_waterfall"]["stage_summary"]["prompt"]["avg_ms"] == 1.0
