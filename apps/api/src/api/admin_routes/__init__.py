"""Admin-focused operational routes."""

from fastapi import APIRouter

from .provider_state import router as provider_state_router

router = APIRouter(prefix="/admin", tags=["admin"])
router.include_router(provider_state_router)

__all__ = ["router"]
