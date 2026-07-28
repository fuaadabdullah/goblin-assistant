"""User profile service for managing structured user data."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..storage.profile_model import UserProfileModel
from .knowledge_graph_service import KnowledgeGraphService


class UserProfileService:
    """Manage user profiles with caching and async refresh."""

    CACHE_TTL_HOURS = 1  # Refresh if older than 1 hour

    def __init__(self, session_factory=None):
        self.session_factory = session_factory
        self.graph_service = KnowledgeGraphService(session_factory)

    async def get_profile(
        self, user_id: str, session: Optional[AsyncSession] = None
    ) -> UserProfileModel:
        """Get user profile, building from scratch if missing or stale."""
        close_session = False
        if session is None:
            if not self.session_factory:
                raise ValueError("session_factory required if session not provided")
            session = self.session_factory()
            close_session = True

        try:
            # Try to fetch existing profile
            result = await session.execute(
                select(UserProfileModel).where(UserProfileModel.user_id == user_id)
            )
            profile = result.scalar_one_or_none()

            # If missing or stale, refresh
            if profile is None or self._is_stale(profile.updated_at):
                profile = await self.refresh_profile(user_id, session)

            return profile
        finally:
            if close_session:
                await session.close()

    async def refresh_profile(
        self, user_id: str, session: Optional[AsyncSession] = None
    ) -> UserProfileModel:
        """Refresh profile from entity graph snapshot."""
        close_session = False
        if session is None:
            if not self.session_factory:
                raise ValueError("session_factory required if session not provided")
            session = self.session_factory()
            close_session = True

        try:
            # Build snapshot from entity graph
            snapshot = await self.graph_service.build_profile_snapshot(user_id, session)

            # Upsert into user_profiles
            result = await session.execute(
                select(UserProfileModel).where(UserProfileModel.user_id == user_id)
            )
            profile = result.scalar_one_or_none()

            snapshot_dict = snapshot.to_dict()

            if profile:
                # Update existing profile
                profile.goals = snapshot_dict["goals"]
                profile.projects = snapshot_dict["projects"]
                profile.preferences = snapshot_dict["preferences"]
                profile.key_entities = snapshot_dict["key_entities"]
                profile.updated_at = datetime.utcnow()
            else:
                # Create new profile
                profile = UserProfileModel(
                    user_id=user_id,
                    goals=snapshot_dict["goals"],
                    projects=snapshot_dict["projects"],
                    preferences=snapshot_dict["preferences"],
                    key_entities=snapshot_dict["key_entities"],
                )
                session.add(profile)

            await session.flush()
            return profile
        finally:
            if close_session:
                await session.close()

    def _is_stale(self, updated_at: datetime) -> bool:
        """Check if profile is older than cache TTL."""
        return datetime.utcnow() - updated_at > timedelta(hours=self.CACHE_TTL_HOURS)

    async def invalidate_profile(
        self, user_id: str, session: Optional[AsyncSession] = None
    ) -> None:
        """Invalidate profile by setting updated_at to far past, forcing refresh on next get."""
        close_session = False
        if session is None:
            if not self.session_factory:
                raise ValueError("session_factory required if session not provided")
            session = self.session_factory()
            close_session = True

        try:
            result = await session.execute(
                select(UserProfileModel).where(UserProfileModel.user_id == user_id)
            )
            profile = result.scalar_one_or_none()
            if profile:
                profile.updated_at = datetime.utcnow() - timedelta(hours=self.CACHE_TTL_HOURS + 1)
                await session.flush()
        finally:
            if close_session:
                await session.close()
