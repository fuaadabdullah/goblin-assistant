import logging
from typing import Any, Dict


logger = logging.getLogger(__name__)


def calculate_aggregated_performance(
    redis_metrics: Dict[str, Any], task_metrics: Dict[str, Any]
) -> Dict[str, float]:
    """Score Redis, task execution, and queue health (each 0–100)."""
    try:
        redis_score = 100
        if redis_metrics.get("status") == "error":
            redis_score = 0
        elif redis_metrics.get("connected_clients", 0) > 100:
            redis_score = 70

        task_score = 100
        failure_rate = task_metrics.get("failure_rate", 0)
        if failure_rate > 20:
            task_score = 40
        elif failure_rate > 10:
            task_score = 70
        elif failure_rate > 5:
            task_score = 85

        queued = task_metrics.get("queued_tasks", 0)
        running = task_metrics.get("running_tasks", 0)
        queue_score = 100
        if queued > running * 2:
            queue_score = 60
        elif queued > running:
            queue_score = 80

        return {
            "redis_performance": round(redis_score, 1),
            "task_performance": round(task_score, 1),
            "queue_health": round(queue_score, 1),
            "overall_performance": round((redis_score + task_score + queue_score) / 3, 1),
        }

    except Exception as e:
        logger.error("Failed to calculate aggregated performance: %s", e)
        return {"overall_performance": 0}


def calculate_performance_health_score(performance_metrics: Dict[str, Any]) -> float:
    """Weighted score: 40% Redis, 40% task execution, 20% queue health."""
    aggregated = performance_metrics.get("aggregated", {})
    redis_score = aggregated.get("redis_performance", 50)
    task_score = aggregated.get("task_performance", 50)
    queue_score = aggregated.get("queue_health", 50)
    return (redis_score * 0.4) + (task_score * 0.4) + (queue_score * 0.2)
