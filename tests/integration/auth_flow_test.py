"""
Real integration tests for the auth flow.

These tests exercise:
- Real bcrypt password hashing
- Real JWT creation and verification
- Real SQLite DB writes for users and sessions
- Real session revocation: a token must 401 AFTER logout

The unit tests mock all of this out. Here nothing is mocked.
"""

import pytest
from sqlalchemy import select

pytestmark = pytest.mark.asyncio


async def _get_csrf(client):
    r = await client.get("/v1/auth/csrf-token")
    assert r.status_code == 200
    return r.json()["data"]["csrf_token"]


async def _register(client, email, password="TestPass123!"):
    csrf = await _get_csrf(client)
    return await client.post(
        "/v1/auth/register",
        json={"email": email, "password": password, "csrf_token": csrf},
    )


class TestRegistration:
    async def test_register_creates_user_and_session_in_db(self, client, db_session):
        """Registration must persist a bcrypt-hashed user row and an active session."""
        from api.storage.models import UserModel, UserSessionModel
        import jwt as pyjwt

        r = await _register(client, "newuser@test.example")
        assert r.status_code == 200, r.text
        data = r.json()["data"]

        assert data["access_token"]
        assert data["refresh_token"]
        user_id = data["user"]["id"]

        # Confirm user row written to test DB
        result = await db_session.execute(
            select(UserModel).where(UserModel.email == "newuser@test.example")
        )
        user = result.scalar_one()
        assert user.id == user_id
        assert user.hashed_password.startswith("$2b$")  # bcrypt signature
        assert user.is_active is True

        # Confirm session row is active
        from api.auth.router.config import SECRET_KEY, ALGORITHM
        payload = pyjwt.decode(data["access_token"], SECRET_KEY, algorithms=[ALGORITHM])
        session_id = payload["session_id"]

        sess_result = await db_session.execute(
            select(UserSessionModel).where(UserSessionModel.session_id == session_id)
        )
        session = sess_result.scalar_one()
        assert session.is_revoked is False
        assert session.user_id == user_id

    async def test_duplicate_email_rejected(self, client, db_session):
        """Second registration with the same email must fail; DB must have exactly one row."""
        from api.storage.models import UserModel

        await _register(client, "dup@test.example")
        r2 = await _register(client, "dup@test.example")
        assert r2.status_code in (400, 409), r2.text

        result = await db_session.execute(
            select(UserModel).where(UserModel.email == "dup@test.example")
        )
        rows = result.scalars().all()
        assert len(rows) == 1, "duplicate user was created"

    async def test_register_without_csrf_fails(self, client):
        """Omitting the CSRF token must be rejected at input validation."""
        r = await client.post(
            "/v1/auth/register",
            json={"email": "no-csrf@test.example", "password": "Pass123!"},
        )
        assert r.status_code in (400, 422)


class TestLogin:
    async def test_login_returns_valid_jwt_with_correct_claims(self, client, db_session):
        """Login JWT must carry type=access, a session_id, and the user's sub."""
        import jwt as pyjwt
        from api.auth.router.config import SECRET_KEY, ALGORITHM

        await _register(client, "loginuser@test.example")
        csrf = await _get_csrf(client)
        r = await client.post(
            "/v1/auth/login",
            json={"email": "loginuser@test.example", "password": "TestPass123!", "csrf_token": csrf},
        )
        assert r.status_code == 200, r.text
        access_token = r.json()["data"]["access_token"]

        payload = pyjwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["type"] == "access"
        assert "session_id" in payload
        assert "sub" in payload
        assert payload["sub"]  # non-empty user id

    async def test_wrong_password_returns_401(self, client, db_session):
        """Bad password must 401 and must not delete the user."""
        from api.storage.models import UserModel

        await _register(client, "wrongpass@test.example")
        csrf = await _get_csrf(client)
        r = await client.post(
            "/v1/auth/login",
            json={"email": "wrongpass@test.example", "password": "WRONG!", "csrf_token": csrf},
        )
        assert r.status_code == 401

        # User must still exist
        result = await db_session.execute(
            select(UserModel).where(UserModel.email == "wrongpass@test.example")
        )
        assert result.scalar_one_or_none() is not None

    async def test_nonexistent_user_returns_401(self, client):
        csrf = await _get_csrf(client)
        r = await client.post(
            "/v1/auth/login",
            json={"email": "ghost@test.example", "password": "pass", "csrf_token": csrf},
        )
        assert r.status_code == 401


class TestSessionRevocation:
    async def test_logout_revokes_session_token_401s(self, client, db_session):
        """
        The critical real-behavior test the unit suite cannot write.

        The token must 401 AFTER logout because the session row is marked
        is_revoked=True in the DB, and get_current_user checks that column.
        """
        import jwt as pyjwt
        from api.auth.router.config import SECRET_KEY, ALGORITHM
        from api.storage.models import UserSessionModel

        reg = await _register(client, "logout@test.example")
        assert reg.status_code == 200
        access_token = reg.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Before logout: token is valid
        me_before = await client.get("/v1/auth/me", headers=headers)
        assert me_before.status_code == 200, f"Expected 200 before logout, got {me_before.status_code}"

        # Logout
        logout_r = await client.post("/v1/auth/logout", headers=headers)
        assert logout_r.status_code == 200, f"Logout failed: {logout_r.text}"

        # After logout: same token must 401
        me_after = await client.get("/v1/auth/me", headers=headers)
        assert me_after.status_code == 401, (
            f"Token still valid after logout! Got {me_after.status_code}. "
            "This means session revocation is not working."
        )

        # Confirm the DB row is actually revoked
        payload = pyjwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        session_id = payload["session_id"]
        sess = await db_session.execute(
            select(UserSessionModel).where(UserSessionModel.session_id == session_id)
        )
        session = sess.scalar_one()
        assert session.is_revoked is True, "DB session row was not revoked after logout"

    async def test_get_me_requires_valid_token(self, client):
        """No token at all must return 401."""
        r = await client.get("/v1/auth/me")
        assert r.status_code == 401

    async def test_get_me_with_garbage_token_401s(self, client):
        r = await client.get("/v1/auth/me", headers={"Authorization": "Bearer garbage.token.here"})
        assert r.status_code == 401


class TestTokenRefresh:
    async def test_refresh_issues_different_access_token(self, client):
        """Refresh token flow must return a new, different access token."""
        reg = await _register(client, "refresh@test.example")
        assert reg.status_code == 200
        data = reg.json()["data"]
        original_access = data["access_token"]
        refresh_token = data["refresh_token"]

        r = await client.post(
            "/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert r.status_code == 200, f"Refresh failed: {r.text}"
        new_access = r.json()["data"]["access_token"]

        assert new_access  # non-empty
        assert new_access != original_access, "Refresh returned the same access token"

        # New token must be usable
        me = await client.get("/v1/auth/me", headers={"Authorization": f"Bearer {new_access}"})
        assert me.status_code == 200
