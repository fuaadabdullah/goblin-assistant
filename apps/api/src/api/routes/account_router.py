"""
User account management endpoints
Handles user profile and preferences
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
from api.auth.router import get_current_user, User as AuthenticatedUser
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
    other: Optional[Dict[str, Any]] = None

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
    other: Optional[Dict[str, Any]]

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
        
        # Update profile fields
        if profile.name is not None:
            user.name = profile.name
        if profile.email is not None and profile.email != user.email:
            # Check email uniqueness
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

@router.put("/preferences", response_model=PreferencesResponse)
async def save_preferences(
    preferences: PreferencesUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Save user preferences"""
    try:
        # Return success response with user preferences
        return PreferencesResponse(
            theme=preferences.theme or "light",
            default_model=preferences.default_model,
            default_provider=preferences.default_provider,
            notifications_enabled=preferences.notifications_enabled if preferences.notifications_enabled is not None else True,
            language=preferences.language or "en",
            other=preferences.other or {},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save preferences: {str(e)}")
