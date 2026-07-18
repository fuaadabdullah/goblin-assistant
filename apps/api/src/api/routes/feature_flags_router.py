"""Feature flag persistence and evaluation endpoints."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.contracts import SuccessEnvelope
from api.core.errors import DomainError
from api.services.platform_settings_service import SaaSSettingsService
from api.services.platform_settings_service import get_platform_db as get_db

router = APIRouter(prefix="/feature-flags", tags=["feature-flags"])


class FeatureFlagUpsert(BaseModel):
    enabled: bool = False
    default_value: Optional[Dict[str, Any]] = None
    user_overrides: Optional[Dict[str, Any]] = None
    rollout_percent: Optional[int] = None
    target_users: Optional[list[str]] = None
    target_roles: Optional[list[str]] = None
    metadata: Optional[Dict[str, Any]] = None


@router.get("/{flag_key}", response_model=SuccessEnvelope[Dict[str, Any]])
async def get_feature_flag(
    flag_key: str,
    user_id: Optional[str] = None,
    role: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    service = SaaSSettingsService(db)
    resolved = await service.resolve_feature_flag(flag_key, user_id=user_id, role=role)
    if resolved is None:
        raise DomainError(
            code="FEATURE_FLAG_NOT_FOUND",
            message="Feature flag not found",
            status_code=404,
        )
    return SuccessEnvelope(data=resolved)


@router.put("/{flag_key}", response_model=SuccessEnvelope[Dict[str, Any]])
async def upsert_feature_flag(
    flag_key: str,
    payload: FeatureFlagUpsert,
    db: AsyncSession = Depends(get_db),
):
    service = SaaSSettingsService(db)
    row = await service.upsert_feature_flag(
        flag_key,
        {
            "enabled": payload.enabled,
            "default_value": payload.default_value or {},
            "user_overrides": payload.user_overrides or {},
            "rollout_percent": payload.rollout_percent or 0,
            "target_users": payload.target_users or [],
            "target_roles": payload.target_roles or [],
            "metadata": payload.metadata or {},
        },
    )
    return SuccessEnvelope(
        data={
            "flag_key": row.flag_key,
            "enabled": row.enabled,
            "rollout_percent": row.rollout_percent,
            "target_users": row.target_users,
            "target_roles": row.target_roles,
        }
    )
