"""Ops health endpoints (mounted under the ops router).

Imports from ops_routes.shared are deferred inside route handlers to avoid
the circular import: health → ops_routes.__init__ → health.
"""

import statistics
import time
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from .health_checks import (
    _check_chroma,
    _check_cost_tracking,
    _check_mcp,
    _check_raptor,
    _check_sandbox,
)
from .health_core import build_health_payload, overall_status_from

ops_health_router = APIRouter()


@ops_health_router.get("/health/summary")
async def ops_health_summary() -> Dict[str, Any]:
    from .ops_routes.shared import performance_metrics

    try:
        base_health = await build_health_payload()
        chroma_health = await _check_chroma()
        mcp_health = await _check_mcp()
        raptor_health = await _check_raptor()
        sandbox_health = await _check_sandbox()
        cost_health = await _check_cost_tracking()

        component_statuses = [
            base_health["status"],
            chroma_health["status"],
            mcp_health["status"],
            raptor_health["status"],
            sandbox_health["status"],
        ]

        overall_status = overall_status_from(component_statuses)

        uptime_seconds = time.time() - performance_metrics.start_time
        uptime_days = int(uptime_seconds // 86400)
        uptime_hours = int((uptime_seconds % 86400) // 3600)
        uptime_minutes = int((uptime_seconds % 3600) // 60)

        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "uptime": {
                "seconds": int(uptime_seconds),
                "formatted": f"{uptime_days}d {uptime_hours}h {uptime_minutes}m",
            },
            "components": {
                "api": base_health["components"]["api"],
                "routing": base_health["components"]["routing"],
                "database": base_health["components"]["database"],
                "redis": base_health["components"]["redis"],
                "providers": base_health["components"]["providers"],
                "security": base_health["components"]["security"],
                "chroma": chroma_health,
                "mcp": mcp_health,
                "raptor": raptor_health,
                "sandbox": sandbox_health,
                "cost_tracking": cost_health,
            },
            "summary": {
                "total_components": len(component_statuses),
                "healthy_components": len([s for s in component_statuses if s == "healthy"]),
                "degraded_components": len([s for s in component_statuses if s == "degraded"]),
                "warning_components": len([s for s in component_statuses if s == "warnings"]),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health summary failed: {str(e)}")


@ops_health_router.get("/providers/status")
async def ops_providers_status() -> Dict[str, Any]:
    from .monitoring import monitor
    from .ops_routes.shared import (
        CircuitBreaker,
        calculate_health_score,
        circuit_breakers,
        performance_metrics,
    )

    try:
        provider_status = await monitor.get_status()
        from .config.providers import get_provider_settings

        provider_settings = get_provider_settings()
        settings_map = {p["name"]: p for p in provider_settings}

        enhanced_status = {}
        for provider_name, status in provider_status.items():
            if provider_name not in circuit_breakers:
                circuit_breakers[provider_name] = CircuitBreaker()
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
                "health_score": calculate_health_score(status, metrics, cb),
            }

        for provider_name, settings in settings_map.items():
            if provider_name not in enhanced_status:
                if provider_name not in circuit_breakers:
                    circuit_breakers[provider_name] = CircuitBreaker()

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
            "timestamp": datetime.utcnow().isoformat(),
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
                            [
                                p["latency_ms"]
                                for p in enhanced_status.values()
                                if p["latency_ms"] > 0
                            ]
                        )
                        if any(p["latency_ms"] > 0 for p in enhanced_status.values())
                        else 0
                    ),
                    2,
                ),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Provider status failed: {str(e)}")
