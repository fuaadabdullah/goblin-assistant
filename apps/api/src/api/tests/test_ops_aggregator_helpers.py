"""Tests for the aggregator's scoring helpers.

reliability, performance_metrics, provider_metrics and health are the pure
functions behind the ops dashboard's numbers: freshness grading, trend
detection, the weighted health scores, and the recommendation strings. They
have no I/O, so these are straight input/output tests over the thresholds.
"""

from __future__ import annotations

import time
from collections import deque

import pytest

from api.ops.aggregator.health import build_summary, generate_recommendations
from api.ops.aggregator.models import MetricReliability, SystemHealth
from api.ops.aggregator.performance_metrics import (
    calculate_aggregated_performance,
    calculate_performance_health_score,
)
from api.ops.aggregator.provider_metrics import (
    calculate_provider_health_score,
    get_provider_capabilities,
    get_provider_priority,
)
from api.ops.aggregator.reliability import assess_reliability, calculate_trend


def _history(*entries) -> deque:
    return deque(entries)


def _fresh(value: float = 1.0, age_s: float = 0.0) -> dict:
    return {"value": value, "timestamp": time.time() - age_s}


# ---------------------------------------------------------------------------
# reliability.assess_reliability
# ---------------------------------------------------------------------------


class TestAssessReliability:
    def test_empty_history_is_unknown(self):
        assert assess_reliability(deque(), time.time()) is MetricReliability.UNKNOWN

    def test_older_than_five_minutes_is_poor(self):
        assert assess_reliability(_history(_fresh()), time.time() - 400) is MetricReliability.POOR

    def test_older_than_a_minute_is_fair(self):
        assert assess_reliability(_history(_fresh()), time.time() - 120) is MetricReliability.FAIR

    def test_older_than_ten_seconds_is_good(self):
        assert assess_reliability(_history(_fresh()), time.time() - 30) is MetricReliability.GOOD

    def test_fresh_with_a_dense_history_is_excellent(self):
        history = _history(*[_fresh() for _ in range(5)])

        assert assess_reliability(history, time.time()) is MetricReliability.EXCELLENT

    def test_fresh_with_a_thin_history_is_good(self):
        history = _history(_fresh(), _fresh())

        assert assess_reliability(history, time.time()) is MetricReliability.GOOD

    def test_fresh_with_only_stale_history_is_fair(self):
        history = _history(_fresh(age_s=120))

        assert assess_reliability(history, time.time()) is MetricReliability.FAIR


# ---------------------------------------------------------------------------
# reliability.calculate_trend
# ---------------------------------------------------------------------------


class TestCalculateTrend:
    def test_too_few_points_has_no_trend(self):
        history = _history(_fresh(1.0), _fresh(2.0))

        assert calculate_trend(history) is None

    def test_points_outside_the_window_are_ignored(self):
        history = _history(*[_fresh(float(i), age_s=3600) for i in range(5)])

        assert calculate_trend(history, window_minutes=10) is None

    def test_rising_values_are_increasing(self):
        history = _history(_fresh(1.0), _fresh(5.0), _fresh(9.0))

        assert calculate_trend(history) == "increasing"

    def test_falling_values_are_decreasing(self):
        history = _history(_fresh(9.0), _fresh(5.0), _fresh(1.0))

        assert calculate_trend(history) == "decreasing"

    def test_flat_values_are_stable(self):
        history = _history(_fresh(5.0), _fresh(5.0), _fresh(5.0))

        assert calculate_trend(history) == "stable"

    def test_a_negligible_slope_counts_as_stable(self):
        history = _history(_fresh(5.0), _fresh(5.001), _fresh(5.002))

        assert calculate_trend(history) == "stable"


# ---------------------------------------------------------------------------
# performance_metrics
# ---------------------------------------------------------------------------


class TestAggregatedPerformance:
    def test_a_healthy_system_scores_full_marks(self):
        scores = calculate_aggregated_performance({}, {})

        assert scores["redis_performance"] == 100
        assert scores["task_performance"] == 100
        assert scores["queue_health"] == 100
        assert scores["overall_performance"] == 100

    def test_redis_in_error_zeroes_its_score(self):
        scores = calculate_aggregated_performance({"status": "error"}, {})

        assert scores["redis_performance"] == 0

    def test_many_redis_clients_dock_the_score(self):
        scores = calculate_aggregated_performance({"connected_clients": 150}, {})

        assert scores["redis_performance"] == 70

    @pytest.mark.parametrize("failure_rate,expected", [(25, 40), (15, 70), (7, 85), (1, 100)])
    def test_task_score_steps_down_with_the_failure_rate(self, failure_rate, expected):
        scores = calculate_aggregated_performance({}, {"failure_rate": failure_rate})

        assert scores["task_performance"] == expected

    def test_a_queue_far_ahead_of_workers_scores_lowest(self):
        scores = calculate_aggregated_performance({}, {"queued_tasks": 10, "running_tasks": 2})

        assert scores["queue_health"] == 60

    def test_a_queue_slightly_ahead_of_workers_scores_middling(self):
        scores = calculate_aggregated_performance({}, {"queued_tasks": 3, "running_tasks": 2})

        assert scores["queue_health"] == 80

    def test_overall_is_the_mean_of_the_three(self):
        scores = calculate_aggregated_performance(
            {"status": "error"}, {"failure_rate": 25, "queued_tasks": 10, "running_tasks": 2}
        )

        assert scores["overall_performance"] == round((0 + 40 + 60) / 3, 1)

    def test_bad_input_degrades_instead_of_raising(self):
        # task_metrics is not a mapping, so .get blows up inside the helper.
        scores = calculate_aggregated_performance({}, "not-a-dict")

        assert scores == {"overall_performance": 0}


