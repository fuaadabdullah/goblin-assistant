"""
Unified health check endpoint for all Goblin Assistant subsystems.
Consolidates health checks from main.py, routing_router.py, and api_router.py.
"""

from typing import Dict, Any, List
from datetime import datetime
from fastapi import APIRouter, HTTPException
import asyncio
import os
import sqlite3
import shutil
import subprocess
import statistics
import time
from urllib.parse import urlparse
import httpx
from .core.contracts import SuccessEnvelope

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
        from .storage.database import engine
        from sqlalchemy import text

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
    try:
        from .storage.cache import cache

        # Test basic connectivity
        await cache.redis.ping()

        # Test basic operations
        test_key = "health_check_test"
        await cache.redis.set(test_key, "test_value", ex=10)
        value = await cache.redis.get(test_key)
        await cache.redis.delete(test_key)

        if value == "test_value":
            # Get Redis info for additional metrics
            info = await cache.redis.info()
            return {
                "status": "healthy",
                "connection": "available",
                "memory_used": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", "unknown"),
                "uptime_days": info.get("uptime_in_days", "unknown"),
            }
        else:
            return {"status": "degraded", "error": "Redis operations failed"}

    except Exception as e:
        return {"status": "unhealthy", "error": f"Redis connection failed: {str(e)}"}


