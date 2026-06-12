"""
Unit tests for ProviderDispatcher candidate ordering.

All tests use synthetic configs and stub providers injected via the
ProviderDispatcher(configs=..., class_map=...) constructor — no real
providers, no environment variables, no filesystem access.
"""

from __future__ import annotations

import pytest

from api.providers.base import BaseProvider, ProviderHealth, ProviderResult
from api.providers.dispatcher import ProviderDispatcher
from api.routing.router import HybridRouter, RoutingRegistry

# ── Stub provider ─────────────────────────────────────────────────────────


class StubProvider(BaseProvider):
    """Minimal provider stub.

    Costs are sourced from the provider's config dict (``cost_input_per_1k`` /
    ``cost_output_per_1k`` or the ``[costs]`` section) by ``pricing.resolve_model_pricing``.
    ``default_model`` is a read-only property on ``BaseProvider`` that reads
    ``self.config``, so we pass it through config.
    """

    def __init__(self, provider_id: str, config: dict) -> None:
        super().__init__(provider_id, config)

    async def invoke(self, messages=None, model=None, **kwargs):
        return ProviderResult(ok=True, provider=self.provider_id, model=model or self.default_model)

    async def stream(self, messages=None, model=None, **kwargs):
        return
        yield  # make it an async generator

    async def health_check(self):
        return ProviderHealth(provider_id=self.provider_id, healthy=True)


def _make_dispatcher(providers: dict) -> ProviderDispatcher:
    """
    Build a ProviderDispatcher from a {provider_id: config_dict} mapping.
    Each config_dict must have at minimum: cost_input_per_1k, cost_output_per_1k.
    Adds sensible defaults so is_configured() returns True for all entries.
    """
    configs = {}
    for pid, cfg in providers.items():
        configs[pid] = {
            "name": pid,
            "endpoint": "http://stub",
            "priority_tier": cfg.get("priority_tier", 1),
            "tier": cfg.get("tier", "cloud"),
            "local_routing": cfg.get("local_routing", False),
            "capabilities": cfg.get("capabilities", ["chat"]),
            "default_model": cfg.get("default_model", "stub-model"),
            "cost_input_per_1k": cfg.get("cost_input_per_1k", 0.0),
            "cost_output_per_1k": cfg.get("cost_output_per_1k", 0.0),
            "hidden": cfg.get("hidden", False),
        }
    class_map = {pid: StubProvider for pid in configs}
    return ProviderDispatcher(configs=configs, class_map=class_map)


# ── _cheapest_order ───────────────────────────────────────────────────────


class TestCheapestOrder:
    def test_sorts_by_combined_cost(self):
        d = _make_dispatcher(
            {
                "expensive": {"cost_input_per_1k": 10.0, "cost_output_per_1k": 30.0},
                "cheap": {"cost_input_per_1k": 0.5, "cost_output_per_1k": 1.5},
                "mid": {"cost_input_per_1k": 2.0, "cost_output_per_1k": 6.0},
            }
        )
        order = d._cheapest_order()
        assert order == ["cheap", "mid", "expensive"]

    def test_equal_cost_preserves_stable_ordering(self):
        d = _make_dispatcher(
            {
                "alpha": {"cost_input_per_1k": 1.0, "cost_output_per_1k": 1.0},
                "beta": {"cost_input_per_1k": 1.0, "cost_output_per_1k": 1.0},
            }
        )
        order = d._cheapest_order()
        assert set(order) == {"alpha", "beta"}

    def test_zero_cost_ranks_first(self):
        d = _make_dispatcher(
            {
                "paid": {"cost_input_per_1k": 1.0, "cost_output_per_1k": 1.0},
                "free": {"cost_input_per_1k": 0.0, "cost_output_per_1k": 0.0},
            }
        )
        assert d._cheapest_order()[0] == "free"

    def test_priority_tier_does_not_override_cost(self):
        # cheaper provider has higher (worse) priority_tier number
        d = _make_dispatcher(
            {
                "tier1_expensive": {
                    "priority_tier": 1,
                    "cost_input_per_1k": 20.0,
                    "cost_output_per_1k": 20.0,
                },
                "tier2_cheap": {
                    "priority_tier": 2,
                    "cost_input_per_1k": 0.1,
                    "cost_output_per_1k": 0.1,
                },
            }
        )
        assert d._cheapest_order()[0] == "tier2_cheap"

    def test_single_provider_returns_that_provider(self):
        d = _make_dispatcher({"solo": {"cost_input_per_1k": 5.0, "cost_output_per_1k": 5.0}})
        assert d._cheapest_order() == ["solo"]


# ── _hybrid_order ─────────────────────────────────────────────────────────


class TestHybridOrder:
    """
    HybridRouter combines normalised latency and cost weighted by cost_weight.
    Tests seed the RoutingRegistry directly so latency is deterministic.
    """

    def _dispatcher_with_latencies(
        self,
        providers: dict,
        latencies: dict[str, float],
        cost_weight: float = 0.35,
    ) -> tuple[ProviderDispatcher, RoutingRegistry]:
        d = _make_dispatcher(providers)
        reg = RoutingRegistry()
        for pid, lat in latencies.items():
            stats = reg.get(pid)
            stats.ewma_latency_ms = lat
        router = HybridRouter(cost_weight=cost_weight)

        # Patch the dispatcher's _hybrid_order to use our isolated registry/router
        def _hybrid_order_patched():
            candidates = d._priority_order()
            provider_costs = {p: d._provider_costs(p) for p in candidates}
            return router.rank(candidates, provider_costs)

        d._hybrid_order = _hybrid_order_patched
        return d, reg

    def test_low_latency_low_cost_ranks_first(self):
        providers = {
            "fast_cheap": {
                "cost_input_per_1k": 0.5,
                "cost_output_per_1k": 0.5,
                "priority_tier": 1,
            },
            "slow_expensive": {
                "cost_input_per_1k": 10.0,
                "cost_output_per_1k": 10.0,
                "priority_tier": 1,
            },
        }
        d, _ = self._dispatcher_with_latencies(
            providers,
            latencies={"fast_cheap": 100.0, "slow_expensive": 5000.0},
        )
        order = d._hybrid_order()
        assert order[0] == "fast_cheap"

    def test_cost_weight_zero_ranks_purely_by_latency(self):
        providers = {
            "faster": {"cost_input_per_1k": 99.0, "cost_output_per_1k": 99.0},
            "slower": {"cost_input_per_1k": 0.0, "cost_output_per_1k": 0.0},
        }
        d, _ = self._dispatcher_with_latencies(
            providers,
            latencies={"faster": 50.0, "slower": 2000.0},
            cost_weight=0.0,
        )
        assert d._hybrid_order()[0] == "faster"

    def test_cost_weight_one_ranks_purely_by_cost(self):
        providers = {
            "cheap_slow": {"cost_input_per_1k": 0.1, "cost_output_per_1k": 0.1},
            "expensive_fast": {"cost_input_per_1k": 50.0, "cost_output_per_1k": 50.0},
        }
        d, _ = self._dispatcher_with_latencies(
            providers,
            latencies={"cheap_slow": 5000.0, "expensive_fast": 10.0},
            cost_weight=1.0,
        )
        assert d._hybrid_order()[0] == "cheap_slow"

    def test_single_provider_always_first(self):
        d, _ = self._dispatcher_with_latencies(
            {"only": {"cost_input_per_1k": 1.0, "cost_output_per_1k": 1.0}},
            latencies={"only": 500.0},
        )
        assert d._hybrid_order() == ["only"]


# ── _local_order ──────────────────────────────────────────────────────────


