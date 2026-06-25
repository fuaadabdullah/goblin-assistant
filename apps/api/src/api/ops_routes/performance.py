from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query

from ..ops.performance_metrics import (
    compute_performance_snapshot,
    compute_queues_snapshot,
    performance_metrics,
)
from ..storage.cache import cache
from ..storage.tasks import task_store

router = APIRouter()


def _detail_message(prefix: str, error: Exception) -> str:
    message = str(error).strip()
    if message:
        return f"{prefix}: {message}"
    return f"{prefix}: Request failed"


@router.get("/performance/snapshot")
async def performance_snapshot() -> Dict[str, Any]:
    try:
        result = await compute_performance_snapshot(cache, task_store)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=_detail_message("Performance snapshot failed", e),
        )


@router.get("/queues/snapshot")
async def queues_snapshot() -> Dict[str, Any]:
    try:
        result = await compute_queues_snapshot(task_store)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=_detail_message("Queue snapshot failed", e),
        )


@router.get("/metrics/history")
async def metrics_history(
    provider: str = Query(None, description="Provider name to get history for"),
    metric: str = Query("response_time", description="Metric to get history for"),
    hours: int = Query(1, description="Number of hours to look back"),
) -> Dict[str, Any]:
    import statistics
    from datetime import datetime

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
        for prov_name in performance_metrics.total_requests:
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
        raise HTTPException(status_code=500, detail=_detail_message("Metrics history failed", e))
