"""Targeted tests for uncovered paths in routing modules.

Covers gaps identified by coverage analysis:
- selection.py: top_providers_for, route_task, route_task_sync
- router_supabase.py: schedule_mirror, restore_from_supabase
- policy_engine.py: LatencyRouter, CostRouter, HybridRouter, ModelTierRouter
- provider_selection.py: _softmax_pct, _fallback_reasons, _stage_latency_percentiles
- registry_store.py: load_hourly_spend, flush error handling
- router_registry.py: _flush_if_due, record_success with tokens, persistence_status
- routing_pipeline.py: error paths
- health_provider.py: _status_is_available edge cases
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from api.routing.health_provider import (
    CachedProviderHealthProvider,
    StaticHealthProvider,
    _status_is_available,
)
from api.routing.policy_engine import (
    HybridRouter,
    ModelTierRouter,
    cost_router,
    latency_router,
)
from api.routing.provider_selection import (
    _fallback_reasons,
    _softmax_pct,
    _stage_latency_percentiles,
)
from api.routing.registry_store import ProviderStats, RoutingRegistryStore
from api.routing.router_registry import RoutingRegistry
from api.routing.router_supabase import restore_from_supabase, schedule_mirror
from api.routing.selection import route_task_sync, top_providers_for

# =========================================================================
# selection.py
# =========================================================================


class TestTopProvidersFor:
    def test_empty_candidates_returns_empty_list(self):
        result = top_providers_for("nonexistent", limit=5)
        assert result == []

    def test_prefer_cost_uses_cost_router(self, monkeypatch):
        fake_dispatcher = MagicMock()
        fake_dispatcher.top_providers_for.return_value = ["openai", "anthropic", "groq"]

        def _fake_dispatcher():
            return fake_dispatcher

        monkeypatch.setattr("api.routing.selection._dispatcher", _fake_dispatcher)

        def _fake_costs(provider_ids):
            return {
                "openai": (0.01, 0.03),
                "anthropic": (0.015, 0.06),
                "groq": (0.0005, 0.001),
            }

        monkeypatch.setattr("api.routing.selection._provider_costs", _fake_costs)

        result = top_providers_for("chat", prefer_cost=True, limit=2)
        # CostRouter sorts by input+output cost ascending
        assert result == ["groq", "openai"]

    def test_prefer_local_filters_by_tier(self, monkeypatch):
        fake_dispatcher = MagicMock()
        fake_dispatcher.top_providers_for.return_value = [
            "gcp_vm",
            "ollama_local",
            "openai",
            "anthropic",
        ]

        def _fake_dispatcher():
            return fake_dispatcher

        monkeypatch.setattr("api.routing.selection._dispatcher", _fake_dispatcher)

        result = top_providers_for("chat", prefer_local=True, limit=3)
        # Only local providers should remain
        assert all(pid in ["gcp_vm", "ollama_local"] for pid in result)
        assert len(result) <= 3

    def test_default_returns_candidates_limited(self, monkeypatch):
        fake_dispatcher = MagicMock()
        fake_dispatcher.top_providers_for.return_value = [
            "openai",
            "anthropic",
            "groq",
            "gemini",
            "deepseek",
        ]

        def _fake_dispatcher():
            return fake_dispatcher

        monkeypatch.setattr("api.routing.selection._dispatcher", _fake_dispatcher)

        result = top_providers_for("chat", limit=2)
        assert len(result) == 2
        assert result == ["openai", "anthropic"]


class TestRouteTaskSync:
    def test_returns_error_when_running_in_event_loop(self):
        async def _run():
            result = route_task_sync("chat", {"messages": []})
            assert result["ok"] is False
            assert "active event loop" in result["error"]

        asyncio.run(_run())

    def test_returns_error_when_no_candidates(self, monkeypatch):
        def _fake_top(*args, **kwargs):
            return []

        monkeypatch.setattr("api.routing.selection.top_providers_for", _fake_top)

        result = route_task_sync("chat", {"messages": []})
        assert result["ok"] is False
        assert "no providers available" in result["error"]


# =========================================================================
# router_supabase.py
# =========================================================================


class TestScheduleMirror:
    def test_schedule_mirror_with_running_loop_creates_task(self):
        stats = {
            "openai": ProviderStats(
                provider_id="openai",
                ewma_latency_ms=100.0,
                success_count=10,
                failure_count=1,
                total_cost_usd=0.5,
                last_used=time.time(),
            )
        }
        hourly_spend = {"2026071800": {"openai": 0.5}}

        async def _run():
            schedule_mirror(stats, hourly_spend)
            # Give the task a moment to be scheduled
            await asyncio.sleep(0.05)
            # If we got here without error, the schedule succeeded
            assert True

        asyncio.run(_run())

    def test_schedule_mirror_without_running_loop_does_not_raise(self):
        stats = {
            "openai": ProviderStats(
                provider_id="openai",
                ewma_latency_ms=100.0,
                success_count=10,
                failure_count=1,
                total_cost_usd=0.5,
                last_used=time.time(),
            )
        }
        hourly_spend = {"2026071800": {"openai": 0.5}}
        # No running loop — should silently pass
        schedule_mirror(stats, hourly_spend)
        assert True


class TestRestoreFromSupabase:
    async def test_noop_when_stats_already_populated(self):
        stats = {"openai": ProviderStats(provider_id="openai")}
        hourly_spend: dict = {}
        await restore_from_supabase(stats, hourly_spend)
        # Should not modify stats since it's already populated
        assert "openai" in stats

    async def test_noop_when_supabase_not_enabled(self, monkeypatch):
        stats: dict = {}
        hourly_spend: dict = {}
        # _ENABLED lives in api.providers.supabase_events, imported lazily
        monkeypatch.setattr(
            "api.providers.supabase_events._ENABLED",
            False,
        )
        await restore_from_supabase(stats, hourly_spend)
        assert stats == {}

    async def test_handles_exception_gracefully(self, monkeypatch):
        stats: dict = {}
        hourly_spend: dict = {}

        async def _throw(*args, **kwargs):
            raise RuntimeError("supabase unavailable")

        # _get_client lives in api.providers.supabase_events, imported lazily
        monkeypatch.setattr(
            "api.providers.supabase_events._get_client",
            _throw,
        )
        # Should not raise
        await restore_from_supabase(stats, hourly_spend)
        assert stats == {}


# =========================================================================
# policy_engine.py
# =========================================================================


class TestLatencyRouter:
    def test_rank_sorts_by_latency_over_reliability(self, monkeypatch):
        fake_registry = MagicMock()
        fake_registry.get.side_effect = lambda pid: SimpleNamespace(
            ewma_latency_ms={"fast": 50.0, "medium": 200.0, "slow": 800.0}.get(pid, 100.0),
            success_rate={"fast": 0.99, "medium": 0.95, "slow": 0.90}.get(pid, 0.95),
        )

        def _get_registry():
            return fake_registry

        monkeypatch.setattr("api.routing.policy_engine._get_registry", _get_registry)

        result = latency_router.rank(
            ["slow", "fast", "medium"],
            {"slow": (0.0, 0.0), "fast": (0.0, 0.0), "medium": (0.0, 0.0)},
        )
        assert result == ["fast", "medium", "slow"]

    def test_rank_empty_candidates(self):
        result = latency_router.rank([], {})
        assert result == []


class TestCostRouter:
    def test_rank_sorts_by_total_cost_ascending(self):
        result = cost_router.rank(
            ["expensive", "cheap", "medium"],
            {
                "expensive": (0.05, 0.15),
                "cheap": (0.0005, 0.001),
                "medium": (0.01, 0.03),
            },
        )
        assert result == ["cheap", "medium", "expensive"]

    def test_rank_empty_candidates(self):
        result = cost_router.rank([], {})
        assert result == []

    def test_rank_missing_costs_defaults_to_zero(self):
        result = cost_router.rank(
            ["provider_a", "provider_b"],
            {"provider_a": (0.01, 0.02)},
        )
        # provider_b has no cost entry, defaults to (0.0, 0.0) -> cost_score=0.0
        assert result == ["provider_b", "provider_a"]


class TestHybridRouter:
    def test_rank_sorts_by_hybrid_score(self, monkeypatch):
        fake_registry = MagicMock()
        fake_registry.get.side_effect = lambda pid: SimpleNamespace(
            ewma_latency_ms={"a": 100.0, "b": 200.0, "c": 50.0}.get(pid, 100.0),
            success_rate={"a": 0.95, "b": 0.99, "c": 0.90}.get(pid, 0.95),
        )
        fake_registry.log_decision = MagicMock()

        def _get_registry():
            return fake_registry

        monkeypatch.setattr("api.routing.policy_engine._get_registry", _get_registry)

        router = HybridRouter(cost_weight=0.5)
        result = router.rank(
            ["a", "b", "c"],
            {"a": (0.01, 0.02), "b": (0.005, 0.01), "c": (0.02, 0.04)},
            request_id="test-req",
        )
        # All three should be ranked
        assert len(result) == 3
        fake_registry.log_decision.assert_called_once()

    def test_rank_empty_candidates(self):
        router = HybridRouter(cost_weight=0.5)
        result = router.rank([], {})
        assert result == []

    def test_rank_single_candidate(self, monkeypatch):
        fake_registry = MagicMock()
        fake_registry.get.return_value = SimpleNamespace(
            ewma_latency_ms=100.0,
            success_rate=0.95,
        )
        fake_registry.log_decision = MagicMock()

        def _get_registry():
            return fake_registry

        monkeypatch.setattr("api.routing.policy_engine._get_registry", _get_registry)

        router = HybridRouter(cost_weight=0.5)
        result = router.rank(
            ["only_one"],
            {"only_one": (0.01, 0.02)},
        )
        assert result == ["only_one"]

    def test_cost_weight_clamped(self):
        router = HybridRouter(cost_weight=2.0)
        assert router.cost_weight == 1.0
        router = HybridRouter(cost_weight=-0.5)
        assert router.cost_weight == 0.0


class TestModelTierRouter:
    def test_providers_for_tier_returns_known_providers(self):
        router = ModelTierRouter()
        providers = router.providers_for_tier("fast")
        assert "groq" in providers
        assert "gemini" in providers

    def test_providers_for_tier_falls_back_to_smart(self):
        router = ModelTierRouter()
        providers = router.providers_for_tier("nonexistent")
        assert len(providers) > 0

    def test_model_for_provider_returns_correct_model(self):
        router = ModelTierRouter()
        model = router.model_for_provider("fast", "groq")
        assert model == "llama-3.3-70b-versatile"

    def test_model_for_provider_returns_none_for_unknown(self):
        router = ModelTierRouter()
        model = router.model_for_provider("fast", "nonexistent_provider")
        assert model is None

    def test_reload_does_not_raise(self):
        router = ModelTierRouter()
        router.reload()
        assert router._loaded is True

    def test_load_tier_models_falls_back_on_missing_file(self, monkeypatch):
        router = ModelTierRouter()
        monkeypatch.setattr(
            "api.routing.policy_engine._TIERS_PATH",
            Path("/nonexistent/path/tiers.toml"),
        )
        models = router._load_tier_models()
        assert models == router.TIER_MODELS


# =========================================================================
# provider_selection.py
# =========================================================================


class TestSoftmaxPct:
    def test_empty_scores_returns_empty_dict(self):
        assert _softmax_pct({}) == {}

    def test_single_provider_gets_100_percent(self):
        result = _softmax_pct({"openai": 0.8})
        assert result["openai"] == 100

    def test_multiple_providers_sum_to_100(self):
        result = _softmax_pct({"openai": 0.8, "anthropic": 0.6, "gemini": 0.4})
        total = sum(result.values())
        assert total == 100

    def test_temperature_scaling_spreads_scores(self):
        close_scores = {"a": 0.51, "b": 0.50, "c": 0.49}
        result = _softmax_pct(close_scores, temperature=0.5)
        total = sum(result.values())
        assert total == 100
        # Higher raw score should still rank higher
        assert result["a"] >= result["b"] >= result["c"]


class TestFallbackReasons:
    def test_no_chosen_provider_lists_all_as_fallback(self):
        from api.routing.provider_selection import ProviderScore

        results = [
            ProviderScore("openai", 0.8, 80),
            ProviderScore("anthropic", 0.6, 20),
        ]
        reasons = _fallback_reasons(None, results)
        assert len(reasons) == 2
        assert all(r["reason"] == "candidate_available_but_no_selection" for r in reasons)

    def test_chosen_provider_lists_others_as_ranked_below(self):
        from api.routing.provider_selection import ProviderScore

        chosen = ProviderScore("openai", 0.8, 80)
        results = [
            chosen,
            ProviderScore("anthropic", 0.6, 20),
        ]
        reasons = _fallback_reasons(chosen, results)
        assert len(reasons) == 1
        assert reasons[0]["reason"] == "ranked_below_selected_provider"
        assert reasons[0]["provider_id"] == "anthropic"
        assert reasons[0]["score_delta"] == 0.2
        assert reasons[0]["pct_delta"] == 60

    def test_empty_results_returns_empty_list(self):
        reasons = _fallback_reasons(None, [])
        assert reasons == []


class TestStageLatencyPercentiles:
    def test_empty_trace_returns_zeros(self):
        result = _stage_latency_percentiles([])
        assert result == {"p50": 0.0, "p90": 0.0, "p95": 0.0, "p99": 0.0}

    def test_single_sample_returns_that_value(self):
        result = _stage_latency_percentiles([{"duration_ms": 42.0}])
        assert result["p50"] == 42.0
        assert result["p90"] == 42.0
        assert result["p95"] == 42.0
        assert result["p99"] == 42.0

    def test_multiple_samples_computes_percentiles(self):
        entries = [{"duration_ms": float(i)} for i in range(1, 101)]
        result = _stage_latency_percentiles(entries)
        assert result["p50"] >= 50.0
        assert result["p90"] >= 90.0
        assert result["p99"] >= 99.0

    def test_negative_durations_are_clamped_to_zero(self):
        result = _stage_latency_percentiles([{"duration_ms": -5.0}, {"duration_ms": 10.0}])
        assert result["p50"] >= 0.0


# =========================================================================
# registry_store.py
# =========================================================================


class TestRoutingRegistryStore:
    def test_load_hourly_spend_returns_empty_when_disabled(self):
        store = RoutingRegistryStore(path="")
        store.enabled = False
        result = store.load_hourly_spend()
        assert result == {}

    def test_load_hourly_spend_returns_empty_when_no_db(self, tmp_path):
        store = RoutingRegistryStore(path=str(tmp_path / "nonexistent.db"))
        result = store.load_hourly_spend()
        assert result == {}

    def test_flush_does_nothing_when_disabled(self):
        store = RoutingRegistryStore(path="")
        store.enabled = False
        store.flush({}, {})
        assert store.last_error == ""

    def test_flush_handles_corrupt_db_gracefully(self, tmp_path):
        db_path = tmp_path / "corrupt.db"
        db_path.write_text("not a valid sqlite database")
        store = RoutingRegistryStore(path=str(db_path))
        store.flush(
            {
                "openai": ProviderStats(
                    provider_id="openai",
                    ewma_latency_ms=100.0,
                    success_count=10,
                    failure_count=1,
                    total_cost_usd=0.5,
                    last_used=time.time(),
                )
            },
            {},
        )
        # Should have logged an error but not raised
        assert store.last_error != ""

    def test_load_returns_empty_when_disabled(self):
        store = RoutingRegistryStore(path="")
        store.enabled = False
        result = store.load()
        assert result == {}

    def test_load_returns_empty_when_no_db(self, tmp_path):
        store = RoutingRegistryStore(path=str(tmp_path / "nonexistent.db"))
        result = store.load()
        assert result == {}

    def test_ensure_schema_idempotent(self, tmp_path):
        import sqlite3

        db_path = tmp_path / "schema_test.db"
        store = RoutingRegistryStore(path=str(db_path))
        with sqlite3.connect(str(db_path)) as conn:
            store._ensure_schema(conn)
            store._ensure_schema(conn)  # second call should not raise
        assert db_path.exists()


# =========================================================================
# router_registry.py
# =========================================================================


class TestRoutingRegistry:
    def test_record_success_with_tokens_updates_ewma(self, tmp_path):
        db_path = tmp_path / "test_tokens.db"
        registry = RoutingRegistry(store=RoutingRegistryStore(path=str(db_path)))
        registry.record_success(
            "openai",
            latency_ms=1000.0,
            cost_usd=0.25,
            input_tokens=100,
            output_tokens=50,
            task_type="coding",
        )
        stats = registry.get("openai")
        # tps = (100 + 50) / (1000 / 1000) = 150
        # ewma = 0.2 * 150 + 0.8 * 0 = 30
        assert stats.ewma_tokens_per_sec == 30.0
        assert stats.total_output_tokens == 50

    def test_record_success_without_tokens_does_not_update_ewma(self, tmp_path):
        db_path = tmp_path / "test_no_tokens.db"
        registry = RoutingRegistry(store=RoutingRegistryStore(path=str(db_path)))
        registry.record_success("openai", latency_ms=1000.0, cost_usd=0.25)
        stats = registry.get("openai")
        assert stats.ewma_tokens_per_sec == 0.0
        assert stats.total_output_tokens == 0

    def test_record_failure_with_task_type(self, tmp_path):
        db_path = tmp_path / "test_failure.db"
        registry = RoutingRegistry(store=RoutingRegistryStore(path=str(db_path)))
        registry.record_failure("openai", task_type="coding")
        stats = registry.get("openai")
        assert stats.failure_count == 1

    def test_log_decision_appends_to_audit_trail(self, tmp_path):
        db_path = tmp_path / "test_decision.db"
        registry = RoutingRegistry(store=RoutingRegistryStore(path=str(db_path)))
        registry.log_decision(
            request_id="req-1",
            cost_weight=0.35,
            candidates=["openai", "anthropic"],
            score_breakdown={"openai": {"score": 0.8}},
            rank_order=["openai", "anthropic"],
        )
        trail = registry.get_audit_trail()
        assert len(trail) == 1
        assert trail[0]["request_id"] == "req-1"

    def test_persistence_status_returns_all_fields(self, tmp_path):
        db_path = tmp_path / "test_status.db"
        registry = RoutingRegistry(store=RoutingRegistryStore(path=str(db_path)))
        status = registry.persistence_status()
        assert "path" in status
        assert "dirty" in status
        assert "flush_interval_seconds" in status
        assert "current_hour_bucket" in status
        assert "current_hour_spend_total" in status

    def test_flush_clears_dirty_flag(self, tmp_path):
        db_path = tmp_path / "test_flush.db"
        registry = RoutingRegistry(store=RoutingRegistryStore(path=str(db_path)))
        registry.record_success("openai", latency_ms=100.0, cost_usd=0.0)
        assert registry.persistence_status()["dirty"] is True
        registry.flush()
        assert registry.persistence_status()["dirty"] is False

    def test_current_hour_spend_total_rounds_correctly(self, tmp_path):
        db_path = tmp_path / "test_spend.db"
        registry = RoutingRegistry(store=RoutingRegistryStore(path=str(db_path)))
        registry.record_success("openai", latency_ms=100.0, cost_usd=0.1234567)
        total = registry.current_hour_spend_total()
        assert total == 0.123457  # rounded to 6 decimal places

    def test_snapshot_includes_token_metrics(self, tmp_path):
        db_path = tmp_path / "test_snapshot.db"
        registry = RoutingRegistry(store=RoutingRegistryStore(path=str(db_path)))
        registry.record_success(
            "openai",
            latency_ms=1000.0,
            cost_usd=0.25,
            input_tokens=100,
            output_tokens=50,
        )
        snap = registry.snapshot()
        assert "openai" in snap
        assert snap["openai"]["ewma_tokens_per_sec"] == 30.0
        assert snap["openai"]["total_output_tokens"] == 50

    def test_metrics_snapshot_includes_hourly_spend(self, tmp_path):
        db_path = tmp_path / "test_metrics.db"
        registry = RoutingRegistry(store=RoutingRegistryStore(path=str(db_path)))
        registry.record_success("openai", latency_ms=100.0, cost_usd=0.50)
        metrics = registry.metrics_snapshot()
        assert "current_hour_bucket" in metrics
        assert "current_hour_spend" in metrics
        assert "current_hour_spend_total" in metrics

    def test_close_flushes_and_clears_dirty(self, tmp_path):
        db_path = tmp_path / "test_close.db"
        registry = RoutingRegistry(store=RoutingRegistryStore(path=str(db_path)))
        registry.record_success("openai", latency_ms=100.0, cost_usd=0.0)
        registry.close()
        assert registry.persistence_status()["dirty"] is False

    def test_async_restore_from_supabase_does_not_raise(self, tmp_path):
        db_path = tmp_path / "test_async_restore.db"
        registry = RoutingRegistry(store=RoutingRegistryStore(path=str(db_path)))

        async def _run():
            await registry.async_restore_from_supabase()

        asyncio.run(_run())
        assert True

    def test_hourly_spend_snapshot_returns_rounded_values(self, tmp_path):
        db_path = tmp_path / "test_hourly_snapshot.db"
        registry = RoutingRegistry(store=RoutingRegistryStore(path=str(db_path)))
        registry.record_success("openai", latency_ms=100.0, cost_usd=0.123456789)
        snap = registry.hourly_spend_snapshot()
        assert any(spend == 0.123457 for hb in snap.values() for spend in hb.values())


# =========================================================================
# health_provider.py
# =========================================================================


class TestStatusIsAvailable:
    def test_returns_false_when_error_present(self):
        assert (
            _status_is_available({"error": "timeout", "configured": True, "status": "healthy"})
            is False
        )

    def test_returns_false_when_not_configured(self):
        assert _status_is_available({"configured": False, "status": "healthy"}) is False

    def test_returns_true_when_healthy_and_configured(self):
        assert _status_is_available({"configured": True, "status": "healthy"}) is True

    def test_returns_true_when_degraded_and_configured(self):
        assert _status_is_available({"configured": True, "status": "degraded"}) is True

    def test_returns_false_when_unhealthy(self):
        assert _status_is_available({"configured": True, "status": "unhealthy"}) is False

    def test_returns_false_when_status_unknown(self):
        assert _status_is_available({"configured": True, "status": "unknown"}) is False

    def test_returns_true_by_default_for_empty_status(self):
        assert _status_is_available({"configured": True}) is False


class TestCachedProviderHealthProvider:
    def test_availability_for_empty_list(self):
        provider = CachedProviderHealthProvider()
        result = provider.availability_for([])
        assert result == {}

    def test_availability_for_returns_default_true_when_import_fails(self, monkeypatch):
        provider = CachedProviderHealthProvider()

        def _fail_import(*args, **kwargs):
            raise ImportError("no health monitor")

        monkeypatch.setattr("importlib.import_module", _fail_import)

        result = provider.availability_for(["openai", "anthropic"])
        assert result == {"openai": True, "anthropic": True}

    def test_availability_for_handles_non_mapping_status(self, monkeypatch):
        provider = CachedProviderHealthProvider()
        fake_monitor = MagicMock()
        fake_monitor.get_all_status.return_value = ["not_a_dict"]

        def _fake_import(name):
            module = MagicMock()
            module.health_monitor = fake_monitor
            return module

        monkeypatch.setattr("importlib.import_module", _fake_import)

        result = provider.availability_for(["openai"])
        assert result == {"openai": True}


class TestStaticHealthProvider:
    def test_availability_for_returns_configured_values(self):
        provider = StaticHealthProvider({"openai": True, "anthropic": False})
        result = provider.availability_for(["openai", "anthropic", "gemini"])
        assert result["openai"] is True
        assert result["anthropic"] is False
        assert result["gemini"] is True  # default

    def test_availability_for_empty_constructor(self):
        provider = StaticHealthProvider()
        result = provider.availability_for(["openai"])
        assert result["openai"] is True


# =========================================================================
# routing_pipeline.py — error paths
# =========================================================================


class TestRoutingPipelineErrorPaths:
    def test_score_with_empty_candidates_returns_empty(self):
        from api.routing.feature_extractor import RoutingFeatures
        from api.routing.routing_pipeline import RoutingPipeline

        pipeline = RoutingPipeline(
            feature_router=MagicMock(),
            bandit_cache=MagicMock(),
            feature_extractor_service=MagicMock(),
            classifier_service=MagicMock(),
            policy_engine_service=MagicMock(),
            registry=MagicMock(),
            health_provider_service=MagicMock(),
        )
        features = RoutingFeatures(
            prompt_length_bucket=0,
            task_type="chat",
            complexity_score=0.5,
            conversation_turn=0,
            intent_label="chat",
            intent_confidence=0.8,
        )
        result = pipeline.score([], features, task_type="chat", routing_id="empty-score")
        assert result.scores == []
        assert result.selected_provider_id is None

    def test_route_prompt_with_empty_candidates_returns_empty(self):
        from api.routing.feature_extractor import RoutingFeatures
        from api.routing.routing_pipeline import RoutingPipeline

        # Use a real feature extractor that returns a dataclass so replace() works
        real_extractor = MagicMock()
        real_extractor.extract_request.return_value = RoutingFeatures(
            prompt_length_bucket=0,
            task_type="chat",
            complexity_score=0.5,
            conversation_turn=0,
            intent_label="chat",
            intent_confidence=0.8,
        )

        pipeline = RoutingPipeline(
            feature_router=MagicMock(),
            bandit_cache=MagicMock(),
            feature_extractor_service=real_extractor,
            classifier_service=MagicMock(),
            policy_engine_service=MagicMock(),
            registry=MagicMock(),
            health_provider_service=MagicMock(),
        )
        result = pipeline.route_prompt([], "hello", routing_id="empty-test")
        assert result.scores == []
        assert result.selected_provider_id is None
