"""GCP Self-Hosted colab backend self-registration routes.

POST /ops/gcs/colab/register  — notebook calls this after Cloudflare Tunnel
                                 starts; hot-reloads the colab backend endpoint
                                 in-memory and persists to DB.
GET  /ops/gcs/colab/status    — returns the current registered endpoint.
"""

from __future__ import annotations

import os
from typing import Any, Dict

import httpx
import structlog
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, field_validator

from ._colab_store import load_endpoint_from_db, save_endpoint_to_db, write_env_file

logger = structlog.get_logger(__name__)

router = APIRouter()

_HEALTH_PROBE_TIMEOUT_S = 10
_FAMILY_PROVIDER = "gcp_vm"
_COLAB_ENGINE = "colab"


class ColabRegisterRequest(BaseModel):
    endpoint: str

    @field_validator("endpoint")
    @classmethod
    def validate_endpoint(cls, v: str) -> str:
        url = v.strip().rstrip("/")
        if not url.startswith("http://") and not url.startswith("https://"):
            raise ValueError("endpoint must be an http(s) URL")
        return url


def _colab_api_key() -> str:
    return os.getenv("COLAB_WORKER_API_KEY", "").strip()


def _check_bearer(request: Request) -> None:
    expected = _colab_api_key()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="COLAB_WORKER_API_KEY not configured on backend",
        )
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if auth[len("Bearer ") :] != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid COLAB_WORKER_API_KEY",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def _probe_health(url: str, api_key: str) -> Dict[str, Any]:
    health_url = f"{url}/health"
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        async with httpx.AsyncClient(timeout=_HEALTH_PROBE_TIMEOUT_S) as client:
            resp = await client.get(health_url, headers=headers)
        if resp.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=(f"Colab worker /health returned HTTP {resp.status_code}"),
            )
        try:
            return resp.json()
        except Exception:
            return {"status": "ok"}
    except HTTPException:
        raise
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=(f"Timed out probing {health_url} after {_HEALTH_PROBE_TIMEOUT_S}s"),
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to reach {health_url}: {exc}",
        )


@router.post("/gcs/colab/register")
async def register_colab_backend(
    request: Request,
    body: ColabRegisterRequest,
) -> Dict[str, Any]:
    """Register a new Colab tunnel URL and hot-reload the GCS colab backend."""
    _check_bearer(request)

    endpoint = body.endpoint
    api_key = _colab_api_key()

    health_payload = await _probe_health(endpoint, api_key)

    from ..providers.dispatcher import dispatcher

    try:
        dispatcher.update_backend_endpoint(_FAMILY_PROVIDER, _COLAB_ENGINE, endpoint)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    db_saved = await save_endpoint_to_db(endpoint)

    env_written = False
    if os.getenv("ENVIRONMENT", "development").lower() == "development":
        env_written = write_env_file("COLAB_WORKER_ENDPOINT", endpoint)

    probe_result: str = "skipped"
    try:
        from ..services.provider_health import health_monitor

        await health_monitor.probe_provider(_FAMILY_PROVIDER)
        probe_result = "ok"
    except Exception as exc:
        logger.warning("gcs_colab_register_probe_failed", error=str(exc))
        probe_result = f"failed:{exc}"

    logger.info("gcs_colab_backend_registered", endpoint=endpoint, db_saved=db_saved)

    return {
        "ok": True,
        "endpoint": endpoint,
        "health": health_payload,
        "db_saved": db_saved,
        "env_written": env_written,
        "probe_result": probe_result,
    }


@router.get("/gcs/colab/status")
async def gcs_colab_status(request: Request) -> Dict[str, Any]:
    """Return the current colab backend endpoint (in-memory and DB)."""
    _check_bearer(request)

    from ..providers.dispatcher import dispatcher

    configs = dispatcher._configs.get(_FAMILY_PROVIDER, {})
    backends = configs.get("backends", [])
    colab_bc = next((bc for bc in backends if bc.get("engine") == _COLAB_ENGINE), {})
    in_memory = colab_bc.get("endpoint") or None
    in_db = await load_endpoint_from_db()

    return {
        "provider": _FAMILY_PROVIDER,
        "engine": _COLAB_ENGINE,
        "endpoint_active": in_memory,
        "endpoint_persisted": in_db,
        "configured": bool(in_memory),
    }
