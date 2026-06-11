"""Subsystem health-check primitives shared by the health routers.

Route handlers live in `health.py` (public) and `ops_health.py` (ops);
this module owns the actual checks and the unified payload builder.
"""

import asyncio
import os
from datetime import datetime
from typing import Any, Dict

from ._version import get_version


async def check_routing_health() -> Dict[str, Any]:
    """Check routing system health"""
    try:
        from .departments import DEPARTMENT_REGISTRY

        providers = DEPARTMENT_REGISTRY.list_ids()
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


def overall_status_from(component_statuses: list) -> str:
    return (
        "healthy"
        if all(status == "healthy" for status in component_statuses)
        else "degraded"
        if "degraded" in component_statuses
        else "warnings"
    )


async def build_health_payload(
    routing_check=None,
    db_check=None,
    redis_check=None,
    api_check=None,
) -> Dict[str, Any]:
    """Run all subsystem checks concurrently and build the unified payload.

    The check functions can be overridden so callers (and tests patching
    `api.health.check_*`) control the individual probes.
    """
    routing_health, db_health, redis_health, api_health = await asyncio.gather(
        (routing_check or check_routing_health)(),
        (db_check or check_db_health)(),
        (redis_check or check_redis_health)(),
        (api_check or check_api_health)(),
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

    overall_status = overall_status_from(
        [
            routing_health["status"],
            db_health["status"],
            redis_health["status"],
            api_health["status"],
            provider_health["status"],
            security_status["status"],
        ]
    )

    return {
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
