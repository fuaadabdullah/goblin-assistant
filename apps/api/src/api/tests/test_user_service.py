"""
Tests for UserService.

Uses an in-memory SQLite engine to validate actual SQLAlchemy queries,
following the pattern from test_task_store.py.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from api.storage.user_service import UserService, UserCreateData


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def _db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        from api.storage.models import Base

        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(_db_engine):
    """Yield an isolated AsyncSession backed by the in-memory SQLite engine."""
    _Session = sessionmaker(
        _db_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    session = _Session()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


# ---------------------------------------------------------------------------
# UserCreateData model
# ---------------------------------------------------------------------------


class TestUserCreateData:
    def test_creates_with_minimal_fields(self):
        data = UserCreateData(email="test@example.com")
        assert data.email == "test@example.com"
        assert data.name is None
        assert data.hashed_password is None

    def test_creates_with_all_fields(self):
        data = UserCreateData(
            email="test@example.com",
            name="Test User",
            hashed_password="hashed_pw",
            google_id="google-123",
            passkey_credential_id="cred-1",
            passkey_public_key="pub-key",
        )
        assert data.email == "test@example.com"
        assert data.name == "Test User"
        assert data.hashed_password == "hashed_pw"
        assert data.google_id == "google-123"
        assert data.passkey_credential_id == "cred-1"
        assert data.passkey_public_key == "pub-key"


# ---------------------------------------------------------------------------
# UserService
# ---------------------------------------------------------------------------


class TestUserService:
    @pytest.mark.asyncio
    async def test_create_and_get_user_by_id(self, db_session):
        service = UserService(db_session)
        data = UserCreateData(email="alice@example.com", name="Alice")
        user = await service.create_user(data)

        assert user is not None
        assert user.email == "alice@example.com"
        assert user.name == "Alice"

        fetched = await service.get_user_by_id(str(user.id))
        assert fetched is not None
        assert fetched.email == "alice@example.com"

    @pytest.mark.asyncio
    async def test_create_user_with_duplicate_email(self, db_session):
        service = UserService(db_session)
        data = UserCreateData(email="dupe@example.com", name="First")
        user = await service.create_user(data)
        assert user is not None

        data2 = UserCreateData(email="dupe@example.com", name="Second")
        user2 = await service.create_user(data2)
        assert user2 is None  # IntegrityError caught

    @pytest.mark.asyncio
    async def test_get_user_by_email(self, db_session):
        service = UserService(db_session)
        data = UserCreateData(email="bob@example.com", name="Bob")
        await service.create_user(data)

        fetched = await service.get_user_by_email("bob@example.com")
        assert fetched is not None
        assert fetched.name == "Bob"

        missing = await service.get_user_by_email("nobody@example.com")
        assert missing is None

    @pytest.mark.asyncio
    async def test_get_user_by_google_id(self, db_session):
        service = UserService(db_session)
        data = UserCreateData(
            email="googleuser@example.com",
            google_id="google-abc-123",
        )
        await service.create_user(data)

        fetched = await service.get_user_by_google_id("google-abc-123")
        assert fetched is not None
        assert fetched.email == "googleuser@example.com"

        missing = await service.get_user_by_google_id("nonexistent")
        assert missing is None

    @pytest.mark.asyncio
    async def test_get_user_by_passkey_credential_id(self, db_session):
        service = UserService(db_session)
        data = UserCreateData(
            email="passkeyuser@example.com",
            passkey_credential_id="cred-passkey-1",
            passkey_public_key="pub-key-data",
        )
        await service.create_user(data)

        fetched = await service.get_user_by_passkey_credential_id("cred-passkey-1")
        assert fetched is not None
        assert fetched.email == "passkeyuser@example.com"

        missing = await service.get_user_by_passkey_credential_id("unknown")
        assert missing is None

    @pytest.mark.asyncio
    async def test_update_user_last_login(self, db_session):
        service = UserService(db_session)
        data = UserCreateData(email="login@example.com")
        user = await service.create_user(data)
        assert user is not None

        result = await service.update_user_last_login(str(user.id))
        assert result is True

        # Verify last_login was set
        from sqlalchemy import func, select
        from api.storage.models import UserModel

        result = await db_session.execute(
            select(UserModel).where(UserModel.id == user.id)
        )
        updated = result.scalar_one_or_none()
        assert updated is not None
        assert updated.last_login is not None

    @pytest.mark.asyncio
    async def test_update_user_last_login_nonexistent(self, db_session):
        service = UserService(db_session)
        result = await service.update_user_last_login("00000000-0000-0000-0000-000000000000")
        assert result is False

    @pytest.mark.asyncio
    async def test_update_user(self, db_session):
        service = UserService(db_session)
        data = UserCreateData(email="update@example.com", name="Old Name")
        user = await service.create_user(data)
        assert user is not None

        updated = await service.update_user(str(user.id), name="New Name")
        assert updated is not None
        assert updated.name == "New Name"

        fetched = await service.get_user_by_id(str(user.id))
        assert fetched is not None
        assert fetched.name == "New Name"

    @pytest.mark.asyncio
    async def test_update_user_nonexistent(self, db_session):
        service = UserService(db_session)
        result = await service.update_user("00000000-0000-0000-0000-000000000000", name="Ghost")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_user(self, db_session):
        service = UserService(db_session)
        data = UserCreateData(email="delete@example.com")
        user = await service.create_user(data)
        assert user is not None

        result = await service.delete_user(str(user.id))
        assert result is True

        fetched = await service.get_user_by_id(str(user.id))
        assert fetched is None

    @pytest.mark.asyncio
    async def test_delete_user_nonexistent(self, db_session):
        service = UserService(db_session)
        result = await service.delete_user("00000000-0000-0000-0000-000000000000")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_all_users(self, db_session):
        service = UserService(db_session)
        await service.create_user(UserCreateData(email="u1@example.com"))
        await service.create_user(UserCreateData(email="u2@example.com"))

        users = await service.get_all_users()
        assert len(users) == 2
        emails = {u.email for u in users}
        assert emails == {"u1@example.com", "u2@example.com"}

    @pytest.mark.asyncio
    async def test_create_user_flush_only(self, db_session):
        """flush_only should not commit, but user should be visible within session."""
        service = UserService(db_session)
        data = UserCreateData(email="flush@example.com")
        user = await service.create_user(data, flush_only=True)
        assert user is not None

        fetched = await service.get_user_by_id(str(user.id))
        assert fetched is not None