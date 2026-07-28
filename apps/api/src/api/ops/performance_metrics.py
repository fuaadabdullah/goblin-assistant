"""Performance metrics domain model for tracking provider response times and errors."""

import statistics
import time
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List


class PerformanceMetrics:
    """Tracks in-memory performance metrics per provider."""

    def __init__(self):
        self.response_times: Dict[str, List[float]] = defaultdict(list)
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.total_requests: Dict[str, int] = defaultdict(int)
        self.start_time = time.time()

    def record_request(self, provider: str, response_time: float, success: bool):
        self.total_requests[provider] += 1
        self.response_times[provider].append(response_time)

        if len(self.response_times[provider]) > 100:
            self.response_times[provider] = self.response_times[provider][-100:]

        if not success:
            self.error_counts[provider] += 1

    def get_metrics(self, provider: str) -> Dict[str, Any]:
        times = self.response_times[provider]
        total = self.total_requests[provider]
        errors = self.error_counts[provider]

        if not times:
            return {
                "avg_response_time": 0,
                "min_response_time": 0,
                "max_response_time": 0,
                "p95_response_time": 0,
                "error_rate": 0,
                "total_requests": total,
                "error_count": errors,
            }

        return {
            "avg_response_time": round(statistics.mean(times), 2),
            "min_response_time": round(min(times), 2),
            "max_response_time": round(max(times), 2),
            "p95_response_time": (
                round(statistics.quantiles(times, n=20)[-1], 2)
                if len(times) > 20
                else round(max(times), 2)
            ),
            "error_rate": round((errors / total * 100) if total > 0 else 0, 2),
            "total_requests": total,
            "error_count": errors,
        }


performance_metrics = PerformanceMetrics()


# ----- Snapshot / aggregation helpers extracted from route handlers -----


async def compute_performance_snapshot(
    cache, task_store, metrics: PerformanceMetrics | None = None
) -> Dict[str, Any]:
    """Aggregate performance data into a single snapshot dict."""
    pm = metrics or performance_metrics

    redis_info = {}
    try:
        if cache.redis:
            redis_info = await cache.redis.info()
    except Exception:
        pass

    cache_hits = int(redis_info.get("keyspace_hits", 0))
    cache_misses = int(redis_info.get("keyspace_misses", 0))
    total_reqs = cache_hits + cache_misses
    cache_hit_ratio = round((cache_hits / total_reqs * 100) if total_reqs > 0 else 0, 2)

    all_metrics = []
    for provider_name in pm.total_requests:
        m = pm.get_metrics(provider_name)
        if m["total_requests"] > 0:
            all_metrics.append(m)

    avg_response_time = round(
        (statistics.mean([m["avg_response_time"] for m in all_metrics]) if all_metrics else 0),
        2,
    )
    avg_error_rate = round(
        (statistics.mean([m["error_rate"] for m in all_metrics]) if all_metrics else 0),
        2,
    )

    all_tasks = await task_store.list_tasks()
    task_stats = {
        "total_tasks": len(all_tasks),
        "completed_tasks": len([t for t in all_tasks if t.get("status") == "completed"]),
        "failed_tasks": len([t for t in all_tasks if t.get("status") == "failed"]),
        "running_tasks": len([t for t in all_tasks if t.get("status") == "running"]),
        "queued_tasks": len([t for t in all_tasks if t.get("status") == "queued"]),
    }

    streaming_tasks = len([t for t in all_tasks if t.get("streaming", False)])
    non_streaming_tasks = task_stats["total_tasks"] - streaming_tasks

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "cache": {
            "hit_ratio": cache_hit_ratio,
            "hits": cache_hits,
            "misses": cache_misses,
            "total_requests": total_reqs,
            "memory_usage": redis_info.get("used_memory_human", "unknown"),
            "connected_clients": redis_info.get("connected_clients", "unknown"),
        },
        "performance": {
            "avg_response_time": avg_response_time,
            "avg_error_rate": avg_error_rate,
            "total_requests": sum(m["total_requests"] for m in all_metrics),
            "total_errors": sum(m["error_count"] for m in all_metrics),
        },
        "tasks": task_stats,
        "usage": {
            "streaming_tasks": streaming_tasks,
            "non_streaming_tasks": non_streaming_tasks,
            "streaming_percentage": round(
                (
                    (streaming_tasks / task_stats["total_tasks"] * 100)
                    if task_stats["total_tasks"] > 0
                    else 0
                ),
                2,
            ),
        },
    }


async def compute_queues_snapshot(task_store) -> Dict[str, Any]:
    """Aggregate queue/task data into a snapshot dict."""
    all_tasks = await task_store.list_tasks()

    status_counts: Dict[str, int] = defaultdict(int)
    for task in all_tasks:
        status = task.get("status", "unknown")
        status_counts[status] += 1

    recent_cutoff = time.time() - (24 * 3600)
    recent_tasks = [t for t in all_tasks if t.get("created_at", 0) > recent_cutoff]

    completion_times = []
    for task in all_tasks:
        if task.get("status") == "completed" and "created_at" in task and "updated_at" in task:
            try:
                created_str = task["created_at"]
                updated_str = task["updated_at"]
                if created_str.endswith("Z"):
                    created_str = created_str.replace("Z", "+00:00")
                if updated_str.endswith("Z"):
                    updated_str = updated_str.replace("Z", "+00:00")

                created = datetime.fromisoformat(created_str)
                updated = datetime.fromisoformat(updated_str)
                duration = (updated - created).total_seconds()
                if duration > 0:
                    completion_times.append(duration)
            except (ValueError, TypeError):
                continue

    avg_completion_time = round(statistics.mean(completion_times), 2) if completion_times else 0

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "queue_status": {
            "total_tasks": len(all_tasks),
            "recent_tasks_24h": len(recent_tasks),
            "active_tasks": status_counts.get("running", 0) + status_counts.get("queued", 0),
            "completed_tasks": status_counts.get("completed", 0),
            "failed_tasks": status_counts.get("failed", 0),
            "cancelled_tasks": status_counts.get("cancelled", 0),
        },
        "task_breakdown": dict(status_counts),
        "performance": {
            "avg_completion_time": avg_completion_time,
            "completion_rate": round(
                ((status_counts.get("completed", 0) / len(all_tasks) * 100) if all_tasks else 0),
                2,
            ),
            "failure_rate": round(
                ((status_counts.get("failed", 0) / len(all_tasks) * 100) if all_tasks else 0),
                2,
            ),
        },
        "queue_health": {
            "healthy": len(all_tasks) < 1000,
            "backlog_size": status_counts.get("queued", 0),
            "stuck_tasks": len(
                [
                    t
                    for t in all_tasks
                    if t.get("status") == "running" and time.time() - t.get("created_at", 0) > 300
                ]
            ),
        },
    }
