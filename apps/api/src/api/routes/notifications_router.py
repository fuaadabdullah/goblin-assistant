"""Notification persistence endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.router import User as AuthenticatedUser
from api.auth.router import get_current_user
from api.core.contracts import SuccessEnvelope
from api.services.platform_settings_service import SaaSSettingsService
from api.services.platform_settings_service import get_platform_db as get_db

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationCreate(BaseModel):
    title: str
    body: str
    channel: Optional[str] = "in_app"
    category: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@router.get("/", response_model=SuccessEnvelope[List[Dict[str, Any]]])
async def list_notifications(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = SaaSSettingsService(db)
    rows = await service.list_notifications(current_user.id)
    return SuccessEnvelope(
        data=[
            {
                "notification_id": row.notification_id,
                "user_id": row.user_id,
                "channel": row.channel,
                "title": row.title,
                "body": row.body,
                "category": row.category,
                "is_read": row.is_read,
                "read_at": row.read_at.isoformat() if row.read_at else None,
                "created_at": row.created_at.isoformat(),
                "metadata": row.metadata_ or {},
            }
            for row in rows
        ]
    )


@router.post("/", response_model=SuccessEnvelope[Dict[str, Any]])
async def create_notification(
    payload: NotificationCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = SaaSSettingsService(db)
    row = await service.create_notification(
        {
            "user_id": current_user.id,
            "title": payload.title,
            "body": payload.body,
            "channel": payload.channel or "in_app",
            "category": payload.category,
            "metadata": payload.metadata or {},
        }
    )
    return SuccessEnvelope(
        data={
            "notification_id": row.notification_id,
            "user_id": row.user_id,
            "title": row.title,
            "body": row.body,
            "channel": row.channel,
            "category": row.category,
            "is_read": row.is_read,
        }
    )


@router.patch("/{notification_id}/read", response_model=SuccessEnvelope[Dict[str, Any]])
async def mark_notification_read(
    notification_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = SaaSSettingsService(db)
    row = await service.mark_notification_read(notification_id)
    if row is None or row.user_id != current_user.id:
        return SuccessEnvelope(data={"notification_id": notification_id, "updated": False})
    return SuccessEnvelope(
        data={
            "notification_id": row.notification_id,
            "updated": True,
            "is_read": row.is_read,
            "read_at": row.read_at.isoformat() if row.read_at else None,
        }
    )
