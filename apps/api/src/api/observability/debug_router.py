"""
Debug Surfaces Router
Provides endpoints for inspecting the observability data and debugging system behavior.

Endpoints are organized into four sub-routers by domain:
  debug_write_router   — domain events, write decisions, memory promotions
  debug_retrieval_router — retrieval traces
  debug_context_router   — context assembly snapshots
  debug_system_router    — system health, tool traces, admin actions
"""

from typing import Any, Dict

from fastapi import APIRouter

from .debug_context_router import router as context_router
from .debug_retrieval_router import get_retrieval_trace  # noqa: F401
from .debug_retrieval_router import router as retrieval_router
from .debug_system_router import (  # noqa: F401
    get_observability_summary,
    get_system_health,
)
from .debug_system_router import (
    router as system_router,
)
from .debug_write_router import (  # noqa: F401
    get_write_decisions,
    search_memory_promotions,
    search_write_decisions,
)
from .debug_write_router import (
    router as write_router,
)

router = APIRouter(prefix="/debug", tags=["debug"])

router.include_router(write_router)
router.include_router(retrieval_router)
router.include_router(context_router)
router.include_router(system_router)


async def get_memory_debug_info(user_id: str) -> Dict[str, Any]:
    """Memory debug info for a user — promotions + health summary."""
    from .debug_write_router import get_memory_health, get_user_memory  # noqa: PLC0415

    memory_items_resp = await get_user_memory(user_id=user_id)
    health_resp = await get_memory_health(user_id=user_id)
    return {
        "user_id": user_id,
        "memory_items": memory_items_resp.get("memory_items", []),
        "memory_health": health_resp,
    }
