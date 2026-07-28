"""Hybrid Scoring tests for ProviderDispatcher routing."""

from api.routing.router import HybridRouter, RoutingRegistry


class TestHybridScoring:
    """Tests for ``HybridRouter`` scoring — combined latency, cost, reliability."""

    def _router_and_registry(self, cost_weight=0.35):
        reg = RoutingRegistry()
        router = HybridRouter(cost_weight=cost_weight)
        return reg, router

    def test_hybrid_prefers_low_latency_low_cost(self):
        reg, router = self._router_and_registry()
        reg.get("fast_cheap").ewma_latency_ms = 100.0
        reg.get("fast_cheap").success_count = 10
        reg.get("slow_expensive").ewma_latency_ms = 5000.0
        reg.get("slow_expensive").success_count = 10

        import api.routing.router as mod

        original = mod.registry
        mod.registry = reg
        try:
            costs = {"fast_cheap": (0.5, 0.5), "slow_expensive": (10.0, 10.0)}
            ranked = router.rank(["slow_expensive", "fast_cheap"], costs)
            assert ranked[0] == "fast_cheap"
        finally:
            mod.registry = original

    def test_hybrid_penalizes_unreliable_provider(self):
        """A provider with 50% success rate ranks lower despite good latency+cost."""
        reg, router = self._router_and_registry()
        reg.get("reliable").ewma_latency_ms = 200.0
        reg.get("reliable").success_count = 50
        reg.get("reliable").failure_count = 0
        reg.get("unreliable").ewma_latency_ms = 100.0
        reg.get("unreliable").success_count = 5
        reg.get("unreliable").failure_count = 5  # 50% success rate

        import api.routing.router as mod

        original = mod.registry
        mod.registry = reg
        try:
            costs = {"reliable": (1.0, 1.0), "unreliable": (1.0, 1.0)}
            ranked = router.rank(["unreliable", "reliable"], costs)
            assert ranked[0] == "reliable"
        finally:
            mod.registry = original

    def test_hybrid_score_breakdown_keys(self):
        """Every candidate gets a full score breakdown in the audit trail."""
        reg = RoutingRegistry()
        router = HybridRouter(cost_weight=0.35)
        reg.get("a").ewma_latency_ms = 200.0
        reg.get("a").success_count = 10
        reg.get("b").ewma_latency_ms = 400.0
        reg.get("b").success_count = 10

        import api.routing.router as mod

        original = mod.registry
        mod.registry = reg
        try:
            costs = {"a": (1.0, 2.0), "b": (3.0, 4.0)}
            router.rank(["a", "b"], costs, request_id="test-breakdown")
            trail = reg.get_audit_trail()
            decisions = [r for r in trail if r["event"] == "decision"]
            assert len(decisions) >= 1
            for pid in ("a", "b"):
                bd = decisions[-1]["score_breakdown"][pid]
                assert "normalized_latency" in bd
                assert "normalized_cost" in bd
                assert "reliability" in bd
                assert "final_score" in bd
        finally:
            mod.registry = original

    def test_hybrid_equal_providers_stable_order(self):
        """Providers with identical latency+cost+reliability preserve input order."""
        reg, router = self._router_and_registry()
        reg.get("alpha").ewma_latency_ms = 300.0
        reg.get("alpha").success_count = 10
        reg.get("beta").ewma_latency_ms = 300.0
        reg.get("beta").success_count = 10

        import api.routing.router as mod

        original = mod.registry
        mod.registry = reg
        try:
            costs = {"alpha": (1.0, 1.0), "beta": (1.0, 1.0)}
            ranked = router.rank(["alpha", "beta"], costs)
            assert ranked == ["alpha", "beta"]
        finally:
            mod.registry = original

    def test_hybrid_empty_candidates_returns_empty(self):
        router = HybridRouter(cost_weight=0.50)
        assert router.rank([], {}) == []

    def test_hybrid_single_candidate(self):
        reg, router = self._router_and_registry()
        reg.get("solo").ewma_latency_ms = 500.0
        reg.get("solo").success_count = 10

        import api.routing.router as mod

        original = mod.registry
        mod.registry = reg
        try:
            assert router.rank(["solo"], {"solo": (1.0, 1.0)}) == ["solo"]
        finally:
            mod.registry = original

    def test_hybrid_router_cost_weight_boundaries(self):
        router = HybridRouter(cost_weight=1.5)
        assert router.cost_weight == 1.0

        router = HybridRouter(cost_weight=-0.5)
        assert router.cost_weight == 0.0

        router = HybridRouter(cost_weight=0.5)
        assert router.cost_weight == 0.5

    def test_hybrid_rank_logs_decision(self):
        """HybridRouter.rank() writes a decision record."""
        reg = RoutingRegistry()
        router = HybridRouter(cost_weight=0.50)
        reg.get("a").ewma_latency_ms = 100.0
        reg.get("a").success_count = 10
        reg.get("b").ewma_latency_ms = 200.0
        reg.get("b").success_count = 10

        import api.routing.router as mod

        original = mod.registry
        mod.registry = reg
        try:
            router.rank(["a", "b"], {"a": (0.1, 0.1), "b": (0.2, 0.2)}, request_id="r1")
            trail = reg.get_audit_trail()
            decisions = [r for r in trail if r["event"] == "decision"]
            assert len(decisions) >= 1
        finally:
            mod.registry = original
