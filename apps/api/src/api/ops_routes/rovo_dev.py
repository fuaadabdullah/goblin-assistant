"""Rovo Dev (Goblin Coder) ops routes.

GET  /ops/rovo-dev/status  — credential check + dispatcher health state
POST /ops/rovo-dev/health  — on-demand MCP liveness probe
"""

from __future__ import annotations

import os
from typing import Any, Dict

import structlog
from fastapi import APIRouter

logger = structlog.get_logger(__name__)

router = APIRouter()

_PROVIDER_ID = "rovo_dev"


@router.get("/rovo-dev/status")
async def rovo_dev_status() -> Dict[str, Any]:
    """Return Rovo Dev configuration state and circuit breaker snapshot."""
    from ..providers.dispatcher import dispatcher  # lazy import avoids circular deps

    email_configured = bool(os.getenv("ATLASSIAN_EMAIL", "").strip())
    token_configured = bool(os.getenv("ATLASSIAN_API_TOKEN", "").strip())
    endpoint_override = os.getenv("ROVO_DEV_ENDPOINT", "").strip()

    cfg = dispatcher._configs.get(_PROVIDER_ID) if hasattr(dispatcher, "_configs") else None
    configured = (
        dispatcher.is_configured(_PROVIDER_ID) if hasattr(dispatcher, "is_configured") else False
    )
    base_endpoint = (
        cfg.get("endpoint", "") if isinstance(cfg, dict) else ""
    ) or "https://mcp.atlassian.com/v1/mcp"

    circuit: Dict[str, Any] = {}
    try:
        provider = (
            dispatcher._ensure_provider(_PROVIDER_ID)
            if hasattr(dispatcher, "_ensure_provider")
            else None
        )
        if provider is not None:
            circuit = provider.circuit_status()
    except Exception:
        pass

    return {
        "provider": _PROVIDER_ID,
        "configured": configured,
        "email_configured": email_configured,
        "token_configured": token_configured,
        "endpoint_active": endpoint_override or base_endpoint,
        "circuit_breaker": circuit,
    }


@router.post("/rovo-dev/health")
async def rovo_dev_health_probe() -> Dict[str, Any]:
    """Run an on-demand health probe against the Atlassian MCP endpoint."""
    from ..providers.dispatcher import dispatcher

    try:
        health = await dispatcher.check_provider(_PROVIDER_ID)
        return {"ok": True, "health": health}
    except Exception as exc:
        logger.warning("rovo_dev_health_probe_failed", error=str(exc))
        return {"ok": False, "error": str(exc)}
