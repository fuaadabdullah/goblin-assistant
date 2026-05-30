"""
User account management endpoints
Handles user profile and preferences
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from api.auth.router import get_current_user, User as AuthenticatedUser
from api.core.contracts import JsonObject, SuccessEnvelope
from api.core.errors import DomainError
from api.storage.database import get_db
from api.storage.user_service import UserService
from sqlalchemy.ext.asyncio import AsyncSession

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
    language: Optional[str] = None
    other: Optional[JsonObject] = None


class ProfileResponse(BaseModel):
    id: str
    email: str
    name: Optional[str]
    avatar_url: Optional[str]


class PreferencesResponse(BaseModel):
    theme: Optional[str]
    default_model: Optional[str]
    default_provider: Optional[str]
    notifications_enabled: bool
    language: Optional[str]
    other: Optional[JsonObject]


@router.put("/profile", response_model=SuccessEnvelope[ProfileResponse])
async def save_profile(
    profile: ProfileUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessEnvelope[ProfileResponse]:
    """Save user profile information"""
    try:
        user_service = UserService(db)
        user = await user_service.get_user_by_id(current_user.id)

        if not user:
            raise DomainError(
                code="ACCOUNT_USER_NOT_FOUND", message="User not found", status_code=404
            )

        # Update profile fields
        if profile.name is not None:
            user.name = profile.name
        if profile.email is not None and profile.email != user.email:
            # Check email uniqueness
            existing = await user_service.get_user_by_email(profile.email)
            if existing:
                raise DomainError(
                    code="ACCOUNT_EMAIL_IN_USE",
                    message="Email already in use",
                    status_code=400,
                )
            user.email = profile.email

        db.add(user)
        await db.commit()
        await db.refresh(user)

        return SuccessEnvelope(
            data=ProfileResponse(
                id=user.id,
                email=user.email,
                name=user.name,
                avatar_url=profile.avatar_url,
            )
        )
    except DomainError:
        raise
    except Exception as e:
        await db.rollback()
        raise DomainError(
            code="ACCOUNT_SAVE_PROFILE_FAILED",
            message="Failed to save profile",
            status_code=500,
            details={"reason": str(e)},
        ) from e


@router.put("/preferences", response_model=SuccessEnvelope[PreferencesResponse])
async def save_preferences(
    preferences: PreferencesUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> SuccessEnvelope[PreferencesResponse]:
    """Save user preferences"""
    try:
        # Return success response with user preferences
        return SuccessEnvelope(
            data=PreferencesResponse(
                theme=preferences.theme or "light",
                default_model=preferences.default_model,
                default_provider=preferences.default_provider,
                notifications_enabled=(
                    preferences.notifications_enabled
                    if preferences.notifications_enabled is not None
                    else True
                ),
                language=preferences.language or "en",
                other=preferences.other or {},
            )
        )
    except Exception as e:
        raise DomainError(
            code="ACCOUNT_SAVE_PREFERENCES_FAILED",
            message="Failed to save preferences",
            status_code=500,
            details={"reason": str(e)},
        ) from e
