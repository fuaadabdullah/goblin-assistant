"""
Unified health check endpoint for all Goblin Assistant subsystems.

Check primitives live in `health_core.py`; ops endpoints in `ops_health.py`.
This module keeps the public routes and re-exports the old import surface.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Request

from .core.contracts import SuccessEnvelope
from .health_checks import (
    _check_chroma,
    _check_cost_tracking,
    _check_mcp,
    _check_raptor,
    _check_sandbox,
)
from .health_core import (  # noqa: F401 — re-exported for backward compat
    _summarize_provider_health,
    build_health_payload,
    check_api_health,
    check_db_health,
    check_redis_health,
    check_routing_health,
)
from .ops_health import ops_health_router  # noqa: F401 — re-exported for ops_routes

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(
    request: Request = None,  # type: ignore[assignment] — None only when called directly (tests, ops)
) -> Dict[str, Any] | SuccessEnvelope[Dict[str, Any]]:
    """Unified health endpoint covering all subsystems.

    Strategy: Prioritizes fast response times over comprehensive validation.
    Optional components (database, Redis) use graceful degradation patterns.
    Provider monitoring runs asynchronously to avoid blocking health endpoints.
    """
    # Pass the module-level check functions so patches on `api.health.check_*`
    # (used by tests) are honored.
    payload = await build_health_payload(
        routing_check=check_routing_health,
        db_check=check_db_health,
        redis_check=check_redis_health,
        api_check=check_api_health,
    )
    if request is None or request.url.path.startswith("/api/v1/"):
        return SuccessEnvelope(data=payload)
    return payload


@router.get("/health/stream")
async def health_stream(request: Request) -> Dict[str, Any] | SuccessEnvelope[Dict[str, Any]]:
    """Streaming health check endpoint (legacy compatibility)"""
    # For backward compatibility, redirect to main health endpoint
    return await health_check(request)


@router.get("/health/all")
async def health_all() -> Dict[str, Any]:
    """Return a detailed health summary for all subsystems."""
    chroma, mcp, raptor, sandbox, cost = await asyncio.gather(
        _check_chroma(),
        _check_mcp(),
        _check_raptor(),
        _check_sandbox(),
        _check_cost_tracking(),
    )

    overall = "healthy"
    for comp in (chroma, mcp, raptor, sandbox):
        if comp.get("status") != "healthy":
            overall = "degraded"
            break

    return {
        "status": overall,
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "chroma": chroma,
            "mcp": mcp,
            "raptor": raptor,
            "sandbox": sandbox,
            "cost_tracking": cost,
        },
    }


@router.get("/health/chroma/status")
async def health_chroma():
    return await _check_chroma()


@router.get("/health/mcp/status")
async def health_mcp():
    return await _check_mcp()


@router.get("/health/raptor/status")
async def health_raptor():
    return await _check_raptor()


@router.get("/health/sandbox/status")
async def health_sandbox():
    return await _check_sandbox()


@router.get("/health/cost-tracking")
async def health_cost_tracking():
    return await _check_cost_tracking()


@router.get("/health/latency-history/{service}")
async def health_latency_history(service: str):
    return {
        "service": service,
        "status": "unavailable",
        "latency_history": [],
        "message": f"Latency history tracking not implemented for service '{service}'",
    }


@router.get("/health/service-errors/{service}")
async def health_service_errors(service: str):
    return {
        "service": service,
        "status": "unavailable",
        "errors": [],
        "message": f"Service error tracking not implemented for service '{service}'",
    }


@router.post("/health/retest/{service}")
async def health_retest(service: str):
    return {
        "service": service,
        "status": "accepted",
        "retest": "scheduled",
        "message": f"On-demand retest not implemented for service '{service}'",
    }


@router.get("/health/ready")
async def readiness_check() -> Dict[str, Any]:
    """Readiness probe for Fly.io - returns 200 if app is ready to serve traffic."""
    try:
        # Check if we can connect to database (optional)
        db_ready = False
        try:
            from sqlalchemy import text

            from .storage.database import engine

            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            db_ready = True
        except Exception:
            # Database not available - that's OK, app can run without it
            pass

        # Check if Redis is available (optional)
        redis_ready = False
        try:
            from .storage.cache import cache

            if cache._redis:
                await cache._redis.ping()
                redis_ready = True
        except Exception:
            # Redis not available - that's OK, app can run without it
            pass

        # App is ready as long as it can serve basic requests
        # Database and Redis are optional enhancements
        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Application is ready to serve traffic",
            "database": "available" if db_ready else "unavailable",
            "redis": "available" if redis_ready else "unavailable",
        }
    except Exception as e:
        # If there's a critical error in the readiness check itself, return not ready
        return {
            "status": "not ready",
            "timestamp": datetime.utcnow().isoformat(),
            "error": f"Critical readiness check failure: {str(e)}",
        }


@router.get("/health/live")
async def liveness_check() -> Dict[str, Any]:
    """Liveness probe for Fly.io - returns 200 if app is alive."""
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
        "message": "Application is alive",
    }


@router.get("/health/routing")
async def health_routing() -> Dict[str, Any]:
    """Check routing subsystem health"""
    try:
        from .departments import DEPARTMENT_REGISTRY

        providers = DEPARTMENT_REGISTRY.list_ids()
        return {
            "status": "healthy" if len(providers) > 0 else "degraded",
            "providers_available": len(providers),
            "service": "routing",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "service": "routing",
            "timestamp": datetime.utcnow().isoformat(),
        }


@router.get("/health/streaming")
async def health_streaming() -> Dict[str, Any]:
    """Check streaming capability health (alias for /health/stream)"""
    try:
        from .config.providers import DEFAULT_PROVIDERS

        streaming_providers = [p for p in DEFAULT_PROVIDERS if p.get("enabled") and p.get("models")]
        return {
            "status": "healthy" if len(streaming_providers) > 0 else "degraded",
            "streaming_providers": len(streaming_providers),
            "service": "streaming",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "service": "streaming",
            "timestamp": datetime.utcnow().isoformat(),
        }


__all__ = ["router", "ops_health_router"]
