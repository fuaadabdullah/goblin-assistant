from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..departments import DEPARTMENT_REGISTRY, department_dispatcher
from ..providers.dispatcher import dispatcher

router = APIRouter(prefix="/routing", tags=["routing"])
_ROUTING_DEPRECATION_SUNSET = "2026-09-15"


def _legacy_route_extra(replaced_by: str) -> Dict[str, str]:
    return {
        "x-goblin-replaced-by": replaced_by,
        "x-goblin-sunset-at": _ROUTING_DEPRECATION_SUNSET,
        "x-goblin-route-contract": "compatibility",
    }


class DepartmentRouteRequest(BaseModel):
    """Request to route through a department (not a raw provider)."""

    department: str = "general"  # e.g. "reasoning", "coding", "creative"
    payload: Dict[str, Any]
    stream: Optional[bool] = False


# ── Department endpoints (public-facing) ───────────────────────────────


@router.get("/departments", response_model=List[Dict[str, str]])
async def list_departments():
    """List all available brain departments (no provider details)."""
    return DEPARTMENT_REGISTRY.list_public()


@router.get("/explain/{routing_id}", response_model=Dict[str, Any])
async def explain_routing_decision(routing_id: str):
    """Return why a given routing decision picked its provider.

    Backed by the in-memory explanation cache populated on every
    ProviderSelectionModel.score() call — see routing/provider_selection.py.
    Explanations are bounded and evicted FIFO, so old routing_ids 404.
    """
    from ..routing.provider_selection import get_explanation

    explanation = get_explanation(routing_id)
    if explanation is None:
        raise HTTPException(status_code=404, detail=f"No routing explanation for '{routing_id}'")
    return explanation


@router.get("/departments/{department_id}", response_model=Dict[str, str])
async def get_department(department_id: str):
    """Get details about a specific department."""
    try:
        policy = DEPARTMENT_REGISTRY.get_by_id_str(department_id)
        return {
            "department": policy.department_id.value,
            "name": policy.display_name,
            "description": policy.description,
            "supports_streaming": str(policy.supports_streaming),
            "supports_tools": str(policy.supports_tools),
        }
    except (KeyError, ValueError):
        raise HTTPException(status_code=404, detail=f"Department '{department_id}' not found")


@router.post(
    "/route",
    response_model=Dict[str, Any],
    deprecated=True,
    openapi_extra=_legacy_route_extra("/api/v1/api/route_task"),
)
async def route_through_department(request: DepartmentRouteRequest):
    """Deprecated compatibility route for department-dispatched tasks.

    Prefer `/api/v1/api/route_task` for canonical task routing. This route is
    retained so existing department callers continue to resolve through the
    shared dispatcher/provider-routing stack.
    """
    try:
        from ..departments import DepartmentId, DepartmentSelection

        selection = DepartmentSelection(
            department_id=DepartmentId(request.department.strip().lower()),
            reason=f"routed to {request.department}",
        )
        # Resolve the primary provider
        policy = DEPARTMENT_REGISTRY.get(selection.department_id)
        pid, model = policy.primary_provider
        selection.resolved_provider = pid
        selection.resolved_model = model

        result = await department_dispatcher.dispatch(
            selection=selection,
            payload=request.payload,
            stream=bool(request.stream),
        )
        # Strip internal fields from the public response
        result.pop("_department", None)
        result.pop("_department_reason", None)
        result["department"] = request.department
        return result
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Department routing failed: {exc}") from exc


# ── Legacy provider endpoints (deprecated) ────────────────────────────


@router.get(
    "/providers",
    response_model=List[str],
    deprecated=True,
    openapi_extra=_legacy_route_extra("/api/v1/providers/models"),
)
async def get_available_providers():
    """Deprecated compatibility route for provider discovery.

    Prefer `/api/v1/providers/models` for canonical provider/router inventory.
    """
    try:
        inventory = await dispatcher.get_provider_inventory(include_hidden=False)
        if inventory:
            return [p["id"] for p in inventory if p.get("configured") and not p.get("hidden")]

        # Fallback: return department IDs (more useful than provider IDs)
        return DEPARTMENT_REGISTRY.list_ids()
    except Exception:
        return DEPARTMENT_REGISTRY.list_ids()


@router.get(
    "/providers/{capability}",
    response_model=List[str],
    deprecated=True,
    openapi_extra=_legacy_route_extra("/api/v1/providers/models"),
)
async def get_providers_for_capability(capability: str):
    """Deprecated compatibility route for capability lookup.

    Prefer `/api/v1/providers/models` for canonical provider/router inventory.
    """
    try:
        # Map capability to matching departments
        dept_map = {
            "chat": ["general", "creative", "reasoning"],
            "streaming": ["general", "creative", "reasoning", "coding", "research"],
            "tools": ["general", "coding", "reasoning", "tool_use"],
            "vision": ["general", "creative", "reasoning"],
            "reasoning": ["reasoning", "coding"],
            "coding": ["coding", "reasoning"],
            "research": ["research", "reasoning"],
        }
        return dept_map.get(capability.strip().lower(), DEPARTMENT_REGISTRY.list_ids())
    except Exception:
        return DEPARTMENT_REGISTRY.list_ids()
