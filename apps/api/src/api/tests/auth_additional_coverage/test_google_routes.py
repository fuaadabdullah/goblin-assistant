"""Google Routes auth coverage tests."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, Response

from api.auth.router import routes_google
from api.auth.router.schemas import GoogleAuthCallback, GoogleAuthRequest

from .conftest import _user_model


class TestGoogleRoutes:
    @pytest.mark.asyncio
    async def test_issue_google_session_tokens_existing_and_linked_user(self, monkeypatch):
        committed = {"count": 0}

        async def commit():
            committed["count"] += 1

        db = SimpleNamespace(commit=AsyncMock(side_effect=commit))
        response = Response()

        linked_user = _user_model(email="user@example.com", google_id=None)
        existing_google_user = _user_model(email="google@example.com", google_id="gid")

        user_service = MagicMock()
        user_service.get_user_by_google_id = AsyncMock(side_effect=[existing_google_user, None])
        user_service.get_user_by_email = AsyncMock(return_value=linked_user)
        user_service.update_user = AsyncMock()
        user_service.create_user = AsyncMock()
        user_service.update_user_last_login = AsyncMock()

        monkeypatch.setattr(routes_google._ar, "UserService", lambda _db: user_service)
        monkeypatch.setattr(routes_google, "create_session_id", lambda _uid: "session-1")
        monkeypatch.setattr(routes_google, "_db_create_session", AsyncMock())
        monkeypatch.setattr(routes_google, "create_access_token", lambda **_kwargs: "access-token")
        monkeypatch.setattr(routes_google, "create_refresh_token", lambda *_args: "refresh-token")
        set_cookies = MagicMock()
        monkeypatch.setattr(routes_google, "_set_auth_cookies", set_cookies)

        direct = await routes_google._issue_google_session_tokens(
            {"email": "google@example.com", "sub": "gid", "name": "Google User"},
            db,
            response,
        )
        linked = await routes_google._issue_google_session_tokens(
            {"email": "user@example.com", "sub": "new-google-id", "name": "Linked User"},
            db,
            response,
        )

        assert direct.data.user.email == "google@example.com"
        assert linked.data.user.email == "user@example.com"
        assert committed["count"] == 2
        assert user_service.update_user.await_count == 1
        assert set_cookies.call_count == 2

    @pytest.mark.asyncio
    async def test_issue_google_session_tokens_error_paths(self, monkeypatch):
        db = SimpleNamespace(commit=AsyncMock())
        response = Response()

        with pytest.raises(HTTPException, match="Invalid Google user data"):
            await routes_google._issue_google_session_tokens({"email": "missing-sub"}, db, response)

        inactive_user = _user_model(google_id="gid", is_active=False)
        failing_service = MagicMock()
        failing_service.get_user_by_google_id = AsyncMock(return_value=inactive_user)
        failing_service.get_user_by_email = AsyncMock(return_value=None)
        failing_service.create_user = AsyncMock(return_value=None)
        failing_service.update_user_last_login = AsyncMock()
        monkeypatch.setattr(routes_google._ar, "UserService", lambda _db: failing_service)

        with pytest.raises(HTTPException, match="inactive"):
            await routes_google._issue_google_session_tokens(
                {"email": "inactive@example.com", "sub": "gid", "name": "Inactive"},
                db,
                response,
            )

    @pytest.mark.asyncio
    async def test_google_route_wrappers(self, monkeypatch):
        db = MagicMock()
        response = Response()

        monkeypatch.setattr(
            routes_google.GoogleOAuth,
            "verify_token",
            AsyncMock(return_value={"email": "user@example.com", "sub": "gid", "name": "User"}),
        )
        monkeypatch.setattr(
            routes_google,
            "_issue_google_session_tokens",
            AsyncMock(return_value=SimpleNamespace(ok=True)),
        )
        result = await routes_google.google_auth(GoogleAuthRequest(token="token"), response, db)
        assert result.ok is True

        monkeypatch.setattr(
            routes_google.GoogleOAuth, "get_authorization_url", lambda: "https://google"
        )
        assert (await routes_google.get_google_auth_url())["authorization_url"] == "https://google"

        monkeypatch.setattr(
            routes_google.GoogleOAuth,
            "get_authorization_url",
            lambda: (_ for _ in ()).throw(ValueError("missing config")),
        )
        with pytest.raises(HTTPException, match="missing config"):
            await routes_google.get_google_auth_url()

        monkeypatch.setattr(
            routes_google.GoogleOAuth,
            "exchange_code_for_token",
            AsyncMock(return_value={"access_token": "token"}),
        )
        monkeypatch.setattr(
            routes_google.GoogleOAuth,
            "get_user_info",
            AsyncMock(return_value={"email": "user@example.com", "sub": "gid", "name": "User"}),
        )
        monkeypatch.setattr(
            routes_google,
            "_issue_google_session_tokens",
            AsyncMock(return_value=SimpleNamespace(done=True)),
        )
        callback_result = await routes_google.google_auth_callback(
            GoogleAuthCallback(code="code"),
            response,
            db,
        )
        assert callback_result.done is True

        monkeypatch.setattr(
            routes_google.GoogleOAuth,
            "exchange_code_for_token",
            AsyncMock(return_value=None),
        )
        with pytest.raises(HTTPException, match="Failed to exchange code"):
            await routes_google.google_auth_callback(GoogleAuthCallback(code="bad"), response, db)

    @pytest.mark.asyncio
    async def test_google_auth_with_invalid_token(self, monkeypatch):
        """P2: GoogleOAuth.verify_token returning None should raise 401."""
        response = Response()
        db = MagicMock()

        monkeypatch.setattr(
            routes_google.GoogleOAuth,
            "verify_token",
            AsyncMock(return_value=None),
        )

        with pytest.raises(HTTPException) as exc_info:
            await routes_google.google_auth(GoogleAuthRequest(token="invalid"), response, db)

        assert exc_info.value.status_code == 401
        assert "Invalid Google token" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_google_auth_callback_preserves_exception_message(self, monkeypatch):
        """Callback exceptions should preserve the underlying error text."""
        response = Response()
        db = MagicMock()

        monkeypatch.setattr(
            routes_google.GoogleOAuth,
            "exchange_code_for_token",
            AsyncMock(side_effect=RuntimeError("callback backend unavailable")),
        )

        with pytest.raises(HTTPException) as exc_info:
            await routes_google.google_auth_callback(GoogleAuthCallback(code="bad"), response, db)

        assert exc_info.value.status_code == 401
        assert (
            str(exc_info.value.detail)
            == "Google authentication failed: callback backend unavailable"
        )
