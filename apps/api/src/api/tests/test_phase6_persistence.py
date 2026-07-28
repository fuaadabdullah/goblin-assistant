from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.storage.models import (
    ApiKeyModel,
    Base,
    ChatSettingsModel,
    NotificationModel,
    SupportTicketModel,
    UserModel,
    UserPreferencesModel,
)
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
async def test_account_profile_handles_missing_and_updates_existing_user(db_session):
    service = SaaSSettingsService(db_session)

    assert await service.get_account_profile("missing-user") is None
    with pytest.raises(LookupError, match="user-not-found"):
        await service.save_account_profile(
            "missing-user",
            name="No One",
            email="nobody@example.com",
        )

    await _seed_user(db_session)

    saved = await service.save_account_profile(
        "user-1",
        name="Updated User",
        email="updated@example.com",
    )

    assert saved == {
        "id": "user-1",
        "email": "updated@example.com",
        "name": "Updated User",
        "avatar_url": None,
    }
    assert await service.get_account_profile("user-1") == saved


@pytest.mark.asyncio
async def test_chat_settings_round_trip_and_partial_update(db_session):
    service = SaaSSettingsService(db_session)

    assert await service.get_chat_settings("user-1") is None

    created = await service.save_chat_settings(
        "user-1",
        {
            "default_provider": "openai",
            "default_model": "gpt-4o-mini",
            "system_prompt": "Be concise.",
            "temperature": 0.2,
            "max_tokens": 512,
            "summary_enabled": False,
            "metadata": {"source": "test"},
        },
    )

    assert created["default_provider"] == "openai"
    assert created["summary_enabled"] is False
    assert created["metadata"] == {"source": "test"}

    updated = await service.save_chat_settings(
        "user-1",
        {
            "default_model": "gpt-4.1-mini",
            "metadata": {"source": "update"},
        },
    )

    assert updated["default_provider"] == "openai"
    assert updated["default_model"] == "gpt-4.1-mini"
    assert updated["metadata"] == {"source": "update"}


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
async def test_provider_settings_list_update_and_missing_key_paths(db_session):
    service = SaaSSettingsService(db_session)

    assert await service.get_provider_api_key("missing") is None

    created = await service.upsert_provider_settings(
        "anthropic",
        {"enabled": False, "api_key": "sk-original", "metadata": {"tier": "paid"}},
    )
    encrypted_key = created.api_key_encrypted

    updated = await service.upsert_provider_settings(
        "anthropic",
        {
            "priority": 4,
            "weight": 2.0,
            "models": [],
            "metadata": {"tier": "enterprise"},
        },
    )

    assert updated.enabled is False
    assert updated.priority == 4
    assert updated.weight == 2.0
    assert updated.models == []
    assert updated.metadata_ == {"tier": "enterprise"}
    assert updated.api_key_encrypted == encrypted_key
    assert await service.get_provider_api_key("anthropic") == "sk-original"

    names = {row.provider_name for row in await service.list_provider_settings()}
    assert names == {"anthropic"}


@pytest.mark.asyncio
async def test_global_setting_handles_missing_and_non_json_values(db_session):
    service = SaaSSettingsService(db_session)

    assert await service.get_global_setting("unknown") is None

    saved = await service.set_global_setting("opaque", None)

    assert saved["key"] == "opaque"
    assert saved["value"] == {"value": None}
    assert await service.get_global_setting("opaque") == saved["value"]


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


@pytest.mark.asyncio
async def test_notifications_can_be_listed_and_marked_read(db_session):
    await _seed_user(db_session)
    service = SaaSSettingsService(db_session)

    assert await service.mark_notification_read("missing") is None

    first = await service.create_notification(
        {
            "user_id": "user-1",
            "title": "First",
            "body": "First body",
        }
    )
    second = await service.create_notification(
        {
            "user_id": "user-1",
            "title": "Second",
            "body": "Second body",
            "channel": "email",
            "category": "account",
        }
    )

    listed = await service.list_notifications("user-1")
    assert {notification.notification_id for notification in listed} == {
        first.notification_id,
        second.notification_id,
    }

    read = await service.mark_notification_read(first.notification_id)
    assert read is not None
    assert read.is_read is True
    assert read.read_at is not None


@pytest.mark.asyncio
async def test_feature_flags_resolve_absent_role_and_default_branches(db_session):
    service = SaaSSettingsService(db_session)

    assert await service.resolve_feature_flag("missing") is None

    await service.upsert_feature_flag(
        "admin-console",
        {
            "enabled": False,
            "default_value": {"variant": "control"},
            "rollout_percent": 25,
            "target_users": ["user-1"],
            "target_roles": ["admin"],
        },
    )

    role_enabled = await service.resolve_feature_flag("admin-console", role="admin")
    assert role_enabled is not None
    assert role_enabled["enabled"] is True
    assert role_enabled["default_value"] == {"variant": "control"}
    assert role_enabled["rollout_percent"] == 25
    assert role_enabled["target_users"] == ["user-1"]

    default_disabled = await service.resolve_feature_flag("admin-console", role="member")
    assert default_disabled is not None
    assert default_disabled["enabled"] is False


@pytest.mark.asyncio
async def test_delete_user_data_reports_deleted_domain_rows(db_session):
    await _seed_user(db_session)
    service = SaaSSettingsService(db_session)

    db_session.add_all(
        [
            UserPreferencesModel(user_id="user-1"),
            ChatSettingsModel(user_id="user-1"),
            ApiKeyModel(
                user_id="user-1",
                provider_name="openai",
                ciphertext="encrypted",
            ),
            SupportTicketModel(
                user_id="user-1",
                email="user@example.com",
                message="Please delete my data",
            ),
            NotificationModel(
                user_id="user-1",
                title="Delete request",
                body="Queued",
            ),
        ]
    )
    await db_session.commit()

    counts = await service.delete_user_data("user-1")

    assert counts == {
        "preferences": 1,
        "chat_settings": 1,
        "api_keys": 1,
        "notifications": 1,
        "support_tickets": 1,
    }
    for model in (
        UserPreferencesModel,
        ChatSettingsModel,
        ApiKeyModel,
        NotificationModel,
        SupportTicketModel,
    ):
        result = await db_session.execute(select(model))
        assert result.scalars().all() == []
