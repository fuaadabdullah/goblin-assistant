"""
User preferences service for database operations
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from typing import Optional, Dict, Any
from datetime import datetime

from .models import UserPreferencesModel
from .database import get_db_context


class PreferencesService:
    """Service for managing user preferences"""

    @staticmethod
    async def get_preferences(user_id: str) -> Optional[Dict[str, Any]]:
        """Get user preferences by user_id"""
        async with get_db_context() as session:
            result = await session.execute(
                select(UserPreferencesModel).where(
                    UserPreferencesModel.user_id == user_id
                )
            )
            prefs = result.scalar_one_or_none()
            if prefs:
                return {
                    "id": prefs.id,
                    "user_id": prefs.user_id,
                    "default_provider": prefs.default_provider,
                    "default_model": prefs.default_model,
                    "rag_consent": prefs.rag_consent == "true",
                    "privacy_settings": prefs.privacy_settings,
                    "created_at": prefs.created_at.isoformat(),
                    "updated_at": prefs.updated_at.isoformat(),
                }
            return None

    @staticmethod
    async def create_or_update_preferences(
        user_id: str,
        default_provider: Optional[str] = None,
        default_model: Optional[str] = None,
        rag_consent: Optional[bool] = None,
        privacy_settings: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create or update user preferences"""
        async with get_db_context() as session:
            # Check if preferences exist
            result = await session.execute(
                select(UserPreferencesModel).where(
                    UserPreferencesModel.user_id == user_id
                )
            )
            prefs = result.scalar_one_or_none()

            if prefs:
                # Update existing preferences
                if default_provider is not None:
                    prefs.default_provider = default_provider
                if default_model is not None:
                    prefs.default_model = default_model
                if rag_consent is not None:
                    prefs.rag_consent = "true" if rag_consent else "false"
                if privacy_settings is not None:
                    prefs.privacy_settings = privacy_settings
                prefs.updated_at = datetime.utcnow()
            else:
                # Create new preferences
                prefs = UserPreferencesModel(
                    user_id=user_id,
                    default_provider=default_provider,
                    default_model=default_model,
                    rag_consent="true" if rag_consent else "false",
                    privacy_settings=privacy_settings or {},
                )
                session.add(prefs)

            await session.flush()
            await session.refresh(prefs)

            return {
                "id": prefs.id,
                "user_id": prefs.user_id,
                "default_provider": prefs.default_provider,
                "default_model": prefs.default_model,
                "rag_consent": prefs.rag_consent == "true",
                "privacy_settings": prefs.privacy_settings,
                "created_at": prefs.created_at.isoformat(),
                "updated_at": prefs.updated_at.isoformat(),
            }

    @staticmethod
    async def delete_preferences(user_id: str) -> bool:
        """Delete user preferences"""
        async with get_db_context() as session:
            result = await session.execute(
                delete(UserPreferencesModel).where(
                    UserPreferencesModel.user_id == user_id
                )
            )
            return result.rowcount > 0

    @staticmethod
    async def update_rag_consent(user_id: str, consent: bool) -> Dict[str, Any]:
        """Update RAG consent for user"""
        return await PreferencesService.create_or_update_preferences(
            user_id=user_id, rag_consent=consent
        )

    @staticmethod
    async def has_rag_consent(user_id: str) -> bool:
        """Check if user has given RAG consent"""
        prefs = await PreferencesService.get_preferences(user_id)
        if prefs:
            return prefs.get("rag_consent", False)
        return False


# Singleton instance
preferences_service = PreferencesService()
