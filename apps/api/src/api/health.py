"""
Unified health check endpoint for all Goblin Assistant subsystems.
Consolidates health checks from main.py, routing_router.py, and api_router.py.
"""

import asyncio
import os
import statistics
import time
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request

from ._version import get_version
from .core.contracts import SuccessEnvelope
from .health_checks import (
    _check_chroma,
    _check_cost_tracking,
    _check_mcp,
    _check_raptor,
    _check_sandbox,
)

router = APIRouter(tags=["health"])

# ── Ops sub-router (was in ops_routes/health.py) ──────────────────────────
# Imports from ops_routes.shared are deferred inside route handlers to avoid
# the circular import: health → ops_routes.__init__ → health.

ops_health_router = APIRouter()


async def check_routing_health() -> Dict[str, Any]:
    """Check routing system health"""
    try:
        # Import here to avoid circular imports
        from .routing_router import top_providers_for

        providers = top_providers_for("chat")
        return {
            "status": "healthy",
            "providers_available": len(providers),
            "routing_system": "active",
        }
    except Exception as e:
        return {"status": "degraded", "error": str(e), "routing_system": "fallback"}


async def check_db_health() -> Dict[str, Any]:
    """Check database connectivity health"""
    try:
        from sqlalchemy import text

        from .storage.database import engine

        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "healthy", "connection": "available"}
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": f"Database connection failed: {type(e).__name__}: {e}",
        }


async def check_redis_health() -> Dict[str, Any]:
    """Check Redis connectivity and performance health"""
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return {"status": "unconfigured", "error": "REDIS_URL not set"}

    try:
        import redis.asyncio as _redis

        kwargs: Dict[str, Any] = {
            "encoding": "utf-8",
            "decode_responses": True,
            "socket_connect_timeout": 5,
            "socket_timeout": 5,
        }
        if redis_url.startswith("rediss://"):
            kwargs["ssl_cert_reqs"] = None

        client = _redis.from_url(redis_url, **kwargs)
        try:
            await client.ping()
            test_key = "health_check_test"
            await client.set(test_key, "test_value", ex=10)
            value = await client.get(test_key)
            await client.delete(test_key)
            if value == "test_value":
                info = await client.info()
                return {
                    "status": "healthy",
                    "connection": "available",
                    "memory_used": info.get("used_memory_human", "unknown"),
                    "connected_clients": info.get("connected_clients", "unknown"),
                    "uptime_days": info.get("uptime_in_days", "unknown"),
                }
            return {"status": "degraded", "error": "Redis operations failed"}
        finally:
            await client.aclose()

    except Exception as e:
        return {"status": "unhealthy", "error": f"Redis connection failed: {str(e)}"}


async def check_api_health() -> Dict[str, Any]:
    """Check API system health"""
    try:
        # Basic API health check - could be expanded
        return {"status": "healthy", "endpoints": "responsive"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def _summarize_provider_health(provider_status: Dict[str, Dict[str, Any]]) -> str:
    if not provider_status:
        return "degraded"

    statuses = {provider.get("status") for provider in provider_status.values()}
    if statuses <= {"healthy", "unknown", "billing_issue"}:
        return "healthy"
    if "healthy" in statuses:
        return "warnings"
    return "degraded"


@router.get("/health")
async def health_check(request: Request) -> Dict[str, Any] | SuccessEnvelope[Dict[str, Any]]:
    """Unified health endpoint covering all subsystems.

    Strategy: Prioritizes fast response times over comprehensive validation.
    Optional components (database, Redis) use graceful degradation patterns.
    Provider monitoring runs asynchronously to avoid blocking health endpoints.
    """
    # Run all health checks concurrently for optimal performance
    routing_health, db_health, redis_health, api_health = await asyncio.gather(
        check_routing_health(),
        check_db_health(),
        check_redis_health(),
        check_api_health(),
    )

    # Get provider status from the authoritative provider health monitor
    try:
        from .services.provider_health import health_monitor

        provider_status = health_monitor.get_all_status(include_hidden=False)
        provider_health = {
            "status": _summarize_provider_health(provider_status),
            "providers_checked": len(provider_status),
            "details": provider_status,
        }
    except Exception as e:
        provider_health = {"status": "degraded", "error": str(e)}

    # Get security configuration status
    try:
        from .security_config import SecurityConfig

        security_warnings = SecurityConfig.validate_config()
        security_status = {
            "status": "healthy" if len(security_warnings) == 0 else "warnings",
            "warnings": security_warnings,
            "debug_mode": SecurityConfig.DEBUG,
            "cors_configured": len(SecurityConfig.ALLOWED_ORIGINS) > 0,
        }
    except Exception as e:
        security_status = {"status": "unknown", "error": str(e)}

    # Determine overall status
    component_statuses = [
        routing_health["status"],
        db_health["status"],
        redis_health["status"],
        api_health["status"],
        provider_health["status"],
        security_status["status"],
    ]
    overall_status = (
        "healthy"
        if all(status == "healthy" for status in component_statuses)
        else "degraded"
        if "degraded" in component_statuses
        else "warnings"
    )

    payload = {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "version": get_version(),
        "components": {
            "api": api_health,
            "routing": routing_health,
            "database": db_health,
            "redis": redis_health,
            "providers": provider_health,
            "security": security_status,
        },
    }
    if request.url.path.startswith("/api/v1/"):
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
        from .routing_router import top_providers_for

        providers = top_providers_for("chat")
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


# ── Ops health endpoints (moved from ops_routes/health.py) ────────────────


@ops_health_router.get("/health/summary")
async def ops_health_summary() -> Dict[str, Any]:
    from .ops_routes.shared import performance_metrics

    try:
        base_health = await health_check()
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

        overall_status = (
            "healthy"
            if all(status == "healthy" for status in component_statuses)
            else "degraded"
            if "degraded" in component_statuses
            else "warnings"
        )

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


__all__ = ["router", "ops_health_router"]
