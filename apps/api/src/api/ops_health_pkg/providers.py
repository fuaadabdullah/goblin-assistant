"""Provider-status aggregation helpers for ops health."""

from __future__ import annotations

import statistics
from typing import Any, Dict


async def build_provider_status_payload(
    *,
    monitor: Any,
    get_provider_settings_fn,
    circuit_breakers: Dict[str, Any],
    circuit_breaker_factory,
    performance_metrics: Any,
    calculate_health_score_fn,
) -> Dict[str, Any]:
    provider_status = await monitor.get_status()
    provider_settings = get_provider_settings_fn()
    settings_map = {p["name"]: p for p in provider_settings}

    enhanced_status = {}
    for provider_name, status in provider_status.items():
        if provider_name not in circuit_breakers:
            circuit_breakers[provider_name] = circuit_breaker_factory()
        cb = circuit_breakers[provider_name]
        metrics = performance_metrics.get_metrics(provider_name)
        settings = settings_map.get(provider_name, {})

        enhanced_status[provider_name] = {
            "name": provider_name,
            "status": status.get("status", "unknown"),
            "last_check": status.get("last_check"),
            "latency_ms": status.get("latency_ms", 0),
            "error": status.get("error"),
            "capabilities": settings.get("capabilities", []),
            "models": settings.get("models", []),
            "priority_tier": settings.get("priority_tier", 0),
            "circuit_breaker": cb.get_status(),
            "performance": metrics,
            "health_score": calculate_health_score_fn(status, metrics, cb),
        }

    for provider_name, settings in settings_map.items():
        if provider_name not in enhanced_status:
            if provider_name not in circuit_breakers:
                circuit_breakers[provider_name] = circuit_breaker_factory()

            cb = circuit_breakers[provider_name]
            metrics = performance_metrics.get_metrics(provider_name)

            enhanced_status[provider_name] = {
                "name": provider_name,
                "status": "unknown",
                "last_check": None,
                "latency_ms": 0,
                "error": "Not yet checked",
                "capabilities": settings.get("capabilities", []),
                "models": settings.get("models", []),
                "priority_tier": settings.get("priority_tier", 0),
                "circuit_breaker": cb.get_status(),
                "performance": metrics,
                "health_score": 0,
            }

    return {
        "providers": enhanced_status,
        "summary": {
            "total_providers": len(enhanced_status),
            "healthy_providers": len(
                [p for p in enhanced_status.values() if p["status"] == "healthy"]
            ),
            "unhealthy_providers": len(
                [p for p in enhanced_status.values() if p["status"] != "healthy"]
            ),
            "open_circuit_breakers": len(
                [p for p in enhanced_status.values() if p["circuit_breaker"]["state"] == "OPEN"]
            ),
            "avg_latency": round(
                (
                    statistics.mean(
                        [p["latency_ms"] for p in enhanced_status.values() if p["latency_ms"] > 0]
                    )
                    if any(p["latency_ms"] > 0 for p in enhanced_status.values())
                    else 0
                ),
                2,
            ),
        },
    }
