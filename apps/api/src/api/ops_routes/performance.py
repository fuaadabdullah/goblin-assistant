from collections import defaultdict
from datetime import datetime
from typing import Any, Dict
import statistics
import time

from fastapi import APIRouter, HTTPException, Query

from ..storage.cache import cache
from ..storage.tasks import task_store
from .shared import performance_metrics

router = APIRouter()


@router.get("/performance/snapshot")
async def performance_snapshot() -> Dict[str, Any]:
    try:
        redis_info = {}
        try:
            if cache.redis:
                redis_info = await cache.redis.info()
        except Exception:
            pass

        cache_hits = int(redis_info.get("keyspace_hits", 0))
        cache_misses = int(redis_info.get("keyspace_misses", 0))
        total_requests = cache_hits + cache_misses
        cache_hit_ratio = round((cache_hits / total_requests * 100) if total_requests > 0 else 0, 2)

        all_metrics = []
        for provider_name in performance_metrics.total_requests.keys():
            metrics = performance_metrics.get_metrics(provider_name)
            if metrics["total_requests"] > 0:
                all_metrics.append(metrics)

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
                "total_requests": total_requests,
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Performance snapshot failed: {str(e)}")


@router.get("/queues/snapshot")
async def queues_snapshot() -> Dict[str, Any]:
    try:
        all_tasks = await task_store.list_tasks()

        status_counts = defaultdict(int)
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
                    (
                        (status_counts.get("completed", 0) / len(all_tasks) * 100)
                        if all_tasks
                        else 0
                    ),
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
                        if t.get("status") == "running"
                        and time.time() - t.get("created_at", 0) > 300
                    ]
                ),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Queue snapshot failed: {str(e)}")


@router.get("/metrics/history")
async def metrics_history(
    provider: str = Query(None, description="Provider name to get history for"),
    metric: str = Query("response_time", description="Metric to get history for"),
    hours: int = Query(1, description="Number of hours to look back"),
) -> Dict[str, Any]:
    try:
        if provider:
            times = performance_metrics.response_times.get(provider, [])
            if not times:
                return {"provider": provider, "metric": metric, "history": []}

            return {
                "provider": provider,
                "metric": metric,
                "history": times[-100:],
                "avg": round(statistics.mean(times), 2) if times else 0,
                "min": round(min(times), 2) if times else 0,
                "max": round(max(times), 2) if times else 0,
            }

        all_history = {}
        for prov_name in performance_metrics.total_requests.keys():
            times = performance_metrics.response_times.get(prov_name, [])
            if times:
                all_history[prov_name] = {
                    "history": times[-50:],
                    "avg": round(statistics.mean(times), 2),
                    "min": round(min(times), 2),
                    "max": round(max(times), 2),
                }

        return {
            "metric": metric,
            "history": all_history,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Metrics history failed: {str(e)}")
