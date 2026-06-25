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
import httpx


async def _check_chroma() -> Dict[str, Any]:
    """Check Chroma vector DB.

    Strategy:
    - If CHROMA_DB_PATH (or default chroma_db/chroma.sqlite3) exists, open sqlite and
      report number of tables (approx collections) and file size.
    - Else, if CHROMA_URL is set, call CHROMA_URL/health or CHROMA_URL and inspect response.
    - Otherwise return degraded/unconfigured status.
    """
    from urllib.parse import urlparse

    # Prefer explicit config path
    path = os.environ.get("CHROMA_DB_PATH") or os.path.join(
        os.getcwd(), "chroma_db", "chroma.sqlite3"
    )
    if os.path.exists(path):  # noqa: ASYNC240
        try:
            size = os.path.getsize(path)  # noqa: ASYNC240
            async with (
                aiosqlite.connect(path) as conn,
                conn.execute("SELECT name FROM sqlite_master WHERE type='table';") as cur,
            ):
                tables = [r[0] for r in await cur.fetchall()]
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
            mod = importlib.import_module("api.raptor_router")

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
