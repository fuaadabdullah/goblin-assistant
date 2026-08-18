"""
User account management endpoints
Handles user profile and preferences
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.router import User as AuthenticatedUser, get_current_user
from api.core.contracts import SuccessEnvelope
from api.storage.database import get_db
from api.storage.models import UserPreferencesModel
from api.storage.user_service import UserService

router = APIRouter(prefix="/account", tags=["account"])


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None


class PreferencesUpdate(BaseModel):
    theme: Optional[str] = None
    default_model: Optional[str] = None
    default_provider: Optional[str] = None
    notifications_enabled: Optional[bool] = None
    summaries: Optional[bool] = None
    familyMode: Optional[bool] = None
    language: Optional[str] = None
    other: Optional[Dict[str, Any]] = None


class ProfileResponse(BaseModel):
    id: str
    email: str
    name: Optional[str]
    avatar_url: Optional[str]


class PreferencesResponse(BaseModel):
    theme: Optional[str] = None
    default_model: Optional[str] = None
    default_provider: Optional[str] = None
    notifications_enabled: bool = True
    summaries: Optional[bool] = None
    familyMode: Optional[bool] = None
    language: Optional[str] = None
    other: Optional[Dict[str, Any]] = None


@router.put("/profile", response_model=ProfileResponse)
async def save_profile(
    profile: ProfileUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save user profile information"""
    try:
        user_service = UserService(db)
        user = await user_service.get_user_by_id(current_user.id)

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if profile.name is not None:
            user.name = profile.name
        if profile.email is not None and profile.email != user.email:
            existing = await user_service.get_user_by_email(profile.email)
            if existing:
                raise HTTPException(status_code=400, detail="Email already in use")
            user.email = profile.email

        db.add(user)
        await db.commit()
        await db.refresh(user)

        return ProfileResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            avatar_url=profile.avatar_url,
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save profile: {str(e)}")


async def _get_or_create_prefs(user_id: str, db: AsyncSession) -> UserPreferencesModel:
    result = await db.execute(
        select(UserPreferencesModel).where(UserPreferencesModel.user_id == user_id)
    )
    prefs = result.scalar_one_or_none()
    if prefs is None:
        import uuid as _uuid
        prefs = UserPreferencesModel(
            id=str(_uuid.uuid4()),
            user_id=user_id,
            ui_preferences={},
            privacy_settings={},
        )
        db.add(prefs)
    return prefs


def _prefs_to_response(prefs: UserPreferencesModel) -> PreferencesResponse:
    ui = prefs.ui_preferences or {}
    return PreferencesResponse(
        theme=ui.get("theme"),
        default_model=prefs.default_model,
        default_provider=prefs.default_provider,
        notifications_enabled=ui.get("notifications", True),
        summaries=ui.get("summaries"),
        familyMode=ui.get("familyMode"),
        language=ui.get("language"),
        other=prefs.privacy_settings or {},
    )


@router.get("/preferences")
async def get_preferences(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user preferences"""
    try:
        prefs = await _get_or_create_prefs(current_user.id, db)
        await db.commit()
        return SuccessEnvelope(data=_prefs_to_response(prefs))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get preferences: {str(e)}")


@router.put("/preferences")
async def save_preferences(
    preferences: PreferencesUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save user preferences"""
    try:
        prefs = await _get_or_create_prefs(current_user.id, db)

        if preferences.default_model is not None:
            prefs.default_model = preferences.default_model
        if preferences.default_provider is not None:
            prefs.default_provider = preferences.default_provider

        ui = dict(prefs.ui_preferences or {})
        if preferences.theme is not None:
            ui["theme"] = preferences.theme
        if preferences.notifications_enabled is not None:
            ui["notifications"] = preferences.notifications_enabled
        if preferences.summaries is not None:
            ui["summaries"] = preferences.summaries
        if preferences.familyMode is not None:
            ui["familyMode"] = preferences.familyMode
        if preferences.language is not None:
            ui["language"] = preferences.language
        prefs.ui_preferences = ui

        if preferences.other is not None:
            prefs.privacy_settings = preferences.other

        await db.commit()
        await db.refresh(prefs)
        return SuccessEnvelope(data=_prefs_to_response(prefs))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save preferences: {str(e)}")
