"""Operations router package."""

from fastapi import APIRouter

from ..health import ops_health_router
from .aggregated import router as aggregated_router
from .circuit_breakers import router as circuit_breakers_router
from .gcs_selfhosted import router as gcs_selfhosted_router
from .performance import router as performance_router
from .security_audit import router as security_audit_router

router = APIRouter(prefix="/ops", tags=["operations"])
router.include_router(ops_health_router)
router.include_router(performance_router)
router.include_router(circuit_breakers_router)
router.include_router(aggregated_router)
router.include_router(security_audit_router)
router.include_router(gcs_selfhosted_router)

__all__ = ["router"]
