"""Cost Routing tests for ProviderDispatcher routing."""

from api.routing.router import CostRouter

from .conftest import _clean_env, _make_dispatcher


class TestCostBasedRouting:
    """Tests for ``CostRouter`` and ``pid='cheapest'``."""

    def test_cost_router_sorts_by_combined_cost(self):
        router = CostRouter()
        candidates = ["expensive", "cheap", "mid"]
        costs = {
            "expensive": (10.0, 30.0),
            "cheap": (0.5, 1.5),
            "mid": (2.0, 6.0),
        }
        ranked = router.rank(candidates, costs)
        assert ranked == ["cheap", "mid", "expensive"]

    def test_cost_router_zero_cost_ranks_first(self):
        router = CostRouter()
        ranked = router.rank(
            ["paid", "free"],
            {"paid": (1.0, 1.0), "free": (0.0, 0.0)},
        )
        assert ranked[0] == "free"

    def test_cost_router_empty_candidates_returns_empty(self):
        router = CostRouter()
        assert router.rank([], {}) == []

    def test_cost_router_single_candidate(self):
        router = CostRouter()
        assert router.rank(["solo"], {"solo": (1.0, 1.0)}) == ["solo"]

    def test_cost_router_missing_cost_defaults_to_zero(self):
        router = CostRouter()
        ranked = router.rank(
            ["a", "b"],
            {"a": (1.0, 1.0)},  # b has no entry → defaults to (0.0, 0.0)
        )
        assert ranked[0] == "b"  # b is "cheaper" with default (0,0)

    def test_cheapest_dispatch_via_candidate_order(self):
        providers = {
            "premium": {"cost_input_per_1k": 10.0, "cost_output_per_1k": 10.0},
            "budget": {"cost_input_per_1k": 0.1, "cost_output_per_1k": 0.1},
        }
        d = _make_dispatcher(providers)
        order = d._candidate_order("cheapest")
        assert order[0] == "budget"
        _clean_env(providers)

    def test_cost_equal_providers_stable(self):
        """Equal costs preserve a deterministic (input-preserving) order."""
        router = CostRouter()
        ranked = router.rank(
            ["alpha", "beta"],
            {"alpha": (1.0, 1.0), "beta": (1.0, 1.0)},
        )
        # Python's sort is stable; original order is alpha, beta
        assert ranked == ["alpha", "beta"]
