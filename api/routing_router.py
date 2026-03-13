from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from .providers.dispatcher import dispatcher
from .routing.router import route_task, top_providers_for

router = APIRouter(prefix="/routing", tags=["routing"])


class RouteRequest(BaseModel):
    task_type: str
    payload: Dict[str, Any]
    prefer_local: Optional[bool] = False
    prefer_cost: Optional[bool] = False
    max_retries: Optional[int] = 2
    stream: Optional[bool] = False


def _fallback_provider_entries() -> List[Dict[str, Any]]:
    try:
        return [
            provider
            for provider in dispatcher.list_providers(include_hidden=False)
            if not provider.get("hidden", False)
        ]
    except Exception:
        configs = getattr(dispatcher, "_configs", {}) or {}
        entries: List[Dict[str, Any]] = []
        for provider_id, config in configs.items():
            if config.get("hidden", False):
                continue

            try:
                configured = bool(dispatcher.is_configured(provider_id))
            except Exception:
                configured = False

            entries.append(
                {
                    "id": provider_id,
                    "name": config.get("name", provider_id),
                    "models": list(config.get("models", [])),
                    "capabilities": list(config.get("capabilities", [])),
                    "priority_tier": int(config.get("priority_tier", 999)),
                    "tier": config.get("tier", "cloud"),
                    "local_routing": bool(config.get("local_routing", False)),
                    "hidden": bool(config.get("hidden", False)),
                    "configured": configured,
                    "healthy": False,
                    "health": "unknown",
                    "health_reason": "inventory_unavailable",
                    "is_selectable": False,
                    "latency_ms": 0.0,
                }
            )

        entries.sort(key=lambda item: (int(item.get("priority_tier", 999)), str(item.get("id", ""))))
        return entries


@router.get("/providers", response_model=List[str])
async def get_available_providers():
    try:
        inventory = await dispatcher.get_provider_inventory(include_hidden=False)
        return [entry["id"] for entry in inventory if entry.get("configured")]
    except Exception:
        fallback = _fallback_provider_entries()
        return [entry["id"] for entry in fallback if entry.get("configured")]


@router.get("/providers/details", response_model=List[Dict[str, Any]])
async def get_provider_details():
    try:
        return await dispatcher.get_provider_inventory(include_hidden=False)
    except Exception:
        return _fallback_provider_entries()


@router.get("/providers/{capability}", response_model=List[str])
async def get_providers_for_capability(capability: str):
    try:
        return top_providers_for(capability)
    except Exception:
        return []


@router.post("/route")
async def route_request(request: RouteRequest):
    try:
        return await route_task(
            task_type=request.task_type,
            payload=request.payload,
            prefer_local=bool(request.prefer_local),
            prefer_cost=bool(request.prefer_cost),
            max_retries=int(request.max_retries or 2),
            stream=bool(request.stream),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Routing failed: {exc}") from exc
