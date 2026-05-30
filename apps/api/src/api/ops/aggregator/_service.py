import logging
import statistics
import time
from collections import defaultdict, deque
from datetime import datetime
from typing import Any, Dict, Optional

from ...storage.cache import cache
from ...storage.tasks import task_store
from ...monitoring import monitor
from ...config.providers import get_provider_settings

from .models import MetricReliability, SystemHealth
from .reliability import assess_reliability, calculate_trend
from .provider_metrics import (
    get_provider_capabilities,
    get_provider_priority,
    calculate_provider_health_score,
)
from .performance_metrics import (
    calculate_aggregated_performance,
    calculate_performance_health_score,
)
from .health import build_summary

logger = logging.getLogger(__name__)


class MetricsAggregator:
    """Advanced metrics aggregator with normalization and reliability assessment"""

    def __init__(self):
        self._metric_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._last_aggregation_time = 0
        self._aggregation_cache_ttl = 30
        self._provider_settings = {}

    async def initialize(self):
        try:
            self._provider_settings = get_provider_settings()
            logger.info(
                "Metrics aggregator initialized with %d providers",
                len(self._provider_settings),
            )
        except Exception as e:
            logger.error("Failed to initialize aggregator: %s", e)
            self._provider_settings = []

    def _assess_reliability(
        self, metric_name: str, value: float, timestamp: float
    ) -> MetricReliability:
        return assess_reliability(self._metric_history[metric_name], timestamp)

    def _calculate_trend(self, metric_name: str, window_minutes: int = 10) -> Optional[str]:
        return calculate_trend(self._metric_history[metric_name], window_minutes)

    async def _get_provider_metrics(self) -> Dict[str, Dict[str, Any]]:
        try:
            provider_status = await monitor.get_status()
            current_time = time.time()
            provider_metrics = {}

            for provider_name, status in provider_status.items():
                reliability = self._assess_reliability(
                    f"provider_{provider_name}_status",
                    1.0 if status.get("status") == "healthy" else 0.0,
                    status.get("last_check", current_time),
                )
                trend = self._calculate_trend(f"provider_{provider_name}_status")

                provider_metrics[provider_name] = {
                    "status": status.get("status", "unknown"),
                    "latency_ms": status.get("latency_ms", 0),
                    "error": status.get("error"),
                    "last_check": status.get("last_check"),
                    "reliability": reliability.value,
                    "trend": trend,
                    "metadata": {
                        "provider_type": "llm",
                        "capabilities": get_provider_capabilities(
                            self._provider_settings, provider_name
                        ),
                        "priority_tier": get_provider_priority(
                            self._provider_settings, provider_name
                        ),
                    },
                }

            return provider_metrics

        except Exception as e:
            logger.error("Failed to get provider metrics: %s", e)
            return {}

    async def _get_performance_metrics(self) -> Dict[str, Any]:
        try:
            redis_metrics = await self._get_redis_metrics()
            task_metrics = await self._get_task_metrics()
            cache_metrics = await self._get_cache_metrics()

            return {
                "redis": redis_metrics,
                "tasks": task_metrics,
                "cache": cache_metrics,
                "aggregated": calculate_aggregated_performance(redis_metrics, task_metrics),
            }

        except Exception as e:
            logger.error("Failed to get performance metrics: %s", e)
            return {}

    async def _get_redis_metrics(self) -> Dict[str, Any]:
        try:
            if not cache.redis:
                return {
                    "status": "unavailable",
                    "reliability": MetricReliability.POOR.value,
                }

            info = await cache.redis.info()
            current_time = time.time()
            reliability = self._assess_reliability("redis_info", 1.0, current_time)

            return {
                "memory_usage": info.get("used_memory_human", "unknown"),
                "connected_clients": int(info.get("connected_clients", 0)),
                "keyspace_hits": int(info.get("keyspace_hits", 0)),
                "keyspace_misses": int(info.get("keyspace_misses", 0)),
                "uptime_seconds": int(info.get("uptime_in_seconds", 0)),
                "reliability": reliability.value,
                "timestamp": current_time,
            }

        except Exception as e:
            logger.error("Failed to get Redis metrics: %s", e)
            return {
                "status": "error",
                "error": str(e),
                "reliability": MetricReliability.POOR.value,
            }

    async def _get_task_metrics(self) -> Dict[str, Any]:
        try:
            all_tasks = await task_store.list_tasks()
            current_time = time.time()

            total_tasks = len(all_tasks)
            completed_tasks = len([t for t in all_tasks if t.get("status") == "completed"])
            failed_tasks = len([t for t in all_tasks if t.get("status") == "failed"])
            running_tasks = len([t for t in all_tasks if t.get("status") == "running"])
            queued_tasks = len([t for t in all_tasks if t.get("status") == "queued"])

            completion_times = []
            for task in all_tasks:
                if (
                    task.get("status") == "completed"
                    and "created_at" in task
                    and "updated_at" in task
                ):
                    try:
                        created = datetime.fromisoformat(task["created_at"])
                        updated = datetime.fromisoformat(task["updated_at"])
                        duration = (updated - created).total_seconds()
                        if duration > 0:
                            completion_times.append(duration)
                    except (ValueError, TypeError):
                        continue

            avg_completion_time = statistics.mean(completion_times) if completion_times else 0
            completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            failure_rate = (failed_tasks / total_tasks * 100) if total_tasks > 0 else 0

            reliability = self._assess_reliability("task_metrics", completion_rate, current_time)

            return {
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "failed_tasks": failed_tasks,
                "running_tasks": running_tasks,
                "queued_tasks": queued_tasks,
                "avg_completion_time": round(avg_completion_time, 2),
                "completion_rate": round(completion_rate, 2),
                "failure_rate": round(failure_rate, 2),
                "reliability": reliability.value,
                "timestamp": current_time,
            }

        except Exception as e:
            logger.error("Failed to get task metrics: %s", e)
            return {
                "status": "error",
                "error": str(e),
                "reliability": MetricReliability.POOR.value,
            }

    async def _get_cache_metrics(self) -> Dict[str, Any]:
        try:
            redis_info = await cache.redis.info() if cache.redis else {}
            current_time = time.time()

            hits = int(redis_info.get("keyspace_hits", 0))
            misses = int(redis_info.get("keyspace_misses", 0))
            total_requests = hits + misses
            hit_ratio = (hits / total_requests * 100) if total_requests > 0 else 0

            reliability = self._assess_reliability("cache_hit_ratio", hit_ratio, current_time)

            return {
                "hit_ratio": round(hit_ratio, 2),
                "hits": hits,
                "misses": misses,
                "total_requests": total_requests,
                "memory_usage": redis_info.get("used_memory_human", "unknown"),
                "reliability": reliability.value,
                "timestamp": current_time,
            }

        except Exception as e:
            logger.error("Failed to get cache metrics: %s", e)
            return {
                "status": "error",
                "error": str(e),
                "reliability": MetricReliability.POOR.value,
            }

    async def _get_streaming_metrics(self) -> Dict[str, Any]:
        try:
            all_tasks = await task_store.list_tasks()
            current_time = time.time()

            streaming_tasks = [t for t in all_tasks if t.get("streaming", False)]
            non_streaming_tasks = [t for t in all_tasks if not t.get("streaming", False)]

            def _completion_times(tasks: list) -> list:
                times = []
                for task in tasks:
                    if (
                        task.get("status") == "completed"
                        and "created_at" in task
                        and "updated_at" in task
                    ):
                        try:
                            created = datetime.fromisoformat(task["created_at"])
                            updated = datetime.fromisoformat(task["updated_at"])
                            duration = (updated - created).total_seconds()
                            if duration > 0:
                                times.append(duration)
                        except (ValueError, TypeError):
                            continue
                return times

            streaming_times = _completion_times(streaming_tasks)
            non_streaming_times = _completion_times(non_streaming_tasks)

            streaming_avg = statistics.mean(streaming_times) if streaming_times else 0
            non_streaming_avg = statistics.mean(non_streaming_times) if non_streaming_times else 0

            streaming_rate = (
                (
                    len([t for t in streaming_tasks if t.get("status") == "completed"])
                    / len(streaming_tasks)
                    * 100
                )
                if streaming_tasks
                else 0
            )

            non_streaming_rate = (
                (
                    len([t for t in non_streaming_tasks if t.get("status") == "completed"])
                    / len(non_streaming_tasks)
                    * 100
                )
                if non_streaming_tasks
                else 0
            )

            reliability = self._assess_reliability(
                "streaming_metrics", streaming_rate, current_time
            )

            return {
                "streaming": {
                    "count": len(streaming_tasks),
                    "avg_completion_time": round(streaming_avg, 2),
                    "completion_rate": round(streaming_rate, 2),
                    "failure_rate": (round(100 - streaming_rate, 2) if streaming_tasks else 0),
                },
                "non_streaming": {
                    "count": len(non_streaming_tasks),
                    "avg_completion_time": round(non_streaming_avg, 2),
                    "completion_rate": round(non_streaming_rate, 2),
                    "failure_rate": (
                        round(100 - non_streaming_rate, 2) if non_streaming_tasks else 0
                    ),
                },
                "comparison": {
                    "time_efficiency": (
                        round(non_streaming_avg / streaming_avg, 2) if streaming_avg > 0 else 0
                    ),
                    "reliability_difference": round(abs(streaming_rate - non_streaming_rate), 2),
                },
                "reliability": reliability.value,
                "timestamp": current_time,
            }

        except Exception as e:
            logger.error("Failed to get streaming metrics: %s", e)
            return {
                "status": "error",
                "error": str(e),
                "reliability": MetricReliability.POOR.value,
            }

    async def aggregate_system_metrics(self) -> Dict[str, Any]:
        """Main entry point — returns normalized, frontend-friendly metrics."""
        try:
            current_time = time.time()

            cached = await cache.get("aggregated_metrics")
            if cached and (current_time - cached.get("timestamp", 0)) < self._aggregation_cache_ttl:
                return cached

            provider_metrics = await self._get_provider_metrics()
            performance_metrics = await self._get_performance_metrics()
            streaming_metrics = await self._get_streaming_metrics()
            system_health = await self._calculate_system_health(
                provider_metrics, performance_metrics
            )

            aggregated = {
                "timestamp": current_time,
                "version": "2.0.0",
                "metadata": {
                    "reliability": self._assess_overall_reliability(),
                    "freshness": current_time - self._last_aggregation_time,
                    "sources": ["monitor", "redis", "task_store", "cache"],
                    "normalization": "frontend-friendly",
                },
                "providers": provider_metrics,
                "performance": performance_metrics,
                "streaming": streaming_metrics,
                "health": system_health,
                "summary": build_summary(provider_metrics, performance_metrics, system_health),
            }

            await cache.set("aggregated_metrics", aggregated, expire=self._aggregation_cache_ttl)
            self._last_aggregation_time = current_time

            return aggregated

        except Exception as e:
            logger.error("Failed to aggregate system metrics: %s", e)
            return {
                "error": str(e),
                "timestamp": time.time(),
                "status": "aggregation_failed",
            }

    async def _calculate_system_health(
        self, provider_metrics: Dict[str, Any], performance_metrics: Dict[str, Any]
    ) -> SystemHealth:
        try:
            provider_score = calculate_provider_health_score(provider_metrics)
            performance_score = calculate_performance_health_score(performance_metrics)
            overall_score = (provider_score * 0.6) + (performance_score * 0.4)

            if overall_score >= 90:
                status = "healthy"
            elif overall_score >= 70:
                status = "degraded"
            else:
                status = "critical"

            trend = self._calculate_health_trend()
            reliability = self._assess_reliability("system_health", overall_score, time.time())

            return SystemHealth(
                overall_score=round(overall_score, 1),
                status=status,
                components={
                    "providers": round(provider_score, 1),
                    "performance": round(performance_score, 1),
                },
                trend=trend,
                last_updated=time.time(),
                reliability=reliability,
            )

        except Exception as e:
            logger.error("Failed to calculate system health: %s", e)
            return SystemHealth(
                overall_score=0,
                status="unknown",
                components={},
                trend="unknown",
                last_updated=time.time(),
                reliability=MetricReliability.POOR,
            )

    def _calculate_health_trend(self) -> str:
        trend = self._calculate_trend("system_health")
        if trend == "increasing":
            return "improving"
        elif trend == "decreasing":
            return "degrading"
        return "stable"

    def _assess_overall_reliability(self) -> str:
        provider_fresh = any(
            time.time() - (p.get("last_check", 0) or 0) < 60
            for p in self._metric_history.get("provider_status", [])
        )
        perf_fresh = any(
            time.time() - (m.get("timestamp", 0) or 0) < 60
            for m in self._metric_history.get("performance", [])
        )
        recent_checks = [provider_fresh, perf_fresh]
        if all(recent_checks):
            return "excellent"
        elif any(recent_checks):
            return "good"
        return "poor"


aggregator = MetricsAggregator()
