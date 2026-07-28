from typing import Any, Dict, List

from .models import SystemHealth


def build_summary(
    provider_metrics: Dict[str, Any],
    performance_metrics: Dict[str, Any],
    system_health: SystemHealth,
) -> Dict[str, Any]:
    return {
        "status": system_health.status,
        "health_score": system_health.overall_score,
        "trend": system_health.trend,
        "active_providers": len([p for p in provider_metrics.values() if p["status"] == "healthy"]),
        "total_providers": len(provider_metrics),
        "performance_score": performance_metrics.get("aggregated", {}).get(
            "overall_performance", 0
        ),
        "uptime_estimate": "N/A",
        "recommendations": generate_recommendations(provider_metrics, performance_metrics),
    }


def generate_recommendations(
    provider_metrics: Dict[str, Any], performance_metrics: Dict[str, Any]
) -> List[str]:
    recommendations = []

    unhealthy = [p for p in provider_metrics.values() if p["status"] != "healthy"]
    if unhealthy:
        recommendations.append(f"Check {len(unhealthy)} unhealthy providers")

    perf_score = performance_metrics.get("aggregated", {}).get("overall_performance", 0)
    if perf_score < 70:
        recommendations.append("Investigate performance degradation - check Redis and task queues")

    queued = performance_metrics.get("tasks", {}).get("queued_tasks", 0)
    running = performance_metrics.get("tasks", {}).get("running_tasks", 0)
    if queued > running * 2:
        recommendations.append("Queue is building up - consider scaling task workers")

    return recommendations
