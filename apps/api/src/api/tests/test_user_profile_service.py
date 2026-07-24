"""Tests for user_profile_service module — profile caching and refresh."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.services.user_profile_service import UserProfileService


class TestUserProfileService:
    """Test UserProfileService class methods."""

    def test_init_with_session_factory(self):
        """UserProfileService initializes with session_factory."""
        mock_factory = MagicMock()
        service = UserProfileService(session_factory=mock_factory)

        assert service.session_factory is mock_factory
        assert service.graph_service is not None

    @pytest.mark.asyncio
    async def test_get_profile_raises_without_session_or_factory(self):
        """get_profile raises ValueError when neither session nor factory provided."""
        service = UserProfileService(session_factory=None)

        with pytest.raises(ValueError, match="session_factory required"):
            await service.get_profile("user-1", session=None)

    @pytest.mark.asyncio
    async def test_get_profile_returns_fresh_profile(self):
        """get_profile returns fresh profile from database."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_profile = MagicMock()
        mock_profile.user_id = "user-1"
        mock_profile.updated_at = datetime.utcnow()  # Fresh, not stale

        mock_result.scalar_one_or_none.return_value = mock_profile
        mock_session.execute.return_value = mock_result

        service = UserProfileService(session_factory=None)
        result = await service.get_profile("user-1", session=mock_session)

        assert result == mock_profile

    @pytest.mark.asyncio
    async def test_get_profile_refreshes_stale_profile(self):
        """get_profile refreshes profile when stale."""
        # Mock a stale profile
        mock_session = AsyncMock()
        mock_old_profile = MagicMock()
        mock_old_profile.updated_at = datetime.utcnow() - timedelta(hours=2)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_old_profile

        mock_session.execute.return_value = mock_result

        # Mock the snapshot and refresh
        mock_snapshot = MagicMock()
        mock_snapshot.to_dict.return_value = {
            "goals": ["goal1"],
            "projects": ["proj1"],
            "preferences": {},
            "key_entities": {},
        }

        mock_new_profile = MagicMock()

        service = UserProfileService(session_factory=None)

        with patch.object(
            service.graph_service, "build_profile_snapshot", return_value=mock_snapshot
        ):
            with patch.object(service, "refresh_profile", return_value=mock_new_profile):
                result = await service.get_profile("user-1", session=mock_session)

        assert result == mock_new_profile

    @pytest.mark.asyncio
    async def test_get_profile_no_profile_triggers_refresh(self):
        """get_profile triggers refresh when profile doesn't exist."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # No existing profile

        mock_session.execute.return_value = mock_result

        mock_new_profile = MagicMock()

        service = UserProfileService(session_factory=None)

        with patch.object(service, "refresh_profile", return_value=mock_new_profile):
            result = await service.get_profile("user-1", session=mock_session)

        assert result == mock_new_profile

    @pytest.mark.asyncio
    async def test_refresh_profile_creates_new_profile(self):
        """refresh_profile creates new profile when none exists."""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # No existing profile

        mock_session.execute.return_value = mock_result

        mock_snapshot = MagicMock()
        mock_snapshot.to_dict.return_value = {
            "goals": ["goal1"],
            "projects": ["proj1"],
            "preferences": {"pref": "value"},
            "key_entities": {},
        }

        service = UserProfileService(session_factory=None)

        with patch.object(
            service.graph_service, "build_profile_snapshot", return_value=mock_snapshot
        ):
            await service.refresh_profile("user-1", session=mock_session)

        # Verify that session.add was called (for new profile)
        mock_session.add.assert_called_once()
        # Verify that session.flush was called
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_profile_updates_existing_profile(self):
        """refresh_profile updates existing profile."""
        mock_session = AsyncMock()

        # First query returns existing profile
        mock_existing_profile = MagicMock()
        mock_existing_profile.user_id = "user-1"
        mock_existing_profile.goals = ["old_goal"]

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_existing_profile

        mock_session.execute.return_value = mock_result

        mock_snapshot = MagicMock()
        mock_snapshot.to_dict.return_value = {
            "goals": ["new_goal"],
            "projects": ["proj1"],
            "preferences": {},
            "key_entities": {},
        }

        service = UserProfileService(session_factory=None)

        with patch.object(
            service.graph_service, "build_profile_snapshot", return_value=mock_snapshot
        ):
            await service.refresh_profile("user-1", session=mock_session)

        # Verify update happened on existing profile
        assert mock_existing_profile.goals == ["new_goal"]
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_profile_uses_session_factory_when_needed(self):
        """refresh_profile creates and closes session when not provided."""
        mock_factory = MagicMock()
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_factory.return_value = mock_session

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_session.execute.return_value = mock_result

        mock_snapshot = MagicMock()
        mock_snapshot.to_dict.return_value = {
            "goals": [],
            "projects": [],
            "preferences": {},
            "key_entities": {},
        }

        service = UserProfileService(session_factory=mock_factory)

        with patch.object(
            service.graph_service, "build_profile_snapshot", return_value=mock_snapshot
        ):
            await service.refresh_profile("user-1", session=None)

        # Verify session was created and closed
        mock_factory.assert_called_once()
        mock_session.close.assert_called_once()

    def test_is_stale_fresh_profile(self):
        """_is_stale returns False for fresh profile."""
        service = UserProfileService(session_factory=None)
        fresh_time = datetime.utcnow() - timedelta(minutes=30)

        is_stale = service._is_stale(fresh_time)

        assert is_stale is False

    def test_is_stale_old_profile(self):
        """_is_stale returns True for stale profile."""
        service = UserProfileService(session_factory=None)
        old_time = datetime.utcnow() - timedelta(hours=2)

        is_stale = service._is_stale(old_time)

        assert is_stale is True

    def test_is_stale_boundary(self):
        """_is_stale returns False before TTL and True after."""
        service = UserProfileService(session_factory=None)
        well_before = datetime.utcnow() - timedelta(hours=service.CACHE_TTL_HOURS - 1)
        well_after = datetime.utcnow() - timedelta(hours=service.CACHE_TTL_HOURS + 1)

        # Well before TTL should be False
        assert service._is_stale(well_before) is False
        # Well after TTL should be True
        assert service._is_stale(well_after) is True

    @pytest.mark.asyncio
    async def test_invalidate_profile_sets_stale_timestamp(self):
        """invalidate_profile sets updated_at to far past."""
        mock_session = AsyncMock()
        mock_profile = MagicMock()
        mock_profile.user_id = "user-1"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_profile

        mock_session.execute.return_value = mock_result

        service = UserProfileService(session_factory=None)

        await service.invalidate_profile("user-1", session=mock_session)

        # Verify the timestamp was set to far past
        assert mock_profile.updated_at < datetime.utcnow() - timedelta(hours=2)
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalidate_profile_no_profile(self):
        """invalidate_profile handles non-existent profile gracefully."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_session.execute.return_value = mock_result

        service = UserProfileService(session_factory=None)

        # Should not raise, just return
        await service.invalidate_profile("user-1", session=mock_session)

        # flush should not be called since profile is None
        mock_session.flush.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalidate_profile_uses_session_factory(self):
        """invalidate_profile uses session_factory when session not provided."""
        mock_factory = MagicMock()
        mock_session = AsyncMock()
        mock_factory.return_value = mock_session

        mock_profile = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_profile

        mock_session.execute.return_value = mock_result

        service = UserProfileService(session_factory=mock_factory)

        await service.invalidate_profile("user-1", session=None)

        # Verify factory was called and session was closed
        mock_factory.assert_called_once()
        mock_session.close.assert_called_once()