async def check_api_health() -> Dict[str, Any]:
    """Check API system health"""
    try:
        # Basic API health check - could be expanded
        return {"status": "healthy", "endpoints": "responsive"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@router.get("/health", response_model=SuccessEnvelope[Dict[str, Any]])
async def health_check() -> SuccessEnvelope[Dict[str, Any]]:
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
            "status": (
                "healthy"
                if provider_status
                and all(
                    provider.get("status") in {"healthy", "unknown", "billing_issue"}
                    for provider in provider_status.values()
                )
                else "degraded"
            ),
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

    return SuccessEnvelope(
        data={
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "components": {
                "api": api_health,
                "routing": routing_health,
                "database": db_health,
                "redis": redis_health,
                "providers": provider_health,
                "security": security_status,
            },
        }
    )


@router.get("/health/stream", response_model=SuccessEnvelope[Dict[str, Any]])
async def health_stream() -> SuccessEnvelope[Dict[str, Any]]:
    """Streaming health check endpoint (legacy compatibility)"""
    # For backward compatibility, redirect to main health endpoint
    return await health_check()


# Extended, centralized health endpoints
async def _check_chroma() -> Dict[str, Any]:
    """Check Chroma vector DB.

    Strategy:
    - If CHROMA_DB_PATH (or default chroma_db/chroma.sqlite3) exists, open sqlite and
      report number of tables (approx collections) and file size.
    - Else, if CHROMA_URL is set, call CHROMA_URL/health or CHROMA_URL and inspect response.
    - Otherwise return degraded/unconfigured status.
    """
    # Prefer explicit config path
    path = os.environ.get("CHROMA_DB_PATH") or os.path.join(
        os.getcwd(), "chroma_db", "chroma.sqlite3"
    )
    if os.path.exists(path):
        try:
            size = os.path.getsize(path)
            conn = sqlite3.connect(path)
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [r[0] for r in cur.fetchall()]
            conn.close()
            return {
                "status": "healthy",
                "path": path,
                "file_size": size,
                "tables": len(tables),
                "table_names": tables,
            }
        except Exception as e:
            return {"status": "degraded", "error": str(e), "path": path}

    # Try HTTP probe if URL configured
    chroma_url = os.environ.get("CHROMA_URL") or os.environ.get("CHROMA_API_URL")
    if chroma_url:
        # normalize url
        urlparse(chroma_url)
        base = chroma_url.rstrip("/")
        probes = [f"{base}/health", base]
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                for p in probes:
                    try:
                        r = await client.get(p)
                        if r.status_code == 200:
                            data = r.json() if r.text else {}
                            return {"status": "healthy", "url": p, "response": data}
                    except Exception:
                        continue
        except Exception as e:
            return {"status": "degraded", "error": str(e), "url": chroma_url}

    return {"status": "degraded", "error": "Chroma not configured or unreachable"}


async def _check_mcp() -> Dict[str, Any]:
    """Probe MCP servers for connectivity.

    Reads MCP_SERVERS env var (comma separated host:port) or falls back to localhost:8765.
    Attempts a short TCP connect to each server.
    """
    servers_env = os.environ.get("MCP_SERVERS")
    if servers_env:
        servers = [s.strip() for s in servers_env.split(",") if s.strip()]
    else:
        servers = ["localhost:8765"]

    results: List[Dict[str, Any]] = []
    healthy = False
    for s in servers:
        host, _, port = s.partition(":")
        try:
            port_int = int(port) if port else 8765
            fut = asyncio.open_connection(host, port_int)
            try:
                reader, writer = await asyncio.wait_for(fut, timeout=1.0)
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception:
                    pass
                ok = True
            except Exception:
                ok = False
        except Exception:
            ok = False

        results.append({"server": s, "ok": ok})
        if ok:
            healthy = True

    status = "healthy" if healthy else "degraded"
    return {"status": status, "details": {"servers": results, "count": len(results)}}


async def _check_raptor() -> Dict[str, Any]:
    """Call into the local raptor router to get status if available.

    We attempt to import the router module using absolute import first, then fall back to
    a package relative import. This avoids "attempted relative import with no known parent"
    errors when tests insert the api directory directly on sys.path.
    """
    try:
        import importlib

        try:
            mod = importlib.import_module("raptor_router")
        except Exception:
            # Try package import (when running as a package)
            mod = importlib.import_module("api.raptor_router")

        raptor_status = getattr(mod, "raptor_status")
        status = await raptor_status()
        overall = "healthy" if status.get("running") else "degraded"
        return {"status": overall, **status}
    except Exception as e:
        return {"status": "degraded", "error": str(e)}


async def _check_sandbox() -> Dict[str, Any]:
    """Check sandbox runner configuration and (optionally) docker image availability."""
    # If sandbox feature disabled, mark degraded/unavailable
    enabled = os.environ.get("VITE_FEATURE_SANDBOX", "false").lower() == "true"
    image = os.environ.get("SANDBOX_IMAGE")
    if not enabled and not image:
        return {"status": "degraded", "reason": "sandbox not enabled or configured"}

    # If docker is available and SANDBOX_IMAGE is configured, check image exists
    if image and shutil.which("docker"):
        try:
            out = subprocess.check_output(
                ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"], text=True
            )
            found = any(line.strip() == image for line in out.splitlines())
            return {
                "status": "healthy" if found else "degraded",
                "image": image,
                "image_found": found,
            }
        except Exception as e:
            return {"status": "degraded", "error": str(e), "image": image}

    # Otherwise report configured but not verified
    return {"status": "healthy", "configured": bool(image or enabled), "image": image}


async def _check_cost_tracking() -> Dict[str, Any]:
    # Basic cost tracking probe: look for COST_TRACKING_ENABLED or COST_DB_URL
    enabled = os.environ.get("COST_TRACKING_ENABLED", "false").lower() == "true"
    db = os.environ.get("COST_DB_URL")
    if not enabled and not db:
        return {
            "status": "unknown",
            "total_cost": 0.0,
            "message": "cost tracking not configured",
        }

    # If DB is sqlite file, try a simple query
    if db and db.startswith("sqlite"):
        # expected format sqlite:////absolute/path or sqlite:///relative/path
        try:
            path_part = db.split("sqlite:")[-1]
            # Normalize to a proper filesystem path: ensure absolute paths begin with '/'
            if path_part.startswith("/"):
                path = "/" + path_part.lstrip("/")
            else:
                path = path_part
            conn = sqlite3.connect(path)
            cur = conn.cursor()
            # Try reading a costs table if present
            cur.execute("SELECT SUM(amount) FROM costs")
            total = cur.fetchone()[0] or 0.0
            conn.close()
            return {"status": "healthy", "total_cost": float(total)}
        except Exception as e:
            return {"status": "degraded", "error": str(e)}

    # Postgres support (Supabase, etc.) - safe, short blocking call via thread
    if db and (db.startswith("postgres://") or db.startswith("postgresql://")):
        try:
            import psycopg
        except Exception as e:
            return {
                "status": "degraded",
                "error": "psycopg not installed",
                "details": str(e),
            }

        def _pg_query():
            try:
                conn = psycopg.connect(db, connect_timeout=2)
                cur = conn.cursor()
                cur.execute("SELECT SUM(amount) FROM costs")
                row = cur.fetchone()
                total = float(row[0]) if row and row[0] is not None else 0.0
                cur.close()
                conn.close()
                return {"status": "healthy", "total_cost": total}
            except Exception as e:
                return {"status": "degraded", "error": str(e)}

        try:
            result = await asyncio.to_thread(_pg_query)
            return result
        except Exception as e:
            return {"status": "degraded", "error": str(e)}

    # If we get here, DB is configured but unsupported
    return {"status": "degraded", "error": "unsupported db scheme", "db": db}


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
    # Placeholder: return empty history
    return {"service": service, "history": []}


@router.get("/health/service-errors/{service}")
async def health_service_errors(service: str):
    # Placeholder: no recent errors
    return {"service": service, "recent_errors": []}


@router.post("/health/retest/{service}")
async def health_retest(service: str):
    # Trigger a retest for a service (placeholder)
    return {"service": service, "retest": "scheduled"}


@router.get("/health/ready")
async def readiness_check() -> Dict[str, Any]:
    """Readiness probe for Fly.io - returns 200 if app is ready to serve traffic."""
    try:
        # Check if we can connect to database (optional)
        db_ready = False
        try:
            from .storage.database import engine
            from sqlalchemy import text

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