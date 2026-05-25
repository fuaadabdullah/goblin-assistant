"""
Tests for PreferencesService.

Uses a mocked get_db_context to validate business logic without a real database.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from api.storage.preferences_service import PreferencesService, preferences_service


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_mock_prefs(**overrides):
    """Create a mock UserPreferencesModel (or None) with the given attributes."""
    defaults = {
        "id": 1,
        "user_id": "user-1",
        "default_provider": "openai",
        "default_model": "gpt-4",
        "rag_consent": "true",
        "privacy_settings": {"opt_out_analytics": False},
        "created_at": datetime(2026, 1, 1),
        "updated_at": datetime(2026, 1, 15),
    }
    merged = {**defaults, **overrides}
    mock = MagicMock()
    for attr, val in merged.items():
        setattr(mock, attr, val)
    return mock


def make_mock_session(prefs=None, rowcount=0):
    """Return a mock session that returns prefs from scalar_one_or_none."""
    session = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = prefs
    result.rowcount = rowcount

    async def async_execute(*args, **kwargs):
        return result

    session.execute = async_execute

    async def _refresh_side_effect(obj):
        """Simulate refresh by populating common ORM defaults."""
        now = datetime.utcnow()
        if not hasattr(obj, 'id') or obj.id is None:
            obj.id = 1
        if not hasattr(obj, 'created_at') or obj.created_at is None:
            obj.created_at = now
        if not hasattr(obj, 'updated_at') or obj.updated_at is None:
            obj.updated_at = now

    session.refresh = AsyncMock(side_effect=_refresh_side_effect)

    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


def create_patched_context(session):
    """Create a patched get_db_context context manager yielding session."""

    @asynccontextmanager
    async def fake_context():
        yield session

    return fake_context


class TestPreferencesService:
    @pytest.mark.asyncio
    async def test_get_preferences_returns_dict_when_found(self):
        mock_prefs = make_mock_prefs(user_id="user-1")
        session = make_mock_session(prefs=mock_prefs)

        with patch(
            "api.storage.preferences_service.get_db_context",
            create_patched_context(session),
        ):
            result = await PreferencesService.get_preferences("user-1")

        assert result is not None
        assert result["user_id"] == "user-1"
        assert result["default_provider"] == "openai"
        assert result["rag_consent"] is True
        assert "created_at" in result

    @pytest.mark.asyncio
    async def test_get_preferences_returns_none_when_missing(self):
        session = make_mock_session(prefs=None)

        with patch(
            "api.storage.preferences_service.get_db_context",
            create_patched_context(session),
        ):
            result = await PreferencesService.get_preferences("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_preferences_rag_consent_false(self):
        mock_prefs = make_mock_prefs(rag_consent="false")
        session = make_mock_session(prefs=mock_prefs)

        with patch(
            "api.storage.preferences_service.get_db_context",
            create_patched_context(session),
        ):
            result = await PreferencesService.get_preferences("user-r")

        assert result is not None
        assert result["rag_consent"] is False

    @pytest.mark.asyncio
    async def test_create_or_update_preferences_creates_new(self):
        session = make_mock_session(prefs=None)
        add_mock = MagicMock()
        session.add = add_mock

        with patch(
            "api.storage.preferences_service.get_db_context",
            create_patched_context(session),
        ):
            result = await PreferencesService.create_or_update_preferences(
                user_id="new-user",
                default_provider="anthropic",
                rag_consent=True,
            )

        assert result["user_id"] == "new-user"
        assert result["default_provider"] == "anthropic"
        assert result["rag_consent"] is True
        add_mock.assert_called_once()
        # The mock prefs won't have id after refresh, but the method handles it
        assert session.flush.await_count == 1
        assert session.refresh.await_count == 1

    @pytest.mark.asyncio
    async def test_create_or_update_preferences_updates_existing(self):
        mock_prefs = make_mock_prefs(user_id="existing-user", default_provider="openai")
        session = make_mock_session(prefs=mock_prefs)

        with patch(
            "api.storage.preferences_service.get_db_context",
            create_patched_context(session),
        ):
            result = await PreferencesService.create_or_update_preferences(
                user_id="existing-user",
                default_provider="anthropic",
                default_model="claude-3",
            )

        assert result["default_provider"] == "anthropic"
        assert result["default_model"] == "claude-3"
        assert mock_prefs.default_provider == "anthropic"
        assert mock_prefs.default_model == "claude-3"

    @pytest.mark.asyncio
    async def test_create_or_update_preferences_partial_update(self):
        mock_prefs = make_mock_prefs(
            user_id="partial",
            default_provider="openai",
            default_model="gpt-4",
            rag_consent="false",
        )
        session = make_mock_session(prefs=mock_prefs)

        with patch(
            "api.storage.preferences_service.get_db_context",
            create_patched_context(session),
        ):
            result = await PreferencesService.create_or_update_preferences(
                user_id="partial",
                rag_consent=True,
            )

        assert result["default_provider"] == "openai"  # unchanged
        assert result["rag_consent"] is True  # updated

    @pytest.mark.asyncio
    async def test_delete_preferences_returns_true(self):
        session = make_mock_session(rowcount=1)

        with patch(
            "api.storage.preferences_service.get_db_context",
            create_patched_context(session),
        ):
            result = await PreferencesService.delete_preferences("user-1")

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_preferences_returns_false(self):
        session = make_mock_session(rowcount=0)

        with patch(
            "api.storage.preferences_service.get_db_context",
            create_patched_context(session),
        ):
            result = await PreferencesService.delete_preferences("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_update_rag_consent_delegates(self):
        mock_prefs = make_mock_prefs(user_id="user-r")
        session = make_mock_session(prefs=mock_prefs)

        with patch(
            "api.storage.preferences_service.get_db_context",
            create_patched_context(session),
        ):
            result = await PreferencesService.update_rag_consent("user-r", True)

        assert result["rag_consent"] is True

    @pytest.mark.asyncio
    async def test_has_rag_consent_true(self):
        mock_prefs = make_mock_prefs(rag_consent="true")
        session = make_mock_session(prefs=mock_prefs)

        with patch(
            "api.storage.preferences_service.get_db_context",
            create_patched_context(session),
        ):
            result = await PreferencesService.has_rag_consent("user-1")

        assert result is True

    @pytest.mark.asyncio
    async def test_has_rag_consent_false(self):
        mock_prefs = make_mock_prefs(rag_consent="false")
        session = make_mock_session(prefs=mock_prefs)

        with patch(
            "api.storage.preferences_service.get_db_context",
            create_patched_context(session),
        ):
            result = await PreferencesService.has_rag_consent("user-1")

        assert result is False

    @pytest.mark.asyncio
    async def test_has_rag_consent_false_when_no_prefs(self):
        session = make_mock_session(prefs=None)

        with patch(
            "api.storage.preferences_service.get_db_context",
            create_patched_context(session),
        ):
            result = await PreferencesService.has_rag_consent("unknown")

        assert result is False


class TestPreferencesServiceSingleton:
    def test_singleton_instance(self):
        assert preferences_service is not None
        assert isinstance(preferences_service, PreferencesService)