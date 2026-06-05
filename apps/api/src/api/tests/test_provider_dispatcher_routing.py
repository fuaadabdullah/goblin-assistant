"""
Comprehensive tests for ProviderDispatcher selection, failover, circuit breaker,
cost-based routing, latency-based routing, and hybrid scoring.

All tests use synthetic configs and stub providers injected via the
ProviderDispatcher(configs=..., class_map=...) constructor — no real
providers, no environment variables, no filesystem access (except where
explicitly testing env-var-based configuration).
"""

from __future__ import annotations

import asyncio
import os
import time

import pytest

from api.ops.circuit_breaker import CircuitBreaker, calculate_health_score
from api.providers.base import BaseProvider, ProviderHealth, ProviderResult
from api.providers.dispatcher import ProviderDispatcher
from api.routing.router import (
    CostRouter,
    HybridRouter,
    LatencyRouter,
    RoutingRegistry,
    RoutingRegistryStore,
)

# ── Stub provider ───────────────────────────────────────────────────────────


class _StubProvider(BaseProvider):
    """Minimal provider stub with configurable costs, model, and behavior.

    COST_* are class-level floats on BaseProvider — we set them as instance attrs
    so the dispatcher's ``_provider_costs()`` picks them up.
    """

    def __init__(self, provider_id: str, config: dict) -> None:
        super().__init__(provider_id, config)
        self.COST_INPUT_PER_1K = float(config.get("cost_input_per_1k", 0.0))
        self.COST_OUTPUT_PER_1K = float(config.get("cost_output_per_1k", 0.0))
        # force_fallback requires a sequence of fallback PIDs — stored in config
        self._fake_fail: bool = False
        self._fake_fail_error: str = "stub failure"
        self._fake_fail_category: str = "server-error"
        self._invoke_hook = None

    async def invoke(self, messages=None, model=None, **kwargs):
        if self._fake_fail:
            return ProviderResult(
                ok=False,
                provider=self.provider_id,
                model=model or self.default_model,
                error=self._fake_fail_error,
                error_category=self._fake_fail_category,
                latency_ms=1.0,
            )
        if self._invoke_hook:
            return await self._invoke_hook(messages, model, **kwargs)
        return ProviderResult(
            ok=True,
            text=f"ok from {self.provider_id}",
            provider=self.provider_id,
            model=model or self.default_model,
            usage={"input_tokens": 1, "output_tokens": 1},
            cost_usd=(
                self.COST_INPUT_PER_1K / 1000 * 1
                + self.COST_OUTPUT_PER_1K / 1000 * 1
            ),
            latency_ms=2.0,
        )

    async def stream(self, messages=None, model=None, **kwargs):
        return
        yield  # make it an async generator (unreachable, but syntactically required)

    async def health_check(self):
        return ProviderHealth(provider_id=self.provider_id, healthy=True)


# ── Dispatcher factory helpers ──────────────────────────────────────────────


