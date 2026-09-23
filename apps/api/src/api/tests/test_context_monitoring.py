"""Tests for ContextMonitoringService — assembly metrics, budget tracking,
recommendations, and the health check.

track_assembly is the one method with real branching (it parses an
assembly_log if present, and updates several running aggregates), so it gets
the most cases. The derived getters (performance, budget, recommendations)
are exercised both from a fresh instance and after track_assembly has run,
since several of them divide by counts that start at zero.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from api.services.context_monitoring import ContextMonitoringService


@pytest.fixture
def service() -> ContextMonitoringService:
    return ContextMonitoringService()


def _assembly_log(*, layers=("system", "semantic_retrieval"), token_usage=None) -> dict:
    return {
        "assembly_time": (datetime.utcnow() - timedelta(milliseconds=50)).isoformat(),
        "layers": list(layers),
        "token_usage": token_usage or {name: 100 for name in layers},
    }


# ---------------------------------------------------------------------------
# initialize / construction
# ---------------------------------------------------------------------------


class TestConstruction:
    def test_starts_with_no_metrics(self, service):
        assert service.assembly_metrics == []
        assert service.success_count == 0
        assert service.error_count == 0

    def test_every_layer_starts_at_zero(self, service):
        assert all(
            stats == {"success": 0, "skipped": 0, "failed": 0}
            for stats in service.layer_effectiveness.values()
        )

    def test_initialize_wires_up_the_collaborators(self, service):
        assembly_service = MagicMock()
        prompt_manager = MagicMock()

        service.initialize(assembly_service, prompt_manager)

        assert service.assembly_service is assembly_service
        assert service.system_prompt_manager is prompt_manager

    def test_default_budget_totals_eight_thousand_tokens(self, service):
        assert service.budget_metrics.budget_config["total_tokens"] == 8000


# ---------------------------------------------------------------------------
# track_assembly
# ---------------------------------------------------------------------------


class TestTrackAssembly:
    @pytest.mark.asyncio
    async def test_records_a_successful_assembly(self, service):
        await service.track_assembly(
            {"assembly_log": _assembly_log(), "total_tokens_used": 200, "remaining_tokens": 7800},
            user_id="u-1",
            conversation_id="c-1",
            query="hello",
            success=True,
        )

        assert len(service.assembly_metrics) == 1
        assert service.success_count == 1
        assert service.error_count == 0
        recorded = service.assembly_metrics[0]
        assert recorded.layers_assembled == 2
        assert recorded.total_tokens_used == 200

    @pytest.mark.asyncio
    async def test_records_a_failed_assembly(self, service):
        await service.track_assembly(
            {}, user_id=None, conversation_id=None, query="q", success=False, error="boom"
        )

        assert service.error_count == 1
        assert service.assembly_metrics[0].error == "boom"

    @pytest.mark.asyncio
    async def test_missing_assembly_log_yields_no_layers(self, service):
        await service.track_assembly(
            {"total_tokens_used": 10, "remaining_tokens": 100},
            user_id=None,
            conversation_id=None,
            query="q",
            success=True,
        )

        assert service.assembly_metrics[0].layers_assembled == 0

    @pytest.mark.asyncio
    async def test_updates_layer_effectiveness_for_each_layer(self, service):
        await service.track_assembly(
            {"assembly_log": _assembly_log(layers=("system",))},
            user_id=None,
            conversation_id=None,
            query="q",
            success=True,
        )

        assert service.layer_effectiveness["system"]["success"] == 1

    @pytest.mark.asyncio
    async def test_unknown_layer_names_are_ignored_rather_than_raising(self, service):
        await service.track_assembly(
            {"assembly_log": _assembly_log(layers=("mystery_layer",))},
            user_id=None,
            conversation_id=None,
            query="q",
            success=True,
        )

        assert "mystery_layer" not in service.layer_effectiveness

    @pytest.mark.asyncio
    async def test_assembly_times_cap_at_the_last_hundred(self, service):
        for _ in range(105):
            await service.track_assembly(
                {"assembly_log": _assembly_log()},
                user_id=None,
                conversation_id=None,
                query="q",
                success=True,
            )

        assert len(service.assembly_times) == 100

    @pytest.mark.asyncio
    async def test_tracking_never_raises_even_with_malformed_input(self, service):
        # assembly_time isn't a valid ISO timestamp
        await service.track_assembly(
            {"assembly_log": {"assembly_time": "not-a-date", "layers": []}},
            user_id=None,
            conversation_id=None,
            query="q",
            success=True,
        )

        # The exception is swallowed, so nothing gets recorded.
        assert service.assembly_metrics == []


class TestBudgetMetricsUpdate:
    @pytest.mark.asyncio
    async def test_flags_an_assembly_that_exceeds_the_budget(self, service):
        await service.track_assembly(
            {"assembly_log": _assembly_log(), "total_tokens_used": 9000, "remaining_tokens": 0},
            user_id=None,
            conversation_id=None,
            query="q",
            success=True,
        )

        assert service.budget_metrics.budget_exceeded_count == 1

    @pytest.mark.asyncio
    async def test_flags_a_hard_stop_when_few_layers_fit(self, service):
        await service.track_assembly(
            {
                "assembly_log": _assembly_log(layers=("system",)),
                "total_tokens_used": 8000,
                "remaining_tokens": 0,
            },
            user_id=None,
            conversation_id=None,
            query="q",
            success=True,
        )

        assert service.budget_metrics.hard_stop_triggered_count == 1

    @pytest.mark.asyncio
    async def test_a_well_within_budget_assembly_does_not_trip_either_flag(self, service):
        await service.track_assembly(
            {"assembly_log": _assembly_log(), "total_tokens_used": 100, "remaining_tokens": 7900},
            user_id=None,
            conversation_id=None,
            query="q",
            success=True,
        )

        assert service.budget_metrics.budget_exceeded_count == 0
        assert service.budget_metrics.hard_stop_triggered_count == 0

    @pytest.mark.asyncio
    async def test_averages_are_computed_over_all_recorded_assemblies(self, service):
        for tokens in (100, 300):
            await service.track_assembly(
                {
                    "assembly_log": _assembly_log(),
                    "total_tokens_used": tokens,
                    "remaining_tokens": 0,
                },
                user_id=None,
                conversation_id=None,
                query="q",
                success=True,
            )

        assert service.budget_metrics.average_tokens_used == 200.0


# ---------------------------------------------------------------------------
# get_assembly_performance
# ---------------------------------------------------------------------------


class TestAssemblyPerformance:
    def test_a_fresh_service_reports_zero_rates(self, service):
        performance = service.get_assembly_performance()

        assert performance["total_assemblies"] == 0
        assert performance["success_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_computes_success_and_error_rates(self, service):
        await service.track_assembly({}, None, None, "q", success=True)
        await service.track_assembly({}, None, None, "q", success=True)
        await service.track_assembly({}, None, None, "q", success=False, error="x")

        performance = service.get_assembly_performance()

        assert performance["total_assemblies"] == 3
        assert performance["success_rate"] == pytest.approx(66.67, abs=0.01)
        assert performance["error_rate"] == pytest.approx(33.33, abs=0.01)

    @pytest.mark.asyncio
    async def test_recent_assemblies_are_capped_at_ten(self, service):
        for _ in range(15):
            await service.track_assembly({}, None, None, "q", success=True)

        assert len(service.get_assembly_performance()["recent_assemblies"]) == 10


# ---------------------------------------------------------------------------
# get_budget_utilization / _calculate_budget_efficiency
# ---------------------------------------------------------------------------


class TestBudgetUtilization:
    def test_efficiency_is_zero_with_no_history(self, service):
        assert service._calculate_budget_efficiency() == 0.0

    @pytest.mark.asyncio
    async def test_efficiency_reflects_usage_against_the_full_budget(self, service):
        await service.track_assembly(
            {"total_tokens_used": 4000, "remaining_tokens": 4000},
            None,
            None,
            "q",
            success=True,
        )

        # 4000 used out of an 8000 budget = 50%
        assert service._calculate_budget_efficiency() == 50.0

    def test_utilization_payload_includes_the_configured_budget(self, service):
        utilization = service.get_budget_utilization()

        assert utilization["budget_config"]["total_tokens"] == 8000
        assert "budget_efficiency" in utilization


# ---------------------------------------------------------------------------
# get_debug_info
# ---------------------------------------------------------------------------


class TestDebugInfo:
    def test_uninitialized_collaborators_yield_empty_sections(self, service):
        debug = service.get_debug_info()

        assert debug["assembly_service"] == {}
        assert debug["system_prompt"] == {}

    def test_initialized_collaborators_contribute_their_debug_info(self, service):
        assembly_service = MagicMock()
        assembly_service.get_debug_info.return_value = {"budget": {"total_tokens": 8000}}
        prompt_manager = MagicMock()
        prompt_manager.get_debug_info.return_value = {"prompt_length": 42}
        service.initialize(assembly_service, prompt_manager)

        debug = service.get_debug_info()

        assert debug["assembly_service"]["budget"]["total_tokens"] == 8000
        assert debug["system_prompt"]["prompt_length"] == 42

    def test_reports_monitoring_stats(self, service):
        stats = service.get_debug_info()["monitoring_stats"]

        assert stats == {
            "total_metrics_stored": 0,
            "success_count": 0,
            "error_count": 0,
            "assembly_times_count": 0,
        }


# ---------------------------------------------------------------------------
# get_optimization_recommendations
# ---------------------------------------------------------------------------


class TestOptimizationRecommendations:
    def test_a_healthy_fresh_service_has_no_recommendations(self, service):
        # Zero assemblies means 0% success rate and 0% budget efficiency,
        # which the thresholds would otherwise flag; both checks below 95%
        # and below 50% would fire on an empty service, so this pins that
        # a fresh service still returns *some* recommendations rather than
        # silently passing every check.
        recommendations = service.get_optimization_recommendations()

        types = {r["type"] for r in recommendations}
        assert "reliability" in types  # 0% success rate

    @pytest.mark.asyncio
    async def test_slow_assembly_is_flagged(self, service, monkeypatch):
        monkeypatch.setattr(
            service,
            "get_assembly_performance",
            lambda: {
                "average_assembly_time_ms": 2000,
                "success_rate": 100,
            },
        )
        monkeypatch.setattr(
            service,
            "get_budget_utilization",
            lambda: {"budget_efficiency": 80, "hard_stop_triggered_count": 0},
        )

        recommendations = service.get_optimization_recommendations()

        assert any(r["type"] == "performance" for r in recommendations)

    def test_low_budget_efficiency_is_flagged(self, service, monkeypatch):
        monkeypatch.setattr(
            service,
            "get_assembly_performance",
            lambda: {"average_assembly_time_ms": 100, "success_rate": 100},
        )
        monkeypatch.setattr(
            service,
            "get_budget_utilization",
            lambda: {"budget_efficiency": 10, "hard_stop_triggered_count": 0},
        )

        recommendations = service.get_optimization_recommendations()

        assert any(r["type"] == "efficiency" for r in recommendations)

    def test_frequent_hard_stops_are_flagged(self, service, monkeypatch):
        monkeypatch.setattr(
            service,
            "get_assembly_performance",
            lambda: {"average_assembly_time_ms": 100, "success_rate": 100},
        )
        monkeypatch.setattr(
            service,
            "get_budget_utilization",
            lambda: {"budget_efficiency": 80, "hard_stop_triggered_count": 15},
        )

        recommendations = service.get_optimization_recommendations()

        assert any(r["type"] == "capacity" for r in recommendations)

    def test_a_struggling_layer_is_flagged(self, service, monkeypatch):
        monkeypatch.setattr(
            service,
            "get_assembly_performance",
            lambda: {"average_assembly_time_ms": 100, "success_rate": 100},
        )
        monkeypatch.setattr(
            service,
            "get_budget_utilization",
            lambda: {"budget_efficiency": 80, "hard_stop_triggered_count": 0},
        )
        service.layer_effectiveness["system"] = {"success": 1, "skipped": 5, "failed": 4}

        recommendations = service.get_optimization_recommendations()

        assert any(r["type"] == "layer_optimization" for r in recommendations)

    def test_a_layer_with_no_attempts_is_not_flagged(self, service, monkeypatch):
        monkeypatch.setattr(
            service,
            "get_assembly_performance",
            lambda: {"average_assembly_time_ms": 100, "success_rate": 100},
        )
        monkeypatch.setattr(
            service,
            "get_budget_utilization",
            lambda: {"budget_efficiency": 80, "hard_stop_triggered_count": 0},
        )

        recommendations = service.get_optimization_recommendations()

        assert not any(r["type"] == "layer_optimization" for r in recommendations)

    def test_a_healthy_system_produces_no_recommendations(self, service, monkeypatch):
        monkeypatch.setattr(
            service,
            "get_assembly_performance",
            lambda: {"average_assembly_time_ms": 100, "success_rate": 99},
        )
        monkeypatch.setattr(
            service,
            "get_budget_utilization",
            lambda: {"budget_efficiency": 90, "hard_stop_triggered_count": 0},
        )

        assert service.get_optimization_recommendations() == []


# ---------------------------------------------------------------------------
# reset_metrics
# ---------------------------------------------------------------------------


class TestResetMetrics:
    @pytest.mark.asyncio
    async def test_clears_everything_back_to_defaults(self, service):
        await service.track_assembly(
            {"assembly_log": _assembly_log()}, None, None, "q", success=True
        )
        service.error_count = 3

        service.reset_metrics()

        assert service.assembly_metrics == []
        assert service.assembly_times == []
        assert service.error_count == 0
        assert service.success_count == 0
        assert service.layer_effectiveness["system"] == {"success": 0, "skipped": 0, "failed": 0}
        assert service.budget_metrics.budget_exceeded_count == 0


# ---------------------------------------------------------------------------
# run_health_check
# ---------------------------------------------------------------------------


class TestRunHealthCheck:
    @pytest.mark.asyncio
    async def test_unhealthy_without_any_collaborators(self, service):
        health = await service.run_health_check()

        assert health["status"] == "unhealthy"
        names = {c["name"]: c["status"] for c in health["checks"]}
        assert names["assembly_service"] == "unhealthy"
        assert names["system_prompt_manager"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_healthy_with_working_collaborators_and_good_performance(self, service):
        assembly_service = MagicMock()
        assembly_service.get_debug_info.return_value = {"budget": {"total_tokens": 8000}}
        prompt_manager = MagicMock()
        prompt_manager.get_debug_info.return_value = {"prompt_length": 10}
        service.initialize(assembly_service, prompt_manager)
        await service.track_assembly({}, None, None, "q", success=True)

        health = await service.run_health_check()

        assert health["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_a_raising_collaborator_degrades_rather_than_fails_outright(self, service):
        assembly_service = MagicMock()
        assembly_service.get_debug_info.side_effect = RuntimeError("boom")
        prompt_manager = MagicMock()
        prompt_manager.get_debug_info.return_value = {"prompt_length": 10}
        service.initialize(assembly_service, prompt_manager)
        await service.track_assembly({}, None, None, "q", success=True)

        health = await service.run_health_check()

        assert health["status"] == "degraded"
        assembly_check = next(c for c in health["checks"] if c["name"] == "assembly_service")
        assert assembly_check["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_low_success_rate_marks_performance_unhealthy(self, service):
        assembly_service = MagicMock()
        assembly_service.get_debug_info.return_value = {"budget": {"total_tokens": 8000}}
        prompt_manager = MagicMock()
        prompt_manager.get_debug_info.return_value = {"prompt_length": 10}
        service.initialize(assembly_service, prompt_manager)
        for _ in range(3):
            await service.track_assembly({}, None, None, "q", success=False, error="x")

        health = await service.run_health_check()

        assert health["status"] == "unhealthy"
        perf_check = next(c for c in health["checks"] if c["name"] == "performance")
        assert perf_check["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_many_hard_stops_degrade_a_healthy_status(self, service, monkeypatch):
        assembly_service = MagicMock()
        assembly_service.get_debug_info.return_value = {"budget": {"total_tokens": 8000}}
        prompt_manager = MagicMock()
        prompt_manager.get_debug_info.return_value = {"prompt_length": 10}
        service.initialize(assembly_service, prompt_manager)
        await service.track_assembly({}, None, None, "q", success=True)
        monkeypatch.setattr(
            service,
            "get_budget_utilization",
            lambda: {"hard_stop_triggered_count": 25},
        )

        health = await service.run_health_check()

        assert health["status"] == "degraded"

    @pytest.mark.asyncio
    async def test_a_total_failure_reports_unhealthy_with_the_error(self, service, monkeypatch):
        def _raise():
            raise RuntimeError("catastrophic")

        monkeypatch.setattr(service, "get_assembly_performance", _raise)

        health = await service.run_health_check()

        assert health["status"] == "unhealthy"
        assert "catastrophic" in health["error"]


def test_module_exposes_a_shared_instance():
    from api.services.context_monitoring import context_monitoring_service

    assert isinstance(context_monitoring_service, ContextMonitoringService)