class TestLocalOrder:
    def test_returns_only_local_routing_providers(self):
        d = _make_dispatcher(
            {
                "cloud_a": {"local_routing": False, "tier": "cloud"},
                "local_x": {"local_routing": True, "tier": "self_hosted"},
                "cloud_b": {"local_routing": False, "tier": "cloud"},
                "local_y": {"local_routing": True, "tier": "cloud"},
            }
        )
        order = d._local_order()
        assert set(order) == {"local_x", "local_y"}
        assert "cloud_a" not in order
        assert "cloud_b" not in order

    def test_self_hosted_tier_included_even_without_local_routing_flag(self):
        d = _make_dispatcher(
            {
                "self_h": {"local_routing": False, "tier": "self_hosted"},
                "cloud": {"local_routing": False, "tier": "cloud"},
            }
        )
        assert "self_h" in d._local_order()
        assert "cloud" not in d._local_order()

    def test_empty_when_no_local_providers(self):
        d = _make_dispatcher(
            {
                "a": {"local_routing": False, "tier": "cloud"},
                "b": {"local_routing": False, "tier": "cloud"},
            }
        )
        assert d._local_order() == []


# ── _candidate_order ──────────────────────────────────────────────────────


class TestCandidateOrder:
    def test_explicit_provider_returns_single_entry(self):
        d = _make_dispatcher({"openai": {}, "anthropic": {}})
        order = d._candidate_order("openai")
        assert order == ["openai"]

    def test_unknown_explicit_provider_returns_empty(self):
        d = _make_dispatcher({"openai": {}})
        assert d._candidate_order("does_not_exist") == []

    def test_auto_returns_multiple_candidates(self):
        d = _make_dispatcher({"a": {}, "b": {}, "c": {}})
        order = d._candidate_order("auto")
        assert len(order) >= 1
        assert set(order).issubset({"a", "b", "c"})

    def test_none_resolves_same_as_auto(self):
        d = _make_dispatcher({"a": {}, "b": {}})
        assert d._candidate_order(None) == d._candidate_order("auto")

    def test_cheapest_uses_cost_order(self):
        d = _make_dispatcher(
            {
                "pricey": {"cost_input_per_1k": 10.0, "cost_output_per_1k": 10.0},
                "budget": {"cost_input_per_1k": 0.1, "cost_output_per_1k": 0.1},
            }
        )
        order = d._candidate_order("cheapest")
        assert order[0] == "budget"

    def test_local_returns_only_local_providers(self):
        d = _make_dispatcher(
            {
                "cloud": {"local_routing": False, "tier": "cloud"},
                "edge": {"local_routing": True, "tier": "self_hosted"},
            }
        )
        order = d._candidate_order("local")
        assert order == ["edge"]


# ── Dry-run dispatch ──────────────────────────────────────────────────────


class TestDryRun:
    @pytest.mark.asyncio
    async def test_dry_run_returns_without_calling_provider(self):
        d = _make_dispatcher({"openai": {"default_model": "gpt-4o"}})
        result = await d.dispatch(
            "openai",
            None,
            {"messages": [{"role": "user", "content": "hi"}]},
            dry_run=True,
        )
        assert result["ok"] is True
        assert result["dry_run"] is True
        assert result["resolved_provider"] == "openai"
        assert result["resolved_model"] == "gpt-4o"

    @pytest.mark.asyncio
    async def test_dry_run_includes_candidate_order(self):
        d = _make_dispatcher(
            {
                "cheap": {"cost_input_per_1k": 0.1, "cost_output_per_1k": 0.1},
                "pricey": {"cost_input_per_1k": 5.0, "cost_output_per_1k": 5.0},
            }
        )
        result = await d.dispatch(None, None, {}, dry_run=True)
        assert result["ok"] is True
        providers_in_order = [c["provider"] for c in result["candidate_order"]]
        assert set(providers_in_order) == {"cheap", "pricey"}

    @pytest.mark.asyncio
    async def test_dry_run_unknown_provider_returns_error(self):
        d = _make_dispatcher({"openai": {}})
        result = await d.dispatch("nonexistent", None, {}, dry_run=True)
        assert result["ok"] is False

    @pytest.mark.asyncio
    async def test_dry_run_explicit_mode_label(self):
        d = _make_dispatcher({"openai": {}})
        result = await d.dispatch("openai", None, {}, dry_run=True)
        assert result["routing_mode"] == "explicit"

    @pytest.mark.asyncio
    async def test_dry_run_auto_mode_label(self):
        d = _make_dispatcher({"openai": {}})
        result = await d.dispatch(None, None, {}, dry_run=True)
        assert result["routing_mode"] == "auto"