def _make_dispatcher(providers: dict) -> ProviderDispatcher:
    """
    Build a ProviderDispatcher from a {provider_id: config_dict} mapping.

    Each config_dict may contain: cost_input_per_1k, cost_output_per_1k,
    priority_tier, tier, local_routing, capabilities, default_model, hidden.
    Sensible defaults are applied so ``is_configured()`` returns True for all
    entries (an api_key_env is set pointing to a stub env var that is set).
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
            "api_key_env": f"_TEST_KEY_{pid.upper()}",
        }
    # Set env vars so is_configured() returns True
    for pid in configs:
        os.environ[f"_TEST_KEY_{pid.upper()}"] = "stub-key"
    class_map = {pid: _StubProvider for pid in configs}
    return ProviderDispatcher(configs=configs, class_map=class_map)


def _clean_env(providers: dict) -> None:
    """Remove env vars set by _make_dispatcher."""
    for pid in providers:
        os.environ.pop(f"_TEST_KEY_{pid.upper()}", None)


# =============================================================================
# 1. Provider Selection
# =============================================================================


class TestProviderSelection:
    """Tests for ``top_providers_for()`` and ``is_configured()``."""

    def setup_method(self):
        self.providers = {
            "openai": {"capabilities": ["chat", "code"], "priority_tier": 1},
            "anthropic": {"capabilities": ["chat"], "priority_tier": 2},
            "gemini": {"capabilities": ["chat", "vision"], "priority_tier": 3},
            "cohere": {"capabilities": ["embed"], "priority_tier": 4},
        }
        self.d = _make_dispatcher(self.providers)

    def teardown_method(self):
        _clean_env(self.providers)

    def test_top_providers_for_filters_by_capability(self):
        result = self.d.top_providers_for("chat")
        assert "cohere" not in result
        assert "openai" in result
        assert "anthropic" in result

    def test_top_providers_for_prefer_local_ranks_local_first(self):
        providers = {
            "cloud_a": {"capabilities": ["chat"], "local_routing": False, "tier": "cloud"},
            "edge_b": {"capabilities": ["chat"], "local_routing": True, "tier": "self_hosted"},
        }
        d = _make_dispatcher(providers)
        result = d.top_providers_for("chat", prefer_local=True)
        assert result[0] == "edge_b"
        _clean_env(providers)

    def test_top_providers_for_prefer_cost_ranks_cheapest_first(self):
        providers = {
            "expensive": {
                "capabilities": ["chat"],
                "cost_input_per_1k": 10.0,
                "cost_output_per_1k": 10.0,
            },
            "cheap": {
                "capabilities": ["chat"],
                "cost_input_per_1k": 0.1,
                "cost_output_per_1k": 0.1,
            },
        }
        d = _make_dispatcher(providers)
        result = d.top_providers_for("chat", prefer_cost=True)
        assert result[0] == "cheap"
        _clean_env(providers)

    def test_top_providers_for_respects_limit(self):
        result = self.d.top_providers_for("chat", limit=2)
        assert len(result) <= 2

    def test_top_providers_for_capability_case_insensitive(self):
        result = self.d.top_providers_for("CHAT")
        assert "openai" in result

    def test_top_providers_for_missing_capability_returns_empty(self):
        result = self.d.top_providers_for("audio")
        assert result == []

    def test_is_configured_true_when_api_key_present(self, monkeypatch):
        providers = {"testprov": {"capabilities": ["chat"]}}
        d = _make_dispatcher(providers)
        assert d.is_configured("testprov") is True
        _clean_env(providers)

    def test_is_configured_false_when_api_key_missing(self, monkeypatch):
        configs = {
            "missingkey": {
                "name": "missingkey",
                "endpoint": "http://stub",
                "capabilities": ["chat"],
                "api_key_env": "SOME_UNSET_KEY",
            }
        }
        class_map = {"missingkey": _StubProvider}
        d = ProviderDispatcher(configs=configs, class_map=class_map)
        assert d.is_configured("missingkey") is False

    def test_provider_ids_matches_list_providers(self):
        ids = self.d.provider_ids()
        listed = [p["id"] for p in self.d.list_providers()]
        assert ids == listed


# =============================================================================
# 2. Provider Failover
# =============================================================================


class TestProviderFailover:
    """Tests for dispatch failover across multiple candidates."""

    def setup_method(self):
        self.providers = {
            "primary": {"capabilities": ["chat"], "priority_tier": 1},
            "secondary": {"capabilities": ["chat"], "priority_tier": 2},
            "tertiary": {"capabilities": ["chat"], "priority_tier": 3},
        }
        self.d = _make_dispatcher(self.providers)

    def teardown_method(self):
        _clean_env(self.providers)

    @pytest.mark.asyncio
    async def test_failover_when_primary_returns_failure(self):
        """When the primary provider returns ok=False, dispatch falls through."""
        primary = self.d.get_provider("primary")
        primary._fake_fail = True

        result = await self.d.dispatch(
            pid="auto",
            model="stub-model",
            payload={"messages": [{"role": "user", "content": "hello"}]},
        )

        assert result["ok"] is True
        assert result["provider"] == "secondary"

    @pytest.mark.asyncio
    async def test_failover_when_primary_raises_exception(self):
        """Exception thrown by a provider invoke → next provider is tried."""
        primary = self.d.get_provider("primary")

        async def boom(*args, **kwargs):
            raise RuntimeError("primary exploded")

        primary._invoke_hook = boom

        result = await self.d.dispatch(
            pid="auto",
            model="stub-model",
            payload={"messages": [{"role": "user", "content": "hello"}]},
        )

        assert result["ok"] is True
        assert result["provider"] == "secondary"

    @pytest.mark.asyncio
    async def test_failover_on_timeout_tries_next_provider(self):
        """asyncio.TimeoutError from a provider → next candidate is tried."""
        primary = self.d.get_provider("primary")

        async def hang(*args, **kwargs):
            await asyncio.sleep(600)

        primary._invoke_hook = hang

        result = await self.d.dispatch(
            pid="auto",
            model="stub-model",
            payload={"messages": [{"role": "user", "content": "hello"}]},
            timeout_ms=5,
        )

        assert result["ok"] is True
        assert result["provider"] == "secondary"

    @pytest.mark.asyncio
    async def test_failover_chain_exhaustion_returns_error(self):
        """All candidates fail → dispatch returns ok=False with last error."""
        for pid in ("primary", "secondary", "tertiary"):
            p = self.d.get_provider(pid)
            p._fake_fail = True

        result = await self.d.dispatch(
            pid="auto",
            model="stub-model",
            payload={"messages": [{"role": "user", "content": "hello"}]},
        )

        assert result["ok"] is False
        assert result["provider"] == "none"
        assert result["error"] == "stub failure"

    @pytest.mark.asyncio
    async def test_explicit_provider_no_fallback_does_not_fallback(self):
        """Explicit provider without force_fallback stays single even on failure."""
        primary = self.d.get_provider("primary")
        secondary = self.d.get_provider("secondary")
        primary._fake_fail = True

        secondary._invoke_hook = lambda *a, **kw: (
            None
            if False
            else (_ for _ in ()).throw(AssertionError("should not be called"))
        )

        result = await self.d.dispatch(
            pid="primary",
            model="stub-model",
            payload={"messages": [{"role": "user", "content": "hello"}]},
        )

        assert result["ok"] is False
        assert result["provider"] == "none"

    @pytest.mark.asyncio
    async def test_dispatch_unknown_provider_returns_error(self):
        """Unknown provider pid → ok=False with unknown-provider error."""
        result = await self.d.dispatch(
            pid="nonexistent_provider",
            model="stub-model",
            payload={"messages": [{"role": "user", "content": "hello"}]},
        )

        assert result["ok"] is False
        assert "unknown-provider" in result["error"]

    @pytest.mark.asyncio
    async def test_dispatch_with_prompt_not_messages(self):
        """Payload with 'prompt' key works (backward compat path)."""
        result = await self.d.dispatch(
            pid="primary",
            model="stub-model",
            payload={"prompt": "hello world"},
        )

        assert result["ok"] is True
        assert result["provider"] == "primary"

    @pytest.mark.asyncio
    async def test_dispatch_records_latency_in_registry(self):
        """After a successful dispatch, registry EWMA latency is updated."""
        from api.routing.router import registry

        before = registry.get("primary").ewma_latency_ms

        await self.d.dispatch(
            pid="primary",
            model="stub-model",
            payload={"messages": [{"role": "user", "content": "hello"}]},
        )

        after = registry.get("primary").ewma_latency_ms
        assert after != before  # registry was updated


# =============================================================================
# 3. Circuit Breaker — BaseProvider (per-provider)
# =============================================================================


class TestBaseProviderCircuitBreaker:
    """Tests for the built-in circuit breaker on ``BaseProvider``."""

    def test_circuit_breaker_soft_opens_after_two_transient_failures(self):
        provider = _StubProvider("stub", {"default_model": "stub-model"})
        assert provider.is_available() is True

        provider.record_failure("timeout one", category="timeout")
        assert provider.circuit_state == "closed"

        provider.record_failure("timeout two", category="timeout")
        assert provider.circuit_state == "soft_open"
        assert provider.is_available() is True
        assert provider.should_attempt(canary=False) is False
        assert provider.should_attempt(canary=True) is False

    def test_circuit_breaker_backoff_duration(self):
        provider = _StubProvider("stub", {"default_model": "stub-model"})
        provider.record_failure("server error 1", backoff_seconds=30.0, category="server-error")
        provider.record_failure("server error 2", backoff_seconds=30.0, category="server-error")
        assert provider.circuit_state == "soft_open"
        # _circuit_open_until should be ~now + 30s
        assert provider._circuit_open_until > time.time() + 25

    def test_circuit_breaker_failed_probe_rearms_soft_open_window(self, monkeypatch):
        import api.providers.base as base_module

        now = 1_000.0
        monkeypatch.setattr(base_module.time, "time", lambda: now)

        provider = _StubProvider("stub", {"default_model": "stub-model"})
        provider.record_failure("timeout 1", category="timeout")
        provider.record_failure("timeout 2", category="timeout")
        assert provider.circuit_state == "soft_open"

        monkeypatch.setattr(base_module.time, "time", lambda: now + 31.0)
        assert provider.claim_soft_open_probe() is True

        provider.record_failure("timeout probe failed", category="timeout")
        assert provider.circuit_state == "soft_open"
        assert provider.soft_open_probe_available() is False
        assert provider._circuit_open_until > now + 31.0

    def test_circuit_breaker_success_resets_backoff(self):
        provider = _StubProvider("stub", {"default_model": "stub-model"})
        provider.record_failure("timeout 1", category="timeout")
        provider.record_failure("timeout 2", category="timeout")
        assert provider.circuit_state == "soft_open"

        provider.record_success()
        assert provider.is_available() is True
        assert provider.circuit_state == "closed"
        assert provider._failure_count == 0
        assert provider._circuit_open_until == 0.0

    def test_circuit_breaker_two_failures_still_available(self):
        provider = _StubProvider("stub", {"default_model": "stub-model"})
        provider.record_failure("f1")
        provider.record_failure("f2")
        assert provider.is_available() is True

    def test_circuit_breaker_record_failure_increments_count(self):
        provider = _StubProvider("stub", {"default_model": "stub-model"})
        assert provider._failure_count == 0
        provider.record_failure("err")
        assert provider._failure_count == 1
        provider.record_failure("err")
        assert provider._failure_count == 2

    def test_circuit_breaker_hard_opens_on_auth_failure(self):
        provider = _StubProvider("stub", {"default_model": "stub-model"})

        provider.record_failure("invalid api key", category="auth")

        assert provider.circuit_state == "hard_open"
        assert provider.is_available() is False
        assert provider.should_attempt(canary=True) is False

    def test_circuit_breaker_hard_opens_on_billing_failure(self):
        provider = _StubProvider("stub", {"default_model": "stub-model"})

        provider.record_failure("credit balance is too low", category="rate-limit")

        assert provider.circuit_state == "hard_open"
        assert provider.is_available() is False
        assert provider.should_attempt(canary=True) is False

    def test_dispatcher_probe_eligibility_uses_recovery_window(self, monkeypatch):
        import api.providers.base as base_module

        providers = {"alpha": {"default_model": "m1"}}
        d = _make_dispatcher(providers)
        try:
            provider = d.get_provider("alpha")

            now = 1_000.0
            monkeypatch.setattr(base_module.time, "time", lambda: now)
            provider.record_failure("timeout one", category="timeout")
            provider.record_failure("timeout two", category="timeout")

            assert d._is_canary_attempt("alpha", "m1") is False

            monkeypatch.setattr(base_module.time, "time", lambda: now + 31.0)
            assert d._is_canary_attempt("alpha", "m1") is True
        finally:
            _clean_env(providers)


# =============================================================================
# 4. Circuit Breaker — ops/CircuitBreaker (system-level)
# =============================================================================


class TestOpsCircuitBreaker:
    """Tests for the ops-domain ``CircuitBreaker``."""

    def test_closed_allows_execution(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
        assert cb.can_execute() is True
        assert cb.state == "CLOSED"

    def test_opens_after_threshold_failures(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "OPEN"
        assert cb.can_execute() is False

    def test_open_blocks_execution(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=60)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "OPEN"
        assert cb.can_execute() is False

    def test_recovery_timeout_transitions_to_half_open(self, monkeypatch):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.01)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "OPEN"
        assert cb.can_execute() is False

        # Advance time past recovery timeout
        monkeypatch.setattr(time, "time", lambda: cb.last_failure_time + 0.02)
        assert cb.can_execute() is True
        assert cb.state == "HALF_OPEN"

    def test_half_open_success_closes_circuit(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.01)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "OPEN"

        # Force into half-open by faking time
        cb.state = "HALF_OPEN"
        cb.can_execute()  # should return True for half-open

        cb.record_success()
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0

    def test_half_open_failure_reopens(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.01)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "OPEN"

        # Force into half-open
        cb.state = "HALF_OPEN"
        cb.record_failure()
        assert cb.state == "OPEN"

    def test_success_resets_from_any_state(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "OPEN"

        cb.record_success()
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0

    def test_get_status_fields(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
        status = cb.get_status()
        assert "state" in status
        assert "failure_count" in status
        assert "failure_threshold" in status
        assert "last_failure_time" in status
        assert "time_until_recovery" in status
        assert status["state"] == "CLOSED"

    def test_get_status_shows_time_until_recovery_when_open(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=30)
        cb.record_failure()
        status = cb.get_status()
        assert status["state"] == "OPEN"
        assert status["time_until_recovery"] > 0

    def test_initial_state_is_closed(self):
        cb = CircuitBreaker()
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0

    def test_failure_updates_last_failure_time(self):
        cb = CircuitBreaker()
        before = cb.last_failure_time
        cb.record_failure()
        assert cb.last_failure_time >= before


class TestCalculateHealthScore:
    """Tests for ``calculate_health_score()`` in ops circuit breaker."""

    def test_healthy_provider_scores_near_100(self):
        status = {"status": "healthy"}
        metrics = {"error_rate": 0, "avg_response_time": 100}
        cb = CircuitBreaker()
        score = calculate_health_score(status, metrics, cb)
        assert score == 100.0

    def test_open_breaker_penalizes_score(self):
        status = {"status": "healthy"}
        metrics = {"error_rate": 0, "avg_response_time": 100}
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60)
        cb.record_failure()
        score = calculate_health_score(status, metrics, cb)
        assert score <= 60.0  # 100 - 40 (OPEN)

    def test_half_open_breaker_penalizes_less(self):
        status = {"status": "healthy"}
        metrics = {"error_rate": 0, "avg_response_time": 100}
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01)
        cb.record_failure()
        cb.state = "HALF_OPEN"
        score = calculate_health_score(status, metrics, cb)
        assert score == 80.0  # 100 - 20 (HALF_OPEN)

    def test_high_error_rate_penalizes_score(self):
        status = {"status": "healthy"}
        metrics = {"error_rate": 15, "avg_response_time": 100}
        cb = CircuitBreaker()
        score = calculate_health_score(status, metrics, cb)
        assert score == 80.0  # 100 - 20 (error_rate > 10)

    def test_high_latency_penalizes_score(self):
        status = {"status": "healthy"}
        metrics = {"error_rate": 0, "avg_response_time": 6000}
        cb = CircuitBreaker()
        score = calculate_health_score(status, metrics, cb)
        assert score == 90.0  # 100 - 10 (avg_response_time > 5000)

    def test_combined_penalties_stack(self):
        status = {"status": "unhealthy"}
        metrics = {"error_rate": 6, "avg_response_time": 3000}
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60)
        cb.record_failure()
        score = calculate_health_score(status, metrics, cb)
        # 100 - 30 (unhealthy) - 40 (OPEN) - 10 (error_rate > 5) - 5 (latency > 2000)
        assert score == 15.0

    def test_score_minimum_zero(self):
        status = {"status": "unhealthy"}
        metrics = {"error_rate": 100, "avg_response_time": 10000}
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60)
        cb.record_failure()
        score = calculate_health_score(status, metrics, cb)
        assert score >= 0.0


# =============================================================================
# 5. Cost-Based Routing
# =============================================================================


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


# =============================================================================
# 6. Latency-Based Routing
# =============================================================================


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


# =============================================================================
# 7. Hybrid Scoring
# =============================================================================


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


# =============================================================================
# 8. Dispatch Integration
# =============================================================================


class TestDispatchIntegration:
    """End-to-end dispatch integration tests."""

    def setup_method(self):
        self.providers = {
            "alpha": {"capabilities": ["chat"], "priority_tier": 1},
        }
        self.d = _make_dispatcher(self.providers)

    def teardown_method(self):
        _clean_env(self.providers)

    def test_update_provider_endpoint_hot_reload(self):
        """update_provider_endpoint() changes in-memory config."""
        self.d.update_provider_endpoint("alpha", "http://new-endpoint")
        config = self.d.get_provider_config("alpha")
        assert config["endpoint"] == "http://new-endpoint"

    def test_update_provider_endpoint_clears_cache(self):
        """After endpoint update, provider list cache is invalidated."""
        self.d.list_providers()  # warm cache
        self.d.update_provider_endpoint("alpha", "http://new-endpoint")
        # Should not raise; cache is clear
        assert self.d.list_providers() is not None

    def test_update_provider_endpoint_unknown_provider(self):
        """Updating endpoint for unknown provider raises KeyError."""
        with pytest.raises(KeyError):
            self.d.update_provider_endpoint("does_not_exist", "http://x")

    def test_debug_info_returns_complete_state(self):
        info = self.d.debug_info()
        assert "routing_table" in info
        assert "registry_stats" in info
        assert "routing_min_success_rate" in info
        assert "model_aliases" in info
        assert "provider_aliases" in info
        assert "visible_provider_order" in info

    def test_debug_info_includes_provider_entry(self):
        info = self.d.debug_info()
        routing_table = info["routing_table"]
        alpha_entry = next((e for e in routing_table if e["provider_id"] == "alpha"), None)
        assert alpha_entry is not None
        assert alpha_entry["configured"] is True
        assert alpha_entry["capabilities"] == ["chat"]

    def test_list_providers_includes_configured_flag(self):
        providers = self.d.list_providers()
        assert len(providers) >= 1
        for p in providers:
            assert "id" in p
            assert "name" in p
            assert "capabilities" in p
            assert "priority_tier" in p

    def test_get_provider_config_returns_config(self):
        cfg = self.d.get_provider_config("alpha")
        assert "endpoint" in cfg
        assert "capabilities" in cfg

    def test_get_provider_config_unknown_returns_empty(self):
        cfg = self.d.get_provider_config("i_dont_exist")
        assert cfg == {}

    def test_health_all_key_structure(self):
        health = asyncio.run(self.d.health_all(include_hidden=True))
        assert "alpha" in health
        assert "healthy" in health["alpha"]
        assert "configured" in health["alpha"]
        assert "latency_ms" in health["alpha"]
        assert "error" in health["alpha"]


# =============================================================================
# 9. Edge Cases and Error Handling
# =============================================================================


class TestErrorHandling:
    """Edge cases and defensive error handling in the dispatcher."""

    def test_candidate_order_unknown_provider_returns_empty(self):
        d = _make_dispatcher({"a": {}})
        assert d._candidate_order("nonexistent") == []
        _clean_env({"a": {}})

    def test_candidate_order_none_uses_hybrid(self):
        d = _make_dispatcher({"a": {}, "b": {}})
        none_order = d._candidate_order(None)
        auto_order = d._candidate_order("auto")
        assert none_order == auto_order
        _clean_env({"a": {}, "b": {}})

    def test_dispatcher_raises_key_error_for_missing_provider(self):
        d = _make_dispatcher({"exists": {}})
        with pytest.raises(KeyError, match="Unknown provider"):
            d.get_provider("does_not_exist")
        _clean_env({"exists": {}})

    def test_dry_run_dispatch_no_side_effects(self):
        """Dry-run dispatch does not invoke any provider."""
        d = _make_dispatcher({"p1": {"default_model": "m1"}})
        p1 = d.get_provider("p1")

        async def should_not_run(*args, **kwargs):
            raise AssertionError("provider should not be called during dry_run")

        p1._invoke_hook = should_not_run

        result = asyncio.run(d.dispatch("p1", None, {}, dry_run=True))
        assert result["ok"] is True
        assert result["dry_run"] is True
        assert result["resolved_provider"] == "p1"
        _clean_env({"p1": {}})

    def test_provider_error_category_classification(self):
        """classify_provider_error maps known error strings correctly."""
        from api.providers.base import ProviderErrorCategory, classify_provider_error

        assert classify_provider_error("401") == ProviderErrorCategory.AUTH
        assert classify_provider_error("rate limit exceeded") == ProviderErrorCategory.RATE_LIMIT
        assert classify_provider_error("timed out") == ProviderErrorCategory.TIMEOUT
        assert classify_provider_error("model not found") == ProviderErrorCategory.MODEL_ERROR
        assert classify_provider_error("502 Bad Gateway") == ProviderErrorCategory.SERVER_ERROR
        assert classify_provider_error("Connection refused") == ProviderErrorCategory.CONNECTION
        assert classify_provider_error("something else") == ProviderErrorCategory.UNKNOWN
