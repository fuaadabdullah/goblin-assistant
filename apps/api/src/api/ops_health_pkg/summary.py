"""Summary aggregation helpers for ops health."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Dict

from ..health_core import build_health_payload, overall_status_from


async def build_ops_health_summary(
    *,
    performance_metrics: Any,
    check_vector_store_fn=None,
    check_mcp_fn,
    check_raptor_fn,
    check_sandbox_fn,
    check_cost_tracking_fn,
    build_health_payload_fn=build_health_payload,
    # Backward-compat alias — callers that still pass check_chroma_fn= work.
    check_chroma_fn=None,
) -> Dict[str, Any]:
    _vector_store_fn = check_vector_store_fn or check_chroma_fn
    if _vector_store_fn is None:
        from ..health_checks import _check_vector_store

        _vector_store_fn = _check_vector_store

    base_health = await build_health_payload_fn()
    vector_store_health = await _vector_store_fn()
    mcp_health = await check_mcp_fn()
    raptor_health = await check_raptor_fn()
    sandbox_health = await check_sandbox_fn()
    cost_health = await check_cost_tracking_fn()

    component_statuses = [
        base_health["status"],
        vector_store_health["status"],
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
            "vector_store": vector_store_health,
            "mcp": mcp_health,
            "raptor": raptor_health,
            "sandbox": sandbox_health,
            "cost_tracking": cost_health,
        },
        "summary": {
            "total_components": len(component_statuses),
            "healthy_components": len([s for s in component_statuses if s == "healthy"]),
            "unhealthy_components": len([s for s in component_statuses if s == "unhealthy"]),
            "degraded_components": len([s for s in component_statuses if s == "degraded"]),
            "warning_components": len([s for s in component_statuses if s == "warnings"]),
        },
    }
