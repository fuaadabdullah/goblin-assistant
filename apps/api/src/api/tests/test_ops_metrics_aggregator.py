"""Tests for MetricsAggregator — the ops metrics fan-in.

Every collector here wraps its work in a try/except that degrades to an
"error" payload rather than propagating, because the ops dashboard must keep
rendering when one source is down. That degradation is the behaviour worth
pinning, so each collector is tested both happy and failing.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.ops.aggregator import _service as svc
from api.ops.aggregator._service import MetricsAggregator
from api.ops.aggregator.models import MetricReliability


def _task(
    status: str = "completed",
    *,
    streaming: bool = False,
    duration_s: float | None = 5.0,
) -> Dict[str, Any]:
    task: Dict[str, Any] = {"status": status, "streaming": streaming}
    if duration_s is not None:
        created = datetime(2026, 1, 1, 12, 0, 0)
        task["created_at"] = created.isoformat()
        task["updated_at"] = (created + timedelta(seconds=duration_s)).isoformat()
    return task


@pytest.fixture
def aggregator() -> MetricsAggregator:
    return MetricsAggregator()


# ---------------------------------------------------------------------------
# initialize
# ---------------------------------------------------------------------------


class TestInitialize:
    @pytest.mark.asyncio
    async def test_loads_provider_settings(self, aggregator):
        with patch.object(svc, "get_provider_settings", return_value={"openai": {}}):
            await aggregator.initialize()

        assert aggregator._provider_settings == {"openai": {}}

    @pytest.mark.asyncio
    async def test_falls_back_to_an_empty_list_on_failure(self, aggregator):
        with patch.object(svc, "get_provider_settings", side_effect=RuntimeError("no config")):
            await aggregator.initialize()

        assert aggregator._provider_settings == []


# ---------------------------------------------------------------------------
# Provider metrics
# ---------------------------------------------------------------------------


class TestProviderMetrics:
    @pytest.mark.asyncio
    async def test_normalizes_each_provider_status(self, aggregator):
        status = {
            "openai": {"status": "healthy", "latency_ms": 120, "last_check": 1000, "error": None}
        }

        with patch.object(svc.monitor, "get_status", AsyncMock(return_value=status)):
            metrics = await aggregator._get_provider_metrics()

        assert metrics["openai"]["status"] == "healthy"
        assert metrics["openai"]["latency_ms"] == 120
        assert metrics["openai"]["metadata"]["provider_type"] == "llm"
        assert "reliability" in metrics["openai"]

    @pytest.mark.asyncio
    async def test_defaults_missing_fields(self, aggregator):
        with patch.object(svc.monitor, "get_status", AsyncMock(return_value={"p": {}})):
            metrics = await aggregator._get_provider_metrics()

        assert metrics["p"]["status"] == "unknown"
        assert metrics["p"]["latency_ms"] == 0

    @pytest.mark.asyncio
    async def test_degrades_to_empty_on_monitor_failure(self, aggregator):
        with patch.object(svc.monitor, "get_status", AsyncMock(side_effect=RuntimeError("down"))):
            assert await aggregator._get_provider_metrics() == {}


# ---------------------------------------------------------------------------
# Redis / task / cache metrics
# ---------------------------------------------------------------------------


class TestRedisMetrics:
    @pytest.mark.asyncio
    async def test_reports_unavailable_without_a_client(self, aggregator):
        with patch.object(svc.cache, "_redis", None):
            result = await aggregator._get_redis_metrics()

        assert result["status"] == "unavailable"
        assert result["reliability"] == MetricReliability.POOR.value

    @pytest.mark.asyncio
    async def test_reads_the_info_payload(self, aggregator):
        redis = MagicMock()
        redis.info = AsyncMock(
            return_value={
                "used_memory_human": "1.2M",
                "connected_clients": "4",
                "keyspace_hits": "10",
                "keyspace_misses": "5",
                "uptime_in_seconds": "99",
            }
        )

        with patch.object(svc.cache, "_redis", redis):
            result = await aggregator._get_redis_metrics()

        assert result["memory_usage"] == "1.2M"
        assert result["connected_clients"] == 4
        assert result["keyspace_hits"] == 10
        assert result["uptime_seconds"] == 99

    @pytest.mark.asyncio
    async def test_degrades_on_redis_error(self, aggregator):
        redis = MagicMock()
        redis.info = AsyncMock(side_effect=RuntimeError("conn reset"))

        with patch.object(svc.cache, "_redis", redis):
            result = await aggregator._get_redis_metrics()

        assert result["status"] == "error"
        assert "conn reset" in result["error"]


class TestTaskMetrics:
    @pytest.mark.asyncio
    async def test_counts_each_status_and_derives_rates(self, aggregator):
        tasks = [
            _task("completed"),
            _task("completed"),
            _task("failed", duration_s=None),
            _task("running", duration_s=None),
            _task("queued", duration_s=None),
        ]

        with patch.object(svc.task_store, "list_tasks", AsyncMock(return_value=tasks)):
            result = await aggregator._get_task_metrics()

        assert result["total_tasks"] == 5
        assert result["completed_tasks"] == 2
        assert result["failed_tasks"] == 1
        assert result["running_tasks"] == 1
        assert result["queued_tasks"] == 1
        assert result["completion_rate"] == 40.0
        assert result["failure_rate"] == 20.0
        assert result["avg_completion_time"] == 5.0

    @pytest.mark.asyncio
    async def test_no_tasks_means_zero_rates_not_division_by_zero(self, aggregator):
        with patch.object(svc.task_store, "list_tasks", AsyncMock(return_value=[])):
            result = await aggregator._get_task_metrics()

        assert result["total_tasks"] == 0
        assert result["completion_rate"] == 0
        assert result["avg_completion_time"] == 0

    @pytest.mark.asyncio
    async def test_skips_tasks_with_unparsable_timestamps(self, aggregator):
        bad = {"status": "completed", "created_at": "not-a-date", "updated_at": "also-bad"}

        with patch.object(svc.task_store, "list_tasks", AsyncMock(return_value=[bad])):
            result = await aggregator._get_task_metrics()

        assert result["completed_tasks"] == 1
        assert result["avg_completion_time"] == 0

    @pytest.mark.asyncio
    async def test_ignores_non_positive_durations(self, aggregator):
        backwards = _task("completed", duration_s=-5.0)

        with patch.object(svc.task_store, "list_tasks", AsyncMock(return_value=[backwards])):
            result = await aggregator._get_task_metrics()

        assert result["avg_completion_time"] == 0

    @pytest.mark.asyncio
    async def test_degrades_on_store_failure(self, aggregator):
        with patch.object(
            svc.task_store, "list_tasks", AsyncMock(side_effect=RuntimeError("no db"))
        ):
            result = await aggregator._get_task_metrics()

        assert result["status"] == "error"


class TestCacheMetrics:
    @pytest.mark.asyncio
    async def test_computes_the_hit_ratio(self, aggregator):
        redis = MagicMock()
        redis.info = AsyncMock(
            return_value={"keyspace_hits": "75", "keyspace_misses": "25", "used_memory_human": "2M"}
        )

        with patch.object(svc.cache, "_redis", redis):
            result = await aggregator._get_cache_metrics()

        assert result["hit_ratio"] == 75.0
        assert result["total_requests"] == 100
        assert result["memory_usage"] == "2M"

    @pytest.mark.asyncio
    async def test_no_traffic_yields_a_zero_ratio(self, aggregator):
        with patch.object(svc.cache, "_redis", None):
            result = await aggregator._get_cache_metrics()

        assert result["hit_ratio"] == 0
        assert result["total_requests"] == 0

    @pytest.mark.asyncio
    async def test_degrades_on_redis_error(self, aggregator):
        redis = MagicMock()
        redis.info = AsyncMock(side_effect=RuntimeError("boom"))

        with patch.object(svc.cache, "_redis", redis):
            result = await aggregator._get_cache_metrics()

        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# Streaming comparison
# ---------------------------------------------------------------------------


class TestStreamingMetrics:
    @pytest.mark.asyncio
    async def test_compares_streaming_against_non_streaming(self, aggregator):
        tasks = [
            _task("completed", streaming=True, duration_s=2.0),
            _task("completed", streaming=False, duration_s=4.0),
        ]

        with patch.object(svc.task_store, "list_tasks", AsyncMock(return_value=tasks)):
            result = await aggregator._get_streaming_metrics()

        assert result["streaming"]["count"] == 1
        assert result["non_streaming"]["count"] == 1
        assert result["streaming"]["avg_completion_time"] == 2.0
        # non-streaming took twice as long, so streaming is 2x more efficient
        assert result["comparison"]["time_efficiency"] == 2.0

    @pytest.mark.asyncio
    async def test_failure_rate_is_the_complement_of_completion(self, aggregator):
        tasks = [
            _task("completed", streaming=True),
            _task("failed", streaming=True, duration_s=None),
        ]

        with patch.object(svc.task_store, "list_tasks", AsyncMock(return_value=tasks)):
            result = await aggregator._get_streaming_metrics()

        assert result["streaming"]["completion_rate"] == 50.0
        assert result["streaming"]["failure_rate"] == 50.0

    @pytest.mark.asyncio
    async def test_empty_buckets_report_zero_rather_than_dividing(self, aggregator):
        with patch.object(svc.task_store, "list_tasks", AsyncMock(return_value=[])):
            result = await aggregator._get_streaming_metrics()

        assert result["streaming"]["count"] == 0
        assert result["streaming"]["failure_rate"] == 0
        assert result["comparison"]["time_efficiency"] == 0

    @pytest.mark.asyncio
    async def test_skips_unparsable_timestamps(self, aggregator):
        bad = {
            "status": "completed",
            "streaming": True,
            "created_at": "nope",
            "updated_at": "nope",
        }

        with patch.object(svc.task_store, "list_tasks", AsyncMock(return_value=[bad])):
            result = await aggregator._get_streaming_metrics()

        assert result["streaming"]["avg_completion_time"] == 0

    @pytest.mark.asyncio
    async def test_degrades_on_store_failure(self, aggregator):
        with patch.object(
            svc.task_store, "list_tasks", AsyncMock(side_effect=RuntimeError("no db"))
        ):
            result = await aggregator._get_streaming_metrics()

        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# Performance roll-up
# ---------------------------------------------------------------------------


class TestPerformanceMetrics:
    @pytest.mark.asyncio
    async def test_combines_the_three_sources(self, aggregator):
        with (
            patch.object(aggregator, "_get_redis_metrics", AsyncMock(return_value={"r": 1})),
            patch.object(aggregator, "_get_task_metrics", AsyncMock(return_value={"t": 1})),
            patch.object(aggregator, "_get_cache_metrics", AsyncMock(return_value={"c": 1})),
            patch.object(svc, "calculate_aggregated_performance", return_value={"agg": 1}),
        ):
            result = await aggregator._get_performance_metrics()

        assert result == {
            "redis": {"r": 1},
            "tasks": {"t": 1},
            "cache": {"c": 1},
            "aggregated": {"agg": 1},
        }

    @pytest.mark.asyncio
    async def test_degrades_to_empty_on_failure(self, aggregator):
        with patch.object(
            aggregator, "_get_redis_metrics", AsyncMock(side_effect=RuntimeError("x"))
        ):
            assert await aggregator._get_performance_metrics() == {}


# ---------------------------------------------------------------------------
# System health
# ---------------------------------------------------------------------------


class TestSystemHealth:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "provider,performance,expected",
        [
            (100.0, 100.0, "healthy"),
            (80.0, 80.0, "degraded"),
            (10.0, 10.0, "critical"),
        ],
    )
    async def test_status_follows_the_weighted_score(
        self, aggregator, provider, performance, expected
    ):
        with (
            patch.object(svc, "calculate_provider_health_score", return_value=provider),
            patch.object(svc, "calculate_performance_health_score", return_value=performance),
        ):
            health = await aggregator._calculate_system_health({}, {})

        assert health.status == expected

    @pytest.mark.asyncio
    async def test_providers_are_weighted_more_heavily_than_performance(self, aggregator):
        with (
            patch.object(svc, "calculate_provider_health_score", return_value=100.0),
            patch.object(svc, "calculate_performance_health_score", return_value=0.0),
        ):
            health = await aggregator._calculate_system_health({}, {})

        assert health.overall_score == 60.0
        assert health.components == {"providers": 100.0, "performance": 0.0}

    @pytest.mark.asyncio
    async def test_degrades_to_unknown_on_failure(self, aggregator):
        with patch.object(
            svc, "calculate_provider_health_score", side_effect=RuntimeError("bad input")
        ):
            health = await aggregator._calculate_system_health({}, {})

        assert health.status == "unknown"
        assert health.overall_score == 0
        assert health.reliability == MetricReliability.POOR


class TestHealthTrend:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("increasing", "improving"),
            ("decreasing", "degrading"),
            ("stable", "stable"),
            (None, "stable"),
        ],
    )
    def test_translates_the_raw_trend(self, aggregator, raw, expected):
        with patch.object(aggregator, "_calculate_trend", return_value=raw):
            assert aggregator._calculate_health_trend() == expected


class TestOverallReliability:
    def test_poor_when_nothing_is_fresh(self, aggregator):
        assert aggregator._assess_overall_reliability() == "poor"

    def test_good_when_only_one_source_is_fresh(self, aggregator):
        import time as _time

        aggregator._metric_history["provider_status"].append({"last_check": _time.time()})

        assert aggregator._assess_overall_reliability() == "good"

    def test_excellent_when_both_sources_are_fresh(self, aggregator):
        import time as _time

        now = _time.time()
        aggregator._metric_history["provider_status"].append({"last_check": now})
        aggregator._metric_history["performance"].append({"timestamp": now})

        assert aggregator._assess_overall_reliability() == "excellent"

    def test_stale_entries_do_not_count_as_fresh(self, aggregator):
        aggregator._metric_history["provider_status"].append({"last_check": 0})

        assert aggregator._assess_overall_reliability() == "poor"


# ---------------------------------------------------------------------------
# aggregate_system_metrics
# ---------------------------------------------------------------------------


class TestAggregateSystemMetrics:
    @pytest.mark.asyncio
    async def test_serves_a_fresh_cache_entry_without_recollecting(self, aggregator):
        import time as _time

        cached = {"timestamp": _time.time(), "cached": True}

        with (
            patch.object(svc.cache, "get", AsyncMock(return_value=cached)),
            patch.object(aggregator, "_get_provider_metrics", AsyncMock()) as collect,
        ):
            result = await aggregator.aggregate_system_metrics()

        assert result is cached
        collect.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_recollects_when_the_cache_entry_is_stale(self, aggregator):
        stale = {"timestamp": 0, "cached": True}

        with (
            patch.object(svc.cache, "get", AsyncMock(return_value=stale)),
            patch.object(svc.cache, "set", AsyncMock()) as cache_set,
            patch.object(aggregator, "_get_provider_metrics", AsyncMock(return_value={"p": {}})),
            patch.object(aggregator, "_get_performance_metrics", AsyncMock(return_value={})),
            patch.object(aggregator, "_get_streaming_metrics", AsyncMock(return_value={})),
            patch.object(aggregator, "_calculate_system_health", AsyncMock(return_value="health")),
            patch.object(svc, "build_summary", return_value={"s": 1}),
        ):
            result = await aggregator.aggregate_system_metrics()

        assert result["version"] == "2.0.0"
        assert result["providers"] == {"p": {}}
        assert result["summary"] == {"s": 1}
        cache_set.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_records_the_aggregation_time(self, aggregator):
        with (
            patch.object(svc.cache, "get", AsyncMock(return_value=None)),
            patch.object(svc.cache, "set", AsyncMock()),
            patch.object(aggregator, "_get_provider_metrics", AsyncMock(return_value={})),
            patch.object(aggregator, "_get_performance_metrics", AsyncMock(return_value={})),
            patch.object(aggregator, "_get_streaming_metrics", AsyncMock(return_value={})),
            patch.object(aggregator, "_calculate_system_health", AsyncMock(return_value="h")),
            patch.object(svc, "build_summary", return_value={}),
        ):
            await aggregator.aggregate_system_metrics()

        assert aggregator._last_aggregation_time > 0

    @pytest.mark.asyncio
    async def test_reports_aggregation_failure_rather_than_raising(self, aggregator):
        with patch.object(svc.cache, "get", AsyncMock(side_effect=RuntimeError("cache down"))):
            result = await aggregator.aggregate_system_metrics()

        assert result["status"] == "aggregation_failed"
        assert "cache down" in result["error"]


def test_module_exposes_a_shared_aggregator():
    assert isinstance(svc.aggregator, MetricsAggregator)
