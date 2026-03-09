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


@router.get("/providers", response_model=List[str])
async def get_available_providers():
    try:
        inventory = await dispatcher.get_provider_inventory(include_hidden=False)
        return [entry["id"] for entry in inventory if entry.get("configured")]
    except Exception:
        return []


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
