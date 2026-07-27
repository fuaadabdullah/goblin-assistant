"""
User account management endpoints
Handles user profile and preferences
"""

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.router import User as AuthenticatedUser
from api.auth.router import get_current_user
from api.core.contracts import JsonObject, SuccessEnvelope
from api.core.errors import DomainError
from api.services.platform_settings_service import (
    SaaSSettingsService,
)
from api.services.platform_settings_service import (
    get_platform_db as get_db,
)
from api.services.platform_settings_service import (
    get_readonly_platform_db as get_readonly_db,
)
from api.services.platform_settings_service import (
    save_account_profile as save_account_profile_record,
)

router = APIRouter(prefix="/account", tags=["account"])


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None


class PreferencesUpdate(BaseModel):
    summaries: Optional[bool] = None
    notifications: Optional[bool] = None
    familyMode: Optional[bool] = None
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
    summaries: bool = True
    familyMode: bool = False
    other: Optional[JsonObject]


class ChatSettingsUpdate(BaseModel):
    default_provider: Optional[str] = None
    default_model: Optional[str] = None
    system_prompt: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    summary_enabled: Optional[bool] = None
    metadata: Optional[JsonObject] = None


class ChatSettingsResponse(BaseModel):
    user_id: str
    default_provider: Optional[str]
    default_model: Optional[str]
    system_prompt: Optional[str]
    temperature: Optional[float]
    max_tokens: Optional[int]
    summary_enabled: bool
    metadata: Optional[JsonObject]


@router.put("/profile", response_model=SuccessEnvelope[ProfileResponse])
async def save_profile(
    profile: ProfileUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessEnvelope[ProfileResponse]:
    """Save user profile information"""
    try:
        saved = await save_account_profile_record(
            db=db,
            user_id=current_user.id,
            name=profile.name,
            email=profile.email,
            avatar_url=profile.avatar_url,
        )
        return SuccessEnvelope(
            data=ProfileResponse(
                id=saved["id"],
                email=saved["email"],
                name=saved["name"],
                avatar_url=saved["avatar_url"],
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


@router.get("/profile", response_model=SuccessEnvelope[ProfileResponse])
async def get_profile(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_readonly_db),
) -> SuccessEnvelope[ProfileResponse]:
    service = SaaSSettingsService(db)
    profile = await service.get_account_profile(current_user.id)
    if profile is None:
        raise DomainError(
            code="ACCOUNT_USER_NOT_FOUND",
            message="User not found",
            status_code=404,
        )
    return SuccessEnvelope(data=ProfileResponse(**profile))


@router.put("/preferences", response_model=SuccessEnvelope[PreferencesResponse])
async def save_preferences(
    preferences: PreferencesUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessEnvelope[PreferencesResponse]:
    """Save user preferences"""
    try:
        service = SaaSSettingsService(db)
        saved = await service.save_account_preferences(
            current_user.id,
            {
                "summaries": preferences.summaries,
                "notifications_enabled": preferences.notifications_enabled
                if preferences.notifications_enabled is not None
                else preferences.notifications,
                "familyMode": preferences.familyMode,
                "theme": preferences.theme,
                "default_model": preferences.default_model,
                "default_provider": preferences.default_provider,
                "language": preferences.language,
                "other": preferences.other or {},
            },
        )
        return SuccessEnvelope(
            data=PreferencesResponse(
                theme=saved.get("theme"),
                default_model=saved.get("default_model"),
                default_provider=saved.get("default_provider"),
                notifications_enabled=bool(saved.get("notifications_enabled", True)),
                language=saved.get("language"),
                summaries=bool(saved.get("summaries", True)),
                familyMode=bool(saved.get("familyMode", False)),
                other=saved.get("other") or {},
            )
        )
    except Exception as e:
        raise DomainError(
            code="ACCOUNT_SAVE_PREFERENCES_FAILED",
            message="Failed to save preferences",
            status_code=500,
            details={"reason": str(e)},
        ) from e


@router.get("/preferences", response_model=SuccessEnvelope[PreferencesResponse])
async def get_preferences(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_readonly_db),
) -> SuccessEnvelope[PreferencesResponse]:
    service = SaaSSettingsService(db)
    preferences = await service.get_account_preferences(current_user.id)
    if preferences is None:
        preferences = {
            "theme": "light",
            "default_model": None,
            "default_provider": None,
            "notifications_enabled": True,
            "language": "en",
            "summaries": True,
            "familyMode": False,
            "other": {},
        }
    return SuccessEnvelope(data=PreferencesResponse(**preferences))


@router.get("/chat-settings", response_model=SuccessEnvelope[ChatSettingsResponse])
async def get_chat_settings(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_readonly_db),
) -> SuccessEnvelope[ChatSettingsResponse]:
    service = SaaSSettingsService(db)
    settings = await service.get_chat_settings(current_user.id)
    if settings is None:
        settings = {
            "user_id": current_user.id,
            "default_provider": None,
            "default_model": None,
            "system_prompt": None,
            "temperature": 0.7,
            "max_tokens": None,
            "summary_enabled": True,
            "metadata": {},
        }
    return SuccessEnvelope(data=ChatSettingsResponse(**settings))


@router.put("/chat-settings", response_model=SuccessEnvelope[ChatSettingsResponse])
async def save_chat_settings(
    settings: ChatSettingsUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessEnvelope[ChatSettingsResponse]:
    service = SaaSSettingsService(db)
    saved = await service.save_chat_settings(
        current_user.id,
        {
            "default_provider": settings.default_provider,
            "default_model": settings.default_model,
            "system_prompt": settings.system_prompt,
            "temperature": settings.temperature,
            "max_tokens": settings.max_tokens,
            "summary_enabled": settings.summary_enabled,
            "metadata": settings.metadata or {},
        },
    )
    return SuccessEnvelope(data=ChatSettingsResponse(**saved))
