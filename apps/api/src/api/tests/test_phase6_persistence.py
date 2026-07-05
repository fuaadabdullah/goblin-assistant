from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.storage.models import Base, UserModel
from api.storage.saas_service import SaaSSettingsService


@pytest_asyncio.fixture
async def db_session(tmp_path):
    db_path = tmp_path / "phase6.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


async def _seed_user(session, user_id: str = "user-1", email: str = "user@example.com"):
    user = UserModel(id=user_id, email=email, name="Test User", is_active=True)
    session.add(user)
    await session.commit()
    return user


@pytest.mark.asyncio
async def test_account_preferences_round_trip(db_session):
    await _seed_user(db_session)
    service = SaaSSettingsService(db_session)

    saved = await service.save_account_preferences(
        "user-1",
        {
            "summaries": False,
            "notifications_enabled": False,
            "familyMode": True,
            "theme": "dark",
            "language": "en",
            "other": {"beta": True},
        },
    )

    assert saved["summaries"] is False
    assert saved["notifications_enabled"] is False
    assert saved["familyMode"] is True

    loaded = await service.get_account_preferences("user-1")
    assert loaded is not None
    assert loaded["summaries"] is False
    assert loaded["familyMode"] is True
    assert loaded["other"] == {"beta": True}


@pytest.mark.asyncio
async def test_provider_settings_and_global_settings_persist(db_session):
    service = SaaSSettingsService(db_session)

    row = await service.upsert_provider_settings(
        "openai",
        {
            "endpoint": "https://api.openai.com",
            "base_url": "https://api.openai.com",
            "enabled": True,
            "priority": 10,
            "weight": 1.5,
            "models": ["gpt-4o-mini"],
            "api_key": "sk-test",
        },
    )

    assert row.provider_name == "openai"
    assert row.api_key_encrypted
    assert await service.get_provider_api_key("openai") == "sk-test"

    global_setting = await service.set_global_setting("default_model", "gpt-4o-mini")
    assert global_setting == {"key": "default_model", "value": "gpt-4o-mini"}
    assert await service.get_global_setting("default_model") == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_support_notifications_and_flags_persist(db_session):
    await _seed_user(db_session)
    service = SaaSSettingsService(db_session)

    ticket = await service.create_support_ticket(
        {
            "user_id": "user-1",
            "email": "user@example.com",
            "category": "bug",
            "priority": "P2",
            "message": "Something broke",
            "metadata": {"source": "test"},
        }
    )
    assert ticket.ticket_id
    assert ticket.status == "received"

    notification = await service.create_notification(
        {
            "user_id": "user-1",
            "title": "Welcome",
            "body": "Hello there",
            "metadata": {"source": "test"},
        }
    )
    assert notification.notification_id
    assert notification.is_read is False

    flag = await service.upsert_feature_flag(
        "new-dashboard",
        {
            "enabled": True,
            "user_overrides": {"user-1": False},
            "target_roles": ["admin"],
            "metadata": {"owner": "platform"},
        },
    )
    assert flag.flag_key == "new-dashboard"
    resolved = await service.resolve_feature_flag("new-dashboard", user_id="user-1")
    assert resolved is not None
    assert resolved["enabled"] is False