class TestPerformanceHealthScore:
    def test_missing_aggregate_defaults_to_the_midpoint(self):
        assert calculate_performance_health_score({}) == 50.0

    def test_weights_redis_and_tasks_above_the_queue(self):
        score = calculate_performance_health_score(
            {
                "aggregated": {
                    "redis_performance": 100,
                    "task_performance": 100,
                    "queue_health": 0,
                }
            }
        )

        assert score == 80.0

    def test_a_perfect_system_scores_100(self):
        score = calculate_performance_health_score(
            {
                "aggregated": {
                    "redis_performance": 100,
                    "task_performance": 100,
                    "queue_health": 100,
                }
            }
        )

        assert score == 100.0


# ---------------------------------------------------------------------------
# provider_metrics
# ---------------------------------------------------------------------------


class TestProviderSettingsLookups:
    def test_finds_capabilities_by_name(self):
        settings = [{"name": "openai", "capabilities": ["chat", "embed"]}]

        assert get_provider_capabilities(settings, "openai") == ["chat", "embed"]

    def test_unknown_provider_has_no_capabilities(self):
        assert get_provider_capabilities([{"name": "other"}], "openai") == []

    def test_provider_without_capabilities_returns_empty(self):
        assert get_provider_capabilities([{"name": "openai"}], "openai") == []

    def test_finds_priority_by_name(self):
        settings = [{"name": "openai", "priority_tier": 2}]

        assert get_provider_priority(settings, "openai") == 2

    def test_unknown_provider_has_priority_zero(self):
        assert get_provider_priority([{"name": "other"}], "openai") == 0

    def test_provider_without_priority_defaults_to_zero(self):
        assert get_provider_priority([{"name": "openai"}], "openai") == 0


class TestProviderHealthScore:
    def test_no_providers_scores_the_midpoint(self):
        assert calculate_provider_health_score({}) == 50.0

    def test_all_healthy_and_excellent_scores_100(self):
        metrics = {
            "a": {"status": "healthy", "reliability": "excellent"},
            "b": {"status": "healthy", "reliability": "excellent"},
        }

        assert calculate_provider_health_score(metrics) == 100.0

    def test_availability_dominates_the_score(self):
        metrics = {
            "a": {"status": "healthy", "reliability": "excellent"},
            "b": {"status": "critical", "reliability": "excellent"},
        }

        # 50% available -> 35, plus full reliability -> 30
        assert calculate_provider_health_score(metrics) == 65.0

    @pytest.mark.parametrize(
        "reliability,expected",
        [("excellent", 100.0), ("good", 92.5), ("fair", 85.0), ("poor", 77.5)],
    )
    def test_reliability_grades_shift_the_score(self, reliability, expected):
        metrics = {"a": {"status": "healthy", "reliability": reliability}}

        assert calculate_provider_health_score(metrics) == expected


# ---------------------------------------------------------------------------
# health
# ---------------------------------------------------------------------------


def _health(status: str = "healthy", score: float = 95.0) -> SystemHealth:
    return SystemHealth(
        overall_score=score,
        status=status,
        components={},
        trend="stable",
        last_updated=time.time(),
        reliability=MetricReliability.GOOD,
    )


class TestBuildSummary:
    def test_counts_healthy_providers(self):
        providers = {
            "a": {"status": "healthy"},
            "b": {"status": "critical"},
        }

        summary = build_summary(providers, {}, _health())

        assert summary["active_providers"] == 1
        assert summary["total_providers"] == 2

    def test_carries_the_health_fields_through(self):
        summary = build_summary({}, {}, _health(status="degraded", score=72.5))

        assert summary["status"] == "degraded"
        assert summary["health_score"] == 72.5
        assert summary["trend"] == "stable"

    def test_reads_the_aggregate_performance_score(self):
        summary = build_summary({}, {"aggregated": {"overall_performance": 88}}, _health())

        assert summary["performance_score"] == 88

    def test_defaults_the_performance_score_to_zero(self):
        assert build_summary({}, {}, _health())["performance_score"] == 0


class TestGenerateRecommendations:
    def test_a_healthy_system_needs_no_advice(self):
        performance = {"aggregated": {"overall_performance": 95}}

        assert generate_recommendations({"a": {"status": "healthy"}}, performance) == []

    def test_flags_unhealthy_providers_with_a_count(self):
        providers = {"a": {"status": "critical"}, "b": {"status": "degraded"}}
        performance = {"aggregated": {"overall_performance": 95}}

        assert "Check 2 unhealthy providers" in generate_recommendations(providers, performance)

    def test_flags_degraded_performance(self):
        recommendations = generate_recommendations({}, {"aggregated": {"overall_performance": 40}})

        assert any("performance degradation" in r for r in recommendations)

    def test_flags_a_building_queue(self):
        performance = {
            "aggregated": {"overall_performance": 95},
            "tasks": {"queued_tasks": 20, "running_tasks": 2},
        }

        recommendations = generate_recommendations({}, performance)

        assert any("scaling task workers" in r for r in recommendations)

    def test_a_queue_matching_capacity_is_not_flagged(self):
        performance = {
            "aggregated": {"overall_performance": 95},
            "tasks": {"queued_tasks": 2, "running_tasks": 2},
        }

        assert generate_recommendations({}, performance) == []
