from __future__ import annotations

from contextlib import asynccontextmanager
import importlib
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from api.core.contracts import ChatMessageCreatedPayload, EventEnvelope
from api.observability.events import DomainEventEmitter
from api.ops.security import OpsSecurityConfig


@pytest.fixture
async def event_db(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        from api.storage.models import Base

        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )

    @asynccontextmanager
    async def patched_db_context():
        session = async_session()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    monkeypatch.setattr("api.storage.database.get_db_context", patched_db_context)
    yield
    await engine.dispose()


@pytest.mark.asyncio
async def test_domain_event_emitter_persists_and_filters_events(event_db) -> None:
    emitter = DomainEventEmitter()

    event = await emitter.emit(
        "chat.message.created",
        source="test",
        actor_user_id="u-1",
        correlation_id="corr-1",
        payload=ChatMessageCreatedPayload(
            conversation_id="c-1",
            message_id="m-1",
            role="user",
        ),
    )

    assert event is not None
    fetched = await emitter.get_event(event.event_id)
    assert fetched is not None
    assert fetched.payload["message_id"] == "m-1"

    filtered = await emitter.list_events(
        event_type="chat.message.created",
        actor_user_id="u-1",
        correlation_id="corr-1",
        source="test",
    )
    assert [item.event_id for item in filtered] == [event.event_id]


@pytest.mark.asyncio
async def test_domain_event_emitter_fails_open(monkeypatch) -> None:
    emitter = DomainEventEmitter()
    monkeypatch.setattr(emitter, "_persist", AsyncMock(side_effect=RuntimeError("db down")))

    result = await emitter.emit(
        "chat.message.created",
        source="test",
        payload=ChatMessageCreatedPayload(
            conversation_id="c-1",
            message_id="m-1",
            role="user",
        ),
    )

    assert result is None


def test_debug_events_endpoints_return_success_envelopes(monkeypatch) -> None:
    monkeypatch.setattr(OpsSecurityConfig, "REQUIRE_AUTH", False)
    monkeypatch.setattr(OpsSecurityConfig, "RATE_LIMIT_ENABLED", False)

    app = FastAPI()
    debug_router = importlib.import_module("api.observability.debug_router")

    app.include_router(debug_router.router)
    client = TestClient(app)

    event = EventEnvelope(
        event_id="evt-1",
        event_type="chat.message.created",
        occurred_at="2026-05-29T00:00:00",
        source="test",
        actor_user_id="u-1",
        correlation_id=None,
        payload={"conversation_id": "c-1", "message_id": "m-1", "role": "assistant"},
    )
    monkeypatch.setattr(debug_router.event_emitter, "list_events", AsyncMock(return_value=[event]))
    monkeypatch.setattr(debug_router.event_emitter, "get_event", AsyncMock(return_value=event))
    assert event is not None

    list_response = client.get("/debug/events", params={"event_type": "chat.message.created"})
    assert list_response.status_code == 200
    list_body = list_response.json()
    assert list_body["success"] is True
    assert list_body["data"]["total"] == 1
    assert list_body["data"]["events"][0]["event_id"] == event.event_id

    detail_response = client.get(f"/debug/events/{event.event_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["payload"]["message_id"] == "m-1"

    monkeypatch.setattr(debug_router.event_emitter, "get_event", AsyncMock(return_value=None))
    missing_response = client.get("/debug/events/missing")
    assert missing_response.status_code == 404
