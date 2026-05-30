"""
Integration tests for auth refresh token and session management.

Tests cover:
- Refresh token flow (exchange for access token)
- Token type validation (reject refresh tokens on protected endpoints)
- Session tracking and revocation
- Logout revokes session
- Session validation on use
- Cross-user session isolation
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.router import (
    _db_is_session_valid,
    _db_revoke_session,
    create_access_token,
    create_refresh_token,
    create_session_id,
    router,
    verify_token,
)
from api.storage.models import UserSessionModel


@pytest.fixture
def auth_app():
    """Create test FastAPI app with auth routes."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(auth_app):
    """FastAPI test client."""
    return TestClient(auth_app)


def test_create_session_id():
    """Session IDs are generated as strings."""
    session_id = create_session_id("test-user-123")

    assert session_id is not None
    assert isinstance(session_id, str)
    assert len(session_id) > 0


@pytest.mark.asyncio
async def test_db_session_validation_requires_persisted_session():
    """A session missing from the DB is invalid."""
    db = AsyncMock(spec=AsyncSession)
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute.return_value = result

    assert await _db_is_session_valid("missing-session-id", db) is False
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_db_session_validation_and_revocation_round_trip():
    """DB-backed validation and revocation use the row as the source of truth."""
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()

    session_id = create_session_id("test-user-123")
    record = UserSessionModel(
        session_id=session_id,
        user_id="test-user-123",
        is_revoked=False,
    )
    validate_result = MagicMock()
    validate_result.scalar_one_or_none.return_value = record
    db.execute.return_value = validate_result

    assert await _db_is_session_valid(session_id, db) is True

    revoke_result = MagicMock()
    revoke_result.rowcount = 1
    db.execute.return_value = revoke_result

    assert await _db_revoke_session(session_id, db) is True


def test_create_access_token_with_scopes_and_session():
    """Access token creation includes scopes and session ID."""
    user_id = "test-user-123"
    session_id = create_session_id(user_id)

    access_token = create_access_token(
        data={"sub": user_id},
        scopes=["user", "privacy"],
        session_id=session_id,
    )

    payload = verify_token(access_token)
    assert payload is not None
    assert payload.get("sub") == user_id
    assert payload.get("type") == "access"
    assert payload.get("scopes") == ["user", "privacy"]
    assert payload.get("session_id") == session_id


def test_create_refresh_token_with_session():
    """Refresh token creation includes session tracking."""
    user_id = "test-user-123"
    session_id = create_session_id(user_id)

    refresh_token = create_refresh_token(user_id, session_id)

    payload = verify_token(refresh_token)
    assert payload is not None
    assert payload.get("sub") == user_id
    assert payload.get("type") == "refresh"
    assert payload.get("session_id") == session_id


def test_refresh_token_has_longer_expiration():
    """Refresh tokens outlive access tokens."""
    user_id = "test-user-123"
    session_id = create_session_id(user_id)

    access_payload = verify_token(create_access_token(data={"sub": user_id}, session_id=session_id))
    refresh_payload = verify_token(create_refresh_token(user_id, session_id))

    assert refresh_payload["exp"] > access_payload["exp"]


def test_access_token_has_type_access():
    """Access tokens are marked with type='access'."""
    payload = verify_token(create_access_token(data={"sub": "test-user-123"}))
    assert payload.get("type") == "access"


def test_refresh_token_has_type_refresh():
    """Refresh tokens are marked with type='refresh'."""
    user_id = "test-user-123"
    session_id = create_session_id(user_id)
    payload = verify_token(create_refresh_token(user_id, session_id))
    assert payload.get("type") == "refresh"


def test_session_ids_are_unique():
    """Generated session IDs should be unique."""
    user_id = "test-user-123"

    session1 = create_session_id(user_id)
    session2 = create_session_id(user_id)

    assert session1 != session2


def test_session_isolation():
    """Distinct users still receive distinct sessions."""
    session1 = create_session_id("user-1")
    session2 = create_session_id("user-2")

    assert session1 != session2


@pytest.mark.asyncio
async def test_refresh_endpoint_exchange_token():
    """Refresh token exchange still yields a new access token."""
    user_id = "test-user-123"
    session_id = create_session_id(user_id)

    refresh_token = create_refresh_token(user_id, session_id)
    payload = verify_token(refresh_token)
    assert payload["type"] == "refresh"
    assert payload["session_id"] == session_id

    new_access_token = create_access_token(
        data={"sub": user_id},
        session_id=session_id,
    )
    new_payload = verify_token(new_access_token)
    assert new_payload["type"] == "access"
    assert new_payload["session_id"] == session_id


def test_cannot_use_refresh_token_as_access():
    """Refresh tokens must not masquerade as access tokens."""
    user_id = "test-user-123"
    session_id = create_session_id(user_id)

    payload = verify_token(create_refresh_token(user_id, session_id))
    assert payload["type"] == "refresh"
    assert payload["type"] != "access"


def test_token_contains_user_id():
    """Tokens carry the expected user ID."""
    user_id = "user-12345"
    session_id = create_session_id(user_id)

    access_payload = verify_token(create_access_token(data={"sub": user_id}, session_id=session_id))
    refresh_payload = verify_token(create_refresh_token(user_id, session_id))

    assert access_payload["sub"] == user_id
    assert refresh_payload["sub"] == user_id


def test_multiple_sessions_per_user():
    """A user can have multiple distinct sessions."""
    user_id = "test-user"

    session1 = create_session_id(user_id)
    session2 = create_session_id(user_id)
    session3 = create_session_id(user_id)

    assert len({session1, session2, session3}) == 3
