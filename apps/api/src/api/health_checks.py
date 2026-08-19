"""
Internal health-check probes for Goblin Assistant subsystems.

Each ``_check_*`` coroutine is a self-contained probe that returns a status
dict suitable for inclusion in the ``/health/all`` composite response.
Extracted from health.py to keep the router module focused on routing.
"""

import asyncio
import os
import shutil
from typing import Any, Dict, List

import aiosqlite


async def _check_vector_store() -> Dict[str, Any]:
    """Check the configured vector store (pgvector by default, Chroma HTTP if CHROMA_URL is set).

    Never probes the local filesystem — Render Free and similar ephemeral
    runtimes lose filesystem state on restart, so a file-presence check would
    always appear unconfigured even when the service is healthy.
    """
    try:
        from .services.vector_store import create_vector_store

        store = create_vector_store()
        return await store.health()
    except Exception as exc:
        return {"status": "degraded", "error": str(exc)}


# Backward-compatible alias — existing imports, test patches, and callers
# that reference _check_chroma continue to work without changes.
_check_chroma = _check_vector_store


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
            mod = importlib.import_module("api.routes.raptor_router")

        raptor_status = getattr(mod, "raptor_status")
        status = await raptor_status()
        overall = "healthy" if status.get("running") else "degraded"
        return {"status": overall, **status}
    except Exception as e:
        return {"status": "degraded", "error": str(e)}


async def _check_sandbox() -> Dict[str, Any]:
    """Check sandbox runner configuration and (optionally) docker image availability."""
    enabled = os.environ.get("VITE_FEATURE_SANDBOX", "false").lower() == "true"
    image = os.environ.get("SANDBOX_IMAGE")
    if not enabled and not image:
        return {"status": "degraded", "reason": "sandbox not enabled or configured"}

    if image and shutil.which("docker"):
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker",
                "images",
                "--format",
                "{{.Repository}}:{{.Tag}}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            out = stdout.decode()
            found = any(line.strip() == image for line in out.splitlines())
            return {
                "status": "healthy" if found else "degraded",
                "image": image,
                "image_found": found,
            }
        except Exception as e:
            return {"status": "degraded", "error": str(e), "image": image}

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

    if db and db.startswith("sqlite"):
        try:
            path_part = db.split("sqlite:")[-1]
            if path_part.startswith("/"):
                path = "/" + path_part.lstrip("/")
            else:
                path = path_part
            async with aiosqlite.connect(path) as conn:
                async with conn.execute("SELECT SUM(amount) FROM costs") as cur:
                    row = await cur.fetchone()
                    total = float(row[0]) if row and row[0] is not None else 0.0
            return {"status": "healthy", "total_cost": total}
        except Exception as e:
            return {"status": "degraded", "error": str(e)}

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

    return {"status": "degraded", "error": "unsupported db scheme", "db": db}
