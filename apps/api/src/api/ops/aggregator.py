"""
Enhanced Metrics Aggregator for Operational Endpoints
Normalizes internal system metrics into frontend-friendly, operator-ready responses
"""

import asyncio
import time
import statistics
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from enum import Enum
import logging

from ..storage.cache import cache
from ..storage.tasks import task_store
from ..monitoring import monitor
from ..config.providers import get_provider_settings

logger = logging.getLogger(__name__)


class MetricReliability(Enum):
    """Reliability levels for metrics based on data freshness and completeness"""

    EXCELLENT = "excellent"  # Fresh data, complete history
    GOOD = "good"  # Recent data, minor gaps
    FAIR = "fair"  # Older data, some gaps
    POOR = "poor"  # Stale data, significant gaps
    UNKNOWN = "unknown"  # No data available


@dataclass
class AggregatedMetric:
    """Normalized metric with reliability and metadata"""

    name: str
    value: float
    unit: str
    reliability: MetricReliability
    timestamp: float
    source: str
    description: str
    trend: Optional[str] = None  # "increasing", "decreasing", "stable"


@dataclass
class SystemHealth:
    """Comprehensive system health with trend analysis"""

    overall_score: float
    status: str  # "healthy", "degraded", "critical"
    components: Dict[str, float]
    trend: str
    last_updated: float
    reliability: MetricReliability


class MetricsAggregator:
    """Advanced metrics aggregator with normalization and reliability assessment"""

    def __init__(self):
        self._metric_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._last_aggregation_time = 0
        self._aggregation_cache_ttl = 30  # seconds
        self._provider_settings = {}

    async def initialize(self):
        """Initialize aggregator with provider settings"""
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
        """Assess reliability of a metric based on freshness and history"""
        if metric_name not in self._metric_history:
            return MetricReliability.UNKNOWN

        history = self._metric_history[metric_name]
        if not history:
            return MetricReliability.UNKNOWN

        # Check data freshness
        time_diff = time.time() - timestamp
        if time_diff > 300:  # 5 minutes
            return MetricReliability.POOR
        elif time_diff > 60:  # 1 minute
            return MetricReliability.FAIR
        elif time_diff > 10:  # 10 seconds
            return MetricReliability.GOOD

        # Check data completeness
        recent_count = sum(1 for h in history if time.time() - h["timestamp"] < 60)
        if recent_count >= 5:
            return MetricReliability.EXCELLENT
        elif recent_count >= 2:
            return MetricReliability.GOOD
        else:
            return MetricReliability.FAIR

    def _calculate_trend(
        self, metric_name: str, window_minutes: int = 10
    ) -> Optional[str]:
        """Calculate trend direction for a metric"""
        if metric_name not in self._metric_history:
            return None

        history = self._metric_history[metric_name]
        cutoff = time.time() - (window_minutes * 60)

        recent_values = [h["value"] for h in history if h["timestamp"] > cutoff]
        if len(recent_values) < 3:
            return None

        # Simple linear regression for trend
        n = len(recent_values)
        x_values = list(range(n))
        y_values = recent_values

        # Calculate slope
        x_mean = sum(x_values) / n
        y_mean = sum(y_values) / n

        numerator = sum(
            (x_values[i] - x_mean) * (y_values[i] - y_mean) for i in range(n)
        )
        denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return "stable"

        slope = numerator / denominator

        # Determine trend direction
        if abs(slope) < 0.01:  # Threshold for "stable"
            return "stable"
        elif slope > 0:
            return "increasing"
        else:
            return "decreasing"

    async def _get_provider_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get normalized provider metrics with reliability assessment"""
        try:
            provider_status = await monitor.get_status()
            current_time = time.time()

            provider_metrics = {}

            for provider_name, status in provider_status.items():
                # Calculate reliability
                reliability = self._assess_reliability(
                    f"provider_{provider_name}_status",
                    1.0 if status.get("status") == "healthy" else 0.0,
                    status.get("last_check", current_time),
                )

                # Calculate trend
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
                        "capabilities": self._get_provider_capabilities(provider_name),
                        "priority_tier": self._get_provider_priority(provider_name),
                    },
                }

            return provider_metrics

        except Exception as e:
            logger.error("Failed to get provider metrics: %s", e)
            return {}

    def _get_provider_capabilities(self, provider_name: str) -> List[str]:
        """Get capabilities for a provider"""
        for provider in self._provider_settings:
            if provider["name"] == provider_name:
                return provider.get("capabilities", [])
        return []

    def _get_provider_priority(self, provider_name: str) -> int:
        """Get priority tier for a provider"""
        for provider in self._provider_settings:
            if provider["name"] == provider_name:
                return provider.get("priority_tier", 0)
        return 0

    async def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get aggregated performance metrics"""
        try:
            # Get Redis metrics
            redis_metrics = await self._get_redis_metrics()

            # Get task metrics
            task_metrics = await self._get_task_metrics()

            # Get cache metrics
            cache_metrics = await self._get_cache_metrics()

            return {
                "redis": redis_metrics,
                "tasks": task_metrics,
                "cache": cache_metrics,
                "aggregated": self._calculate_aggregated_performance(
                    redis_metrics, task_metrics
                ),
            }

        except Exception as e:
            logger.error("Failed to get performance metrics: %s", e)
            return {}

    async def _get_redis_metrics(self) -> Dict[str, Any]:
        """Get Redis performance metrics"""
        try:
            if not cache.redis:
                return {
                    "status": "unavailable",
                    "reliability": MetricReliability.POOR.value,
                }

            info = await cache.redis.info()
            current_time = time.time()

            # Calculate reliability based on info freshness
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
        """Get task processing metrics"""
        try:
            all_tasks = await task_store.list_tasks()
            current_time = time.time()

            # Calculate task statistics
            total_tasks = len(all_tasks)
            completed_tasks = len(
                [t for t in all_tasks if t.get("status") == "completed"]
            )
            failed_tasks = len([t for t in all_tasks if t.get("status") == "failed"])
            running_tasks = len([t for t in all_tasks if t.get("status") == "running"])
            queued_tasks = len([t for t in all_tasks if t.get("status") == "queued"])

            # Calculate completion times
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

            avg_completion_time = (
                statistics.mean(completion_times) if completion_times else 0
            )
            completion_rate = (
                (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            )
            failure_rate = (failed_tasks / total_tasks * 100) if total_tasks > 0 else 0

            reliability = self._assess_reliability(
                "task_metrics", completion_rate, current_time
            )

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
        """Get cache performance metrics"""
        try:
            redis_info = await cache.redis.info() if cache.redis else {}
            current_time = time.time()

            hits = int(redis_info.get("keyspace_hits", 0))
            misses = int(redis_info.get("keyspace_misses", 0))
            total_requests = hits + misses
            hit_ratio = (hits / total_requests * 100) if total_requests > 0 else 0

            reliability = self._assess_reliability(
                "cache_hit_ratio", hit_ratio, current_time
            )

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

    def _calculate_aggregated_performance(
        self, redis_metrics: Dict[str, Any], task_metrics: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate aggregated performance scores"""
        try:
            # Redis performance score (0-100)
            redis_score = 100
            if redis_metrics.get("status") == "error":
                redis_score = 0
            elif redis_metrics.get("connected_clients", 0) > 100:
                redis_score = 70  # High client count indicates stress

            # Task performance score (0-100)
            task_score = 100
            failure_rate = task_metrics.get("failure_rate", 0)
            if failure_rate > 20:
                task_score = 40
            elif failure_rate > 10:
                task_score = 70
            elif failure_rate > 5:
                task_score = 85

            # Queue health score (0-100)
            queued_tasks = task_metrics.get("queued_tasks", 0)
            running_tasks = task_metrics.get("running_tasks", 0)
            queue_score = 100
            if queued_tasks > running_tasks * 2:
                queue_score = 60  # Queue building up
            elif queued_tasks > running_tasks:
                queue_score = 80

            return {
                "redis_performance": round(redis_score, 1),
                "task_performance": round(task_score, 1),
                "queue_health": round(queue_score, 1),
                "overall_performance": round(
                    (redis_score + task_score + queue_score) / 3, 1
                ),
            }

        except Exception as e:
            logger.error("Failed to calculate aggregated performance: %s", e)
            return {"overall_performance": 0}

    async def _get_streaming_metrics(self) -> Dict[str, Any]:
        """Get streaming vs non-streaming metrics"""
        try:
            all_tasks = await task_store.list_tasks()
            current_time = time.time()

            # Categorize tasks by streaming
            streaming_tasks = [t for t in all_tasks if t.get("streaming", False)]
            non_streaming_tasks = [
                t for t in all_tasks if not t.get("streaming", False)
            ]

            # Calculate streaming metrics
            streaming_completion_times = []
            for task in streaming_tasks:
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
                            streaming_completion_times.append(duration)
                    except (ValueError, TypeError):
                        continue

            streaming_avg_time = (
                statistics.mean(streaming_completion_times)
                if streaming_completion_times
                else 0
            )
            streaming_completion_rate = (
                (
                    len([t for t in streaming_tasks if t.get("status") == "completed"])
                    / len(streaming_tasks)
                    * 100
                )
                if streaming_tasks
                else 0
            )

            # Calculate non-streaming metrics
            non_streaming_completion_times = []
            for task in non_streaming_tasks:
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
                            non_streaming_completion_times.append(duration)
                    except (ValueError, TypeError):
                        continue

            non_streaming_avg_time = (
                statistics.mean(non_streaming_completion_times)
                if non_streaming_completion_times
                else 0
            )
            non_streaming_completion_rate = (
                (
                    len(
                        [
                            t
                            for t in non_streaming_tasks
                            if t.get("status") == "completed"
                        ]
                    )
                    / len(non_streaming_tasks)
                    * 100
                )
                if non_streaming_tasks
                else 0
            )

            reliability = self._assess_reliability(
                "streaming_metrics", streaming_completion_rate, current_time
            )

            return {
                "streaming": {
                    "count": len(streaming_tasks),
                    "avg_completion_time": round(streaming_avg_time, 2),
                    "completion_rate": round(streaming_completion_rate, 2),
                    "failure_rate": round(100 - streaming_completion_rate, 2)
                    if streaming_tasks
                    else 0,
                },
                "non_streaming": {
                    "count": len(non_streaming_tasks),
                    "avg_completion_time": round(non_streaming_avg_time, 2),
                    "completion_rate": round(non_streaming_completion_rate, 2),
                    "failure_rate": round(100 - non_streaming_completion_rate, 2)
                    if non_streaming_tasks
                    else 0,
                },
                "comparison": {
                    "time_efficiency": round(
                        non_streaming_avg_time / streaming_avg_time, 2
                    )
                    if streaming_avg_time > 0
                    else 0,
                    "reliability_difference": round(
                        abs(streaming_completion_rate - non_streaming_completion_rate),
                        2,
                    ),
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
        """Main aggregation method - returns normalized, frontend-friendly metrics"""
        try:
            current_time = time.time()

            # Check cache for recent aggregation
            cached = await cache.get("aggregated_metrics")
            if (
                cached
                and (current_time - cached.get("timestamp", 0))
                < self._aggregation_cache_ttl
            ):
                return cached

            # Get all metric categories
            provider_metrics = await self._get_provider_metrics()
            performance_metrics = await self._get_performance_metrics()
            streaming_metrics = await self._get_streaming_metrics()

            # Calculate overall system health
            system_health = await self._calculate_system_health(
                provider_metrics, performance_metrics
            )

            # Build aggregated response
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
                "summary": self._build_summary(
                    provider_metrics, performance_metrics, system_health
                ),
            }

            # Cache the result
            await cache.set(
                "aggregated_metrics", aggregated, expire=self._aggregation_cache_ttl
            )
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
        """Calculate comprehensive system health with trend analysis"""
        try:
            # Calculate component scores
            provider_score = self._calculate_provider_health_score(provider_metrics)
            performance_score = self._calculate_performance_health_score(
                performance_metrics
            )

            # Weighted overall score
            overall_score = (provider_score * 0.6) + (performance_score * 0.4)

            # Determine status
            if overall_score >= 90:
                status = "healthy"
            elif overall_score >= 70:
                status = "degraded"
            else:
                status = "critical"

            # Calculate trend
            trend = self._calculate_health_trend(overall_score)

            # Assess reliability
            reliability = self._assess_reliability(
                "system_health", overall_score, time.time()
            )

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

    def _calculate_provider_health_score(
        self, provider_metrics: Dict[str, Any]
    ) -> float:
        """Calculate health score for providers"""
        if not provider_metrics:
            return 50  # Neutral score if no providers

        healthy_count = sum(
            1 for p in provider_metrics.values() if p["status"] == "healthy"
        )
        total_count = len(provider_metrics)

        base_score = (healthy_count / total_count) * 100

        # Adjust for reliability
        reliability_scores = [
            100
            if p["reliability"] == "excellent"
            else 75
            if p["reliability"] == "good"
            else 50
            if p["reliability"] == "fair"
            else 25
            for p in provider_metrics.values()
        ]
        reliability_score = (
            statistics.mean(reliability_scores) if reliability_scores else 50
        )

        return (base_score * 0.7) + (reliability_score * 0.3)

    def _calculate_performance_health_score(
        self, performance_metrics: Dict[str, Any]
    ) -> float:
        """Calculate health score for performance metrics"""
        aggregated = performance_metrics.get("aggregated", {})

        redis_score = aggregated.get("redis_performance", 50)
        task_score = aggregated.get("task_performance", 50)
        queue_score = aggregated.get("queue_health", 50)

        return (redis_score * 0.4) + (task_score * 0.4) + (queue_score * 0.2)

    def _calculate_health_trend(self, current_score: float) -> str:
        """Calculate health trend based on historical data"""
        trend = self._calculate_trend("system_health")
        if trend == "increasing":
            return "improving"
        elif trend == "decreasing":
            return "degrading"
        else:
            return "stable"

    def _assess_overall_reliability(self) -> str:
        """Assess overall reliability of the aggregated metrics"""
        # Check if we have recent data from all sources
        recent_checks = []

        # Check provider metrics freshness
        provider_fresh = any(
            time.time() - (p.get("last_check", 0) or 0) < 60
            for p in self._metric_history.get("provider_status", [])
        )
        recent_checks.append(provider_fresh)

        # Check performance metrics freshness
        perf_fresh = any(
            time.time() - (m.get("timestamp", 0) or 0) < 60
            for m in self._metric_history.get("performance", [])
        )
        recent_checks.append(perf_fresh)

        # Determine overall reliability
        if all(recent_checks):
            return "excellent"
        elif any(recent_checks):
            return "good"
        else:
            return "poor"

    def _build_summary(
        self,
        provider_metrics: Dict[str, Any],
        performance_metrics: Dict[str, Any],
        system_health: SystemHealth,
    ) -> Dict[str, Any]:
        """Build a summary of the system state"""
        return {
            "status": system_health.status,
            "health_score": system_health.overall_score,
            "trend": system_health.trend,
            "active_providers": len(
                [p for p in provider_metrics.values() if p["status"] == "healthy"]
            ),
            "total_providers": len(provider_metrics),
            "performance_score": performance_metrics.get("aggregated", {}).get(
                "overall_performance", 0
            ),
            "uptime_estimate": "N/A",  # Would need system start time
            "recommendations": self._generate_recommendations(
                provider_metrics, performance_metrics
            ),
        }

    def _generate_recommendations(
        self, provider_metrics: Dict[str, Any], performance_metrics: Dict[str, Any]
    ) -> List[str]:
        """Generate actionable recommendations based on metrics"""
        recommendations = []

        # Provider recommendations
        unhealthy_providers = [
            p for p in provider_metrics.values() if p["status"] != "healthy"
        ]
        if unhealthy_providers:
            recommendations.append(
                f"Check {len(unhealthy_providers)} unhealthy providers"
            )

        # Performance recommendations
        perf_score = performance_metrics.get("aggregated", {}).get(
            "overall_performance", 0
        )
        if perf_score < 70:
            recommendations.append(
                "Investigate performance degradation - check Redis and task queues"
            )

        # Queue recommendations
        queued_tasks = performance_metrics.get("tasks", {}).get("queued_tasks", 0)
        running_tasks = performance_metrics.get("tasks", {}).get("running_tasks", 0)
        if queued_tasks > running_tasks * 2:
            recommendations.append(
                "Queue is building up - consider scaling task workers"
            )

        return recommendations


# Global aggregator instance
aggregator = MetricsAggregator()
