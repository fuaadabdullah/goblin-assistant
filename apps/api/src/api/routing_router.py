from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .departments import DEPARTMENT_REGISTRY, department_dispatcher
from .providers.dispatcher import dispatcher

router = APIRouter(prefix="/routing", tags=["routing"])


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


@router.post("/route", response_model=Dict[str, Any])
async def route_through_department(request: DepartmentRouteRequest):
    """Route a request through a brain department.

    The department dispatcher selects the best internal provider
    based on the department's policy chain.
    """
    try:
        from .departments import DepartmentId, DepartmentSelection  # noqa: PLC0415

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


@router.get("/providers", response_model=List[str])
async def get_available_providers():
    """[Deprecated] Use /routing/departments instead."""
    try:
        inventory = await dispatcher.get_provider_inventory(include_hidden=False)
        if inventory:
            return [p["id"] for p in inventory if p.get("configured") and not p.get("hidden")]

        # Fallback: return department IDs (more useful than provider IDs)
        return DEPARTMENT_REGISTRY.list_ids()
    except Exception:
        return DEPARTMENT_REGISTRY.list_ids()


@router.get("/providers/{capability}", response_model=List[str])
async def get_providers_for_capability(capability: str):
    """[Deprecated] Use /routing/departments instead — returns departments."""
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
