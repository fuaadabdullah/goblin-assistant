"""Ops health endpoints (mounted under the ops router)."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from .health_checks import (
    _check_chroma,
    _check_cost_tracking,
    _check_mcp,
    _check_raptor,
    _check_sandbox,
)
from .ops_health_pkg import build_ops_health_summary, build_provider_status_payload

ops_health_router = APIRouter()


def _detail_message(prefix: str, error: Exception) -> str:
    message = str(error).strip()
    if message:
        return f"{prefix}: {message}"
    return f"{prefix}: Request failed"


@ops_health_router.get("/health/summary")
async def ops_health_summary() -> Dict[str, Any]:
    from .ops_routes.shared import performance_metrics

    try:
        return await build_ops_health_summary(
            performance_metrics=performance_metrics,
            check_chroma_fn=_check_chroma,
            check_mcp_fn=_check_mcp,
            check_raptor_fn=_check_raptor,
            check_sandbox_fn=_check_sandbox,
            check_cost_tracking_fn=_check_cost_tracking,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=_detail_message("Health summary failed", exc))


@ops_health_router.get("/providers/status")
async def ops_providers_status() -> Dict[str, Any]:
    from .config.providers import get_provider_settings
    from .monitoring import monitor
    from .ops_routes.shared import (
        CircuitBreaker,
        calculate_health_score,
        circuit_breakers,
        performance_metrics,
    )

    try:
        payload = await build_provider_status_payload(
            monitor=monitor,
            get_provider_settings_fn=get_provider_settings,
            circuit_breakers=circuit_breakers,
            circuit_breaker_factory=CircuitBreaker,
            performance_metrics=performance_metrics,
            calculate_health_score_fn=calculate_health_score,
        )
        return {"timestamp": __import__("datetime").datetime.utcnow().isoformat(), **payload}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=_detail_message("Provider status failed", exc))
