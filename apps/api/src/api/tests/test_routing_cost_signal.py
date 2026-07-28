from __future__ import annotations

import api.routing.router as routing_router
from api.routing.router import HybridRouter, ProviderStats, RoutingRegistry


def test_provider_stats_tracks_favorable_cost_signal():
    stats = ProviderStats(provider_id="openai")

    stats.update_cost(0.10)
    assert stats.last_cost_per_request == 0.10
    assert stats.ewma_cost_per_request == 0.10
    assert stats.is_cost_favorable is False

    stats.update_cost(0.05)

    assert stats.last_cost_per_request == 0.05
    assert stats.ewma_cost_per_request > stats.last_cost_per_request
    assert stats.is_cost_favorable is True


def test_routing_registry_snapshot_exposes_cost_signal():
    registry = RoutingRegistry()

    registry.record_success("openai", latency_ms=100.0, cost_usd=0.10)
    registry.record_success("openai", latency_ms=100.0, cost_usd=0.05)

    snapshot = registry.snapshot()["openai"]
    assert snapshot["ewma_cost_per_request"] > 0
    assert snapshot["last_cost_per_request"] == 0.05
    assert snapshot["is_cost_favorable"] is True
    assert snapshot["total_cost_usd"] == 0.15


def test_hybrid_router_discount_records_cost_favorable_breakdown(monkeypatch):
    registry = RoutingRegistry()
    steady = registry.get("steady")
    steady.ewma_latency_ms = 100.0
    steady.success_count = 10
    steady.update_cost(0.10)
    steady.update_cost(0.10)

    discounted = registry.get("discounted")
    discounted.ewma_latency_ms = 100.0
    discounted.success_count = 10
    discounted.update_cost(0.10)
    discounted.update_cost(0.05)

    monkeypatch.setattr(routing_router, "registry", registry)

    ranked = HybridRouter(cost_weight=0.50).rank(
        ["steady", "discounted"],
        {"steady": (0.10, 0.0), "discounted": (0.10, 0.0)},
        request_id="cost-signal",
    )

    assert ranked == ["discounted", "steady"]
    decision = registry.get_audit_trail(limit=1)[0]
    discounted_breakdown = decision["score_breakdown"]["discounted"]
    steady_breakdown = decision["score_breakdown"]["steady"]
    assert discounted_breakdown["cost_favorable"] is True
    assert discounted_breakdown["effective_cost"] == 0.75
    assert steady_breakdown["cost_favorable"] is False
    assert steady_breakdown["effective_cost"] == 1.0
