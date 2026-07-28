"""Dependencies auth coverage tests."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from api.auth.router import dependencies as deps
from api.auth.router.schemas import User

from .conftest import _auth_request, _FakeDb, _FakeExecuteResult, _user_model


class TestAuthDependencies:
    def test_is_user_active_variants(self):
        assert deps._is_user_active(True) is True
        assert deps._is_user_active("YES") is True
        assert deps._is_user_active(1) is True
        assert deps._is_user_active("off") is False
        assert deps._is_user_active(None) is False

    @pytest.mark.asyncio
    async def test_get_authenticated_user_model_paths(self):
        active_user = _user_model()
        active_session = SimpleNamespace(is_revoked=False)
        revoked_session = SimpleNamespace(is_revoked=True)

        db = _FakeDb(
            [
                _FakeExecuteResult(first=(active_user, active_session)),
                _FakeExecuteResult(first=(active_user, revoked_session)),
                _FakeExecuteResult(first=None),
                _FakeExecuteResult(scalar=active_user),
            ]
        )

        assert (
            await deps._get_authenticated_user_model(
                db, user_id=active_user.id, session_id="session-1"
            )
            is active_user
        )
        assert (
            await deps._get_authenticated_user_model(
                db, user_id=active_user.id, session_id="session-2"
            )
            is None
        )
        assert (
            await deps._get_authenticated_user_model(
                db, user_id=active_user.id, session_id="session-3"
            )
            is None
        )
        assert (
            await deps._get_authenticated_user_model(db, user_id=active_user.id, session_id=None)
            is active_user
        )

    @pytest.mark.asyncio
    async def test_get_current_user_error_and_cache_paths(self, monkeypatch):
        request = _auth_request()
        db = MagicMock()

        with pytest.raises(HTTPException, match="Not authenticated"):
            await deps.get_current_user(request, db, credentials=None)

        monkeypatch.setattr(deps, "verify_token", lambda _token: None)
        with pytest.raises(HTTPException, match="Invalid authentication credentials"):
            await deps.get_current_user(request, db, credentials=SimpleNamespace(credentials="bad"))

        monkeypatch.setattr(deps, "verify_token", lambda _token: {"type": "refresh"})
        with pytest.raises(HTTPException, match="Invalid token type"):
            await deps.get_current_user(
                request, db, credentials=SimpleNamespace(credentials="refresh")
            )

        monkeypatch.setattr(deps, "verify_token", lambda _token: {"type": "access"})
        with pytest.raises(HTTPException, match="Invalid token payload"):
            await deps.get_current_user(
                request, db, credentials=SimpleNamespace(credentials="missing-sub")
            )

        inactive_request = _auth_request()
        inactive_user = _user_model(is_active=False)
        monkeypatch.setattr(
            deps,
            "verify_token",
            lambda _token: {"type": "access", "sub": inactive_user.id, "session_id": "sid"},
        )
        monkeypatch.setattr(
            deps,
            "_get_authenticated_user_model",
            AsyncMock(return_value=inactive_user),
        )
        with pytest.raises(HTTPException, match="inactive"):
            await deps.get_current_user(
                inactive_request,
                db,
                credentials=SimpleNamespace(credentials="access"),
            )

        cached_model = _user_model(passkey_public_key="pk")
        cached_request = _auth_request(
            state=SimpleNamespace(
                auth_user=cached_model,
                auth_user_id=cached_model.id,
                auth_session_id="sid",
            )
        )
        fetcher = AsyncMock()
        monkeypatch.setattr(
            deps,
            "verify_token",
            lambda _token: {"type": "access", "sub": cached_model.id, "session_id": "sid"},
        )
        monkeypatch.setattr(deps, "_get_authenticated_user_model", fetcher)

        user = await deps.get_current_user(
            cached_request,
            db,
            credentials=SimpleNamespace(credentials="access"),
        )

        assert isinstance(user, User)
        assert user.id == cached_model.id
        fetcher.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_supabase_provision_and_get_current_user_paths(self, monkeypatch):
        db = SimpleNamespace(
            execute=AsyncMock(
                side_effect=[
                    _FakeExecuteResult(scalar=None),
                    _FakeExecuteResult(scalar=None),
                    _FakeExecuteResult(scalar=None),
                ]
            ),
            add=MagicMock(),
            commit=AsyncMock(),
            refresh=AsyncMock(),
        )

        provisioned_user = _user_model(id="supabase-user", email="supabase@example.com")
        db.execute = AsyncMock(
            side_effect=[
                _FakeExecuteResult(scalar=None),
                _FakeExecuteResult(scalar=None),
                _FakeExecuteResult(scalar=None),
            ]
        )

        async def fake_provision(_db, _payload):
            return provisioned_user

        monkeypatch.setattr(deps, "_provision_supabase_user", fake_provision)
        monkeypatch.setattr(deps, "verify_token", lambda _token: None)
        monkeypatch.setattr(
            deps,
            "verify_supabase_token",
            lambda _token: {"sub": "supabase-user", "email": "supabase@example.com"},
        )

        class _Ctx:
            async def __aenter__(self):
                return db

            async def __aexit__(self, exc_type, exc, tb):
                return False

        monkeypatch.setattr(deps, "get_db_context", _Ctx)

        request = _auth_request()
        user = await deps.get_current_user(
            request,
            db,
            credentials=SimpleNamespace(credentials="supabase-token"),
        )

        assert user.id == "supabase-user"
        assert request.state.auth_user_id == "supabase-user"

    @pytest.mark.asyncio
    async def test_get_authenticated_user_model_provision_and_revoke_paths(self, monkeypatch):
        write_db = SimpleNamespace(
            execute=AsyncMock(return_value=_FakeExecuteResult(scalar=None)),
            add=MagicMock(),
            commit=AsyncMock(),
            refresh=AsyncMock(),
        )

        monkeypatch.setattr(deps.uuid, "uuid4", lambda: "generated-user")

        result = await deps._provision_supabase_user(
            write_db,
            {"sub": "", "email": "new@example.com", "user_metadata": {"name": "New User"}},
        )

        assert result is not None
        assert result.email == "new@example.com"
        assert write_db.add.called
        write_db.commit.assert_awaited_once()
        write_db.refresh.assert_awaited_once()
