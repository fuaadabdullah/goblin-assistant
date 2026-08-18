"""Admin-focused operational routes."""

from fastapi import APIRouter

from .kpi import router as kpi_router
from .provider_state import router as provider_state_router

router = APIRouter(prefix="/admin", tags=["admin"])
router.include_router(provider_state_router)
router.include_router(kpi_router)

__all__ = ["router"]
