"""Email Routes auth coverage tests."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, Response
from jwt import decode

from api.auth.router import routes_email
from api.auth.router.schemas import (
    RefreshTokenRequest,
    TokenValidationRequest,
    User,
    UserCreate,
    UserLogin,
)
from api.auth.router.tokens import SECRET_KEY, create_refresh_token
from api.auth.router.tokens import create_access_token as create_real_access_token
from api.auth.router.tokens import verify_token as verify_auth_token

from .conftest import _user_model


class TestEmailRoutes:
    @pytest.mark.asyncio
    async def test_refresh_logout_and_validate_paths(self, monkeypatch):
        active_user = _user_model(passkey_public_key="pk")
        db = MagicMock()
        response = Response()

        with pytest.raises(HTTPException, match="No refresh token provided"):
            await routes_email.refresh_token_endpoint(
                RefreshTokenRequest(refresh_token=None),
                SimpleNamespace(cookies={}),
                response,
                db,
            )

        monkeypatch.setattr(routes_email, "verify_token", lambda _token: {"type": "access"})
        with pytest.raises(HTTPException, match="Invalid refresh token"):
            await routes_email.refresh_token_endpoint(
                RefreshTokenRequest(refresh_token="wrong-type"),
                SimpleNamespace(cookies={}),
                response,
                db,
            )

        valid_refresh = create_refresh_token(active_user.id, "session-1")
        monkeypatch.setattr(routes_email, "verify_token", verify_auth_token)
        monkeypatch.setattr(
            routes_email, "_get_authenticated_user_model", AsyncMock(return_value=active_user)
        )
        monkeypatch.setattr(routes_email, "create_access_token", lambda **_kwargs: "new-access")
        monkeypatch.setattr(routes_email, "create_refresh_token", lambda *_args: "new-refresh")
        set_cookies = MagicMock()
        monkeypatch.setattr(routes_email, "_set_auth_cookies", set_cookies)

        refreshed = await routes_email.refresh_token_endpoint(
            RefreshTokenRequest(refresh_token=valid_refresh),
            SimpleNamespace(cookies={}),
            response,
            db,
        )
        assert refreshed.data.access_token == "new-access"
        assert set_cookies.called

        revoke = AsyncMock()
        clear_cookies = MagicMock()
        monkeypatch.setattr(routes_email, "_db_revoke_session", revoke)
        monkeypatch.setattr(routes_email, "_clear_auth_cookies", clear_cookies)
        access_token = create_real_access_token(
            data={"sub": active_user.id}, session_id="session-1"
        )

        logged_out = await routes_email.logout(
            SimpleNamespace(cookies={"session_token": access_token}),
            response,
            User(id=active_user.id, email=active_user.email),
            None,
            db,
        )
        assert logged_out.data.message == "Logged out successfully"
        revoke.assert_awaited_once()
        assert clear_cookies.called

        monkeypatch.setattr(routes_email, "verify_token", lambda _token: None)
        invalid = await routes_email.validate_token(TokenValidationRequest(token="bad"), db)
        assert invalid.data.valid is False

        payload = decode(valid_refresh, SECRET_KEY, algorithms=["HS256"])
        access_like = create_real_access_token(data={"sub": payload["sub"]}, session_id="session-1")
        monkeypatch.setattr(
            routes_email,
            "verify_token",
            lambda _token: decode(access_like, SECRET_KEY, algorithms=["HS256"]),
        )
        user_service = MagicMock()
        user_service.get_user_by_id = AsyncMock(return_value=active_user)
        monkeypatch.setattr(routes_email._ar, "UserService", lambda _db: user_service)

        valid = await routes_email.validate_token(TokenValidationRequest(token=access_like), db)
        assert valid.data.valid is True
        assert valid.data.user.email == active_user.email

    @pytest.mark.asyncio
    async def test_validate_token_accepts_supabase_jwt_payload(self, monkeypatch):
        db = MagicMock()
        user_service = MagicMock()
        user_service.get_user_by_id = AsyncMock(return_value=None)
        user_service.get_user_by_email = AsyncMock(return_value=None)
        monkeypatch.setattr(routes_email._ar, "UserService", lambda _db: user_service)
        monkeypatch.setattr(routes_email, "verify_token", lambda _token: None)
        monkeypatch.setattr(
            routes_email,
            "verify_supabase_token",
            lambda _token: {
                "sub": "supabase-user",
                "email": "supabase@example.com",
                "user_metadata": {"name": "Supabase User"},
            },
        )

        valid = await routes_email.validate_token(TokenValidationRequest(token="supabase-jwt"), db)

        assert valid.data.valid is True
        assert valid.data.user.id == "supabase-user"
        assert valid.data.user.email == "supabase@example.com"
        assert valid.data.user.name == "Supabase User"

    @pytest.mark.asyncio
    async def test_register_login_refresh_and_validate_error_branches(self, monkeypatch):
        request = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))
        response = Response()
        db = MagicMock()

        monkeypatch.setattr(routes_email._ar, "check_rate_limit", AsyncMock(return_value=True))
        monkeypatch.setattr(routes_email._ar, "validate_csrf_token", AsyncMock(return_value=True))
        monkeypatch.setattr(routes_email, "hash_password", lambda _password: "hashed-password")

        user_service = MagicMock()
        user_service.get_user_by_email = AsyncMock(return_value=None)
        user_service.create_user = AsyncMock(return_value=None)
        user_service.update_user_last_login = AsyncMock()
        user_service.get_user_by_id = AsyncMock(return_value=None)
        monkeypatch.setattr(routes_email._ar, "UserService", lambda _db: user_service)

        with pytest.raises(HTTPException, match="Failed to create user"):
            await routes_email.register(
                UserCreate(
                    email="new@example.com",
                    password="secret",
                    name="New User",
                    csrf_token="csrf",
                ),
                request,
                response,
                db,
            )

        user_service.get_user_by_email = AsyncMock(return_value=_user_model(is_active=False))
        monkeypatch.setattr(routes_email, "verify_password", lambda *_args: True)
        with pytest.raises(HTTPException, match="inactive"):
            await routes_email.login(
                UserLogin(
                    email="new@example.com",
                    password="secret",
                    csrf_token="csrf",
                ),
                request,
                response,
                db,
            )

        monkeypatch.setattr(
            routes_email, "verify_token", lambda _token: {"type": "refresh", "sub": "user-1"}
        )
        with pytest.raises(HTTPException, match="Session has expired or been revoked"):
            await routes_email.refresh_token_endpoint(
                RefreshTokenRequest(refresh_token="refresh-token"),
                SimpleNamespace(cookies={}),
                response,
                db,
            )

        monkeypatch.setattr(
            routes_email,
            "verify_token",
            lambda _token: {"type": "refresh", "sub": "user-1", "session_id": "session-1"},
        )
        monkeypatch.setattr(
            routes_email,
            "_get_authenticated_user_model",
            AsyncMock(return_value=None),
        )
        with pytest.raises(HTTPException, match="Session has expired or been revoked"):
            await routes_email.refresh_token_endpoint(
                RefreshTokenRequest(refresh_token="refresh-token"),
                SimpleNamespace(cookies={}),
                response,
                db,
            )

        inactive_user = _user_model(is_active=False)
        monkeypatch.setattr(
            routes_email,
            "_get_authenticated_user_model",
            AsyncMock(return_value=inactive_user),
        )
        with pytest.raises(HTTPException, match="inactive"):
            await routes_email.refresh_token_endpoint(
                RefreshTokenRequest(refresh_token="refresh-token"),
                SimpleNamespace(cookies={}),
                response,
                db,
            )

        monkeypatch.setattr(routes_email, "verify_token", lambda _token: {"type": "access"})
        invalid = await routes_email.validate_token(TokenValidationRequest(token="bad"), db)
        assert invalid.data.valid is False

        monkeypatch.setattr(
            routes_email, "verify_token", lambda _token: {"type": "access", "sub": "user-1"}
        )
        monkeypatch.setattr(routes_email._ar, "UserService", lambda _db: user_service)
        user_service.get_user_by_id = AsyncMock(return_value=None)
        missing_user = await routes_email.validate_token(TokenValidationRequest(token="bad"), db)
        assert missing_user.data.valid is False

    @pytest.mark.asyncio
    async def test_register_login_refresh_logout_and_validate_success(self, monkeypatch):
        request = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"), cookies={})
        response = Response()
        db = MagicMock()
        db.commit = AsyncMock()

        user_model = _user_model(hashed_password="hashed-password", is_active=True)
        user_service = MagicMock()
        user_service.get_user_by_email = AsyncMock(return_value=None)
        user_service.create_user = AsyncMock(return_value=user_model)
        user_service.update_user_last_login = AsyncMock()
        user_service.get_user_by_id = AsyncMock(return_value=user_model)
        monkeypatch.setattr(routes_email._ar, "UserService", lambda _db: user_service)
        monkeypatch.setattr(routes_email._ar, "check_rate_limit", AsyncMock(return_value=True))
        monkeypatch.setattr(routes_email._ar, "validate_csrf_token", AsyncMock(return_value=True))
        monkeypatch.setattr(routes_email, "hash_password", lambda _password: "hashed-password")
        monkeypatch.setattr(routes_email, "verify_password", lambda *_args: True)
        monkeypatch.setattr(routes_email, "create_session_id", lambda _uid: "session-1")
        monkeypatch.setattr(routes_email, "_db_create_session", AsyncMock())
        monkeypatch.setattr(routes_email, "_db_revoke_session", AsyncMock())
        monkeypatch.setattr(routes_email, "create_access_token", lambda **_kwargs: "access-token")
        monkeypatch.setattr(routes_email, "create_refresh_token", lambda *_args: "refresh-token")
        monkeypatch.setattr(routes_email, "_set_auth_cookies", MagicMock())
        monkeypatch.setattr(routes_email, "_clear_auth_cookies", MagicMock())

        register_result = await routes_email.register(
            UserCreate(
                email="new@example.com",
                password="secret",
                name="New User",
                csrf_token="csrf",
            ),
            request,
            response,
            db,
        )
        assert register_result.data.access_token == "access-token"

        user_service.get_user_by_email = AsyncMock(return_value=user_model)
        login_result = await routes_email.login(
            UserLogin(email="new@example.com", password="secret", csrf_token="csrf"),
            request,
            response,
            db,
        )
        assert login_result.data.refresh_token == "refresh-token"

        monkeypatch.setattr(
            routes_email,
            "verify_token",
            lambda _token: {"type": "refresh", "sub": user_model.id, "session_id": "session-1"},
        )
        monkeypatch.setattr(
            routes_email,
            "_get_authenticated_user_model",
            AsyncMock(return_value=user_model),
        )
        refresh_result = await routes_email.refresh_token_endpoint(
            RefreshTokenRequest(refresh_token="refresh-token"),
            request,
            response,
            db,
        )
        assert refresh_result.data.access_token == "access-token"

        logout_request = SimpleNamespace(
            client=SimpleNamespace(host="127.0.0.1"),
            cookies={"session_token": "access-token"},
        )
        logout_result = await routes_email.logout(
            logout_request,
            response,
            User(id=user_model.id, email=user_model.email),
            None,
            db,
        )
        assert logout_result.data.message == "Logged out successfully"

        monkeypatch.setattr(
            routes_email,
            "verify_token",
            lambda _token: {"sub": user_model.id, "type": "access", "session_id": "session-1"},
        )
        validate_result = await routes_email.validate_token(
            TokenValidationRequest(token="access-token"),
            db,
        )
        assert validate_result.data.valid is True
        assert validate_result.data.user.email == user_model.email

    @pytest.mark.asyncio
    async def test_refresh_token_endpoint_issues_new_tokens(self, monkeypatch):
        """Refresh endpoint issues new tokens while maintaining session ID."""
        active_user = _user_model()
        db = MagicMock()
        response = Response()
        session_id = "session-123"

        # Create a valid refresh token
        valid_refresh = create_refresh_token(active_user.id, session_id)

        monkeypatch.setattr(routes_email, "verify_token", verify_auth_token)
        monkeypatch.setattr(
            routes_email, "_get_authenticated_user_model", AsyncMock(return_value=active_user)
        )
        set_cookies = MagicMock()
        monkeypatch.setattr(routes_email, "_set_auth_cookies", set_cookies)

        # Call the refresh endpoint
        refreshed = await routes_email.refresh_token_endpoint(
            RefreshTokenRequest(refresh_token=valid_refresh),
            SimpleNamespace(cookies={}),
            response,
            db,
        )

        # Verify new tokens were issued
        assert refreshed.data.access_token
        assert refreshed.data.refresh_token
        # Verify cookies were set with new tokens
        set_cookies.assert_called_once()
