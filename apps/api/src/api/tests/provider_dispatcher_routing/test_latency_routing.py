"""Latency Routing tests for ProviderDispatcher routing."""

import pytest

from api.routing.registry_store import RoutingRegistryStore
from api.routing.router import LatencyRouter
from api.routing.router_registry import RoutingRegistry


class TestLatencyBasedRouting:
    """Tests for ``LatencyRouter`` and registry EWMA tracking."""

    def test_latency_router_prefers_low_ewma(self):
        reg = RoutingRegistry()
        router = LatencyRouter()
        reg.get("fast").ewma_latency_ms = 50.0
        reg.get("slow").ewma_latency_ms = 5000.0
        reg.get("fast").success_count = 10
        reg.get("slow").success_count = 10

        import api.routing.router as mod

        original = mod.registry
        mod.registry = reg
        try:
            ranked = router.rank(["slow", "fast"], {})
            assert ranked == ["fast", "slow"]
        finally:
            mod.registry = original

    def test_latency_router_accounts_for_reliability(self):
        """Low success_rate inflates the effective score, lowering rank."""
        reg = RoutingRegistry()
        router = LatencyRouter()
        # fast_a has low latency but poor reliability (50%)
        # score = 150 / max(0.5, 0.01) = 150 / 0.5 = 300
        reg.get("fast_a").ewma_latency_ms = 150.0
        reg.get("fast_a").success_count = 5
        reg.get("fast_a").failure_count = 5
        # fast_b has slightly higher latency but perfect reliability
        # score = 200 / max(1.0, 0.01) = 200 / 1.0 = 200
        reg.get("fast_b").ewma_latency_ms = 200.0
        reg.get("fast_b").success_count = 10
        reg.get("fast_b").failure_count = 0

        import api.routing.router as mod

        original = mod.registry
        mod.registry = reg
        try:
            ranked = router.rank(["fast_a", "fast_b"], {})
            # fast_b has lower score (better) despite higher raw latency
            assert ranked == ["fast_b", "fast_a"]
        finally:
            mod.registry = original

    def test_routing_registry_ewma_update(self):
        reg = RoutingRegistry()
        stats = reg.get("p1")
        assert stats.ewma_latency_ms == 5000.0  # default

        reg.record_success("p1", latency_ms=100.0)
        # ewma = 0.2 * 100 + 0.8 * 5000 = 4020
        assert stats.ewma_latency_ms == pytest.approx(4020.0, rel=1e-3)

        reg.record_success("p1", latency_ms=50.0)
        # ewma = 0.2 * 50 + 0.8 * 4020 = 3226
        assert stats.ewma_latency_ms == pytest.approx(3226.0, rel=1e-3)

    def test_routing_registry_success_rate_zero_total(self):
        reg = RoutingRegistry()
        stats = reg.get("p1")
        assert stats.success_rate == 1.0

    def test_routing_registry_success_rate_calculation(self):
        reg = RoutingRegistry()
        stats = reg.get("p1")
        stats.success_count = 7
        stats.failure_count = 3
        assert stats.success_rate == 0.7

    def test_routing_registry_record_failure_increments(self):
        reg = RoutingRegistry()
        reg.record_failure("p1")
        reg.record_failure("p1")
        assert reg.get("p1").failure_count == 2

    def test_routing_registry_persists_and_reloads_stats(self, tmp_path):
        store_path = tmp_path / "routing.db"
        reg = RoutingRegistry(store=RoutingRegistryStore(str(store_path)))

        reg.record_success("p1", latency_ms=100.0, cost_usd=0.25)
        reg.record_failure("p1")
        reg.flush()

        restored = RoutingRegistry(store=RoutingRegistryStore(str(store_path)))
        stats = restored.get("p1")
        assert stats.success_count == 1
        assert stats.failure_count == 1
        assert stats.total_cost_usd == pytest.approx(0.25)
        assert stats.ewma_latency_ms != 5000.0

    def test_routing_registry_missing_store_uses_default_latency(self, tmp_path):
        reg = RoutingRegistry(store=RoutingRegistryStore(str(tmp_path / "missing.db")))

        assert reg.get("p1").ewma_latency_ms == 5000.0

    def test_routing_registry_corrupt_store_falls_back_to_empty(self, tmp_path):
        store_path = tmp_path / "corrupt.db"
        store_path.write_text("not sqlite", encoding="utf-8")
        store = RoutingRegistryStore(str(store_path))
        reg = RoutingRegistry(store=store)

        assert reg.get("p1").ewma_latency_ms == 5000.0
        assert store.last_error

    def test_latency_router_empty_candidates(self):
        router = LatencyRouter()
        assert router.rank([], {}) == []

    def test_latency_router_single_candidate(self):
        reg = RoutingRegistry()
        router = LatencyRouter()
        reg.get("solo").ewma_latency_ms = 100.0
        reg.get("solo").success_count = 5

        import api.routing.router as mod

        original = mod.registry
        mod.registry = reg
        try:
            assert router.rank(["solo"], {}) == ["solo"]
        finally:
            mod.registry = original
