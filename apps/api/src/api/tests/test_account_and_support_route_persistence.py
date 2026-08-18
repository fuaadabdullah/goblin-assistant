from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.auth.router import User, get_current_user, get_readonly_db
from api.core.contracts import ErrorEnvelope
from api.core.error_types import ErrorType
from api.core.errors import DomainError
from api.routes import account_router as account_module
from api.routes import support_router as support_module
from api.storage.database import get_db
from api.storage.models import (
    Base,
    NotificationModel,
    SupportTicketModel,
    UserModel,
    UserPreferencesModel,
)


@pytest_asyncio.fixture
async def db_session(tmp_path):
    db_path = Path(tmp_path) / "account_support.db"
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


def _build_app(session, *, user: User | None = None) -> FastAPI:
    app = FastAPI()

    @app.exception_handler(DomainError)
    async def _domain_error_handler(_, exc: DomainError):
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorEnvelope(
                error={
                    "code": exc.code,
                    "type": ErrorType.BUSINESS_LOGIC,
                    "message": exc.message,
                    "details": exc.details,
                }
            ).model_dump(exclude_none=True),
        )

    app.include_router(account_module.router, prefix="/api/v1")
    app.include_router(support_module.router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[get_readonly_db] = lambda: session
    if user is not None:
        app.dependency_overrides[get_current_user] = lambda: user
    return app


@pytest.mark.asyncio
async def test_account_preferences_requires_auth(db_session):
    app = _build_app(db_session)
    client = TestClient(app)

    response = client.get("/api/v1/account/preferences")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


@pytest.mark.asyncio
async def test_account_preferences_round_trip_persists_to_db(db_session):
    current_user = User(id="u-account", email="account@example.com")
    app = _build_app(db_session, user=current_user)
    client = TestClient(app)

    payload = {
        "theme": "dark",
        "default_model": "gpt-4o-mini",
        "default_provider": "openai",
        "notifications_enabled": False,
        "summaries": False,
        "familyMode": True,
        "language": "es",
        "other": {"beta": True},
    }

    update_response = client.put("/api/v1/account/preferences", json=payload)
    assert update_response.status_code == 200
    update_body = update_response.json()["data"]
    assert update_body["theme"] == "dark"
    assert update_body["default_model"] == "gpt-4o-mini"
    assert update_body["notifications_enabled"] is False
    assert update_body["summaries"] is False
    assert update_body["familyMode"] is True
    assert update_body["other"] == {"beta": True}

    get_response = client.get("/api/v1/account/preferences")
    assert get_response.status_code == 200
    get_body = get_response.json()["data"]
    assert get_body == update_body

    result = await db_session.execute(
        select(UserPreferencesModel).where(UserPreferencesModel.user_id == current_user.id)
    )
    prefs = result.scalar_one()
    assert prefs.default_model == "gpt-4o-mini"
    assert prefs.default_provider == "openai"
    assert prefs.ui_preferences["theme"] == "dark"
    assert prefs.ui_preferences["notifications"] is False
    assert prefs.privacy_settings == {"beta": True}


@pytest.mark.asyncio
async def test_support_message_persists_ticket_metadata(db_session):
    app = _build_app(db_session)
    client = TestClient(app)

    payload = {
        "message": "Something broke in production",
        "email": "support@example.com",
        "category": "bug",
    }

    response = client.post("/api/v1/support/message", json=payload)
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["id"]
    assert body["status"] == "received"
    assert body["timestamp"]

    result = await db_session.execute(
        select(SupportTicketModel).where(SupportTicketModel.message == payload["message"])
    )
    ticket = result.scalar_one()
    assert ticket.email == "support@example.com"
    assert ticket.category == "bug"
    assert ticket.subject == "Bug"
    assert ticket.metadata_ == {"source": "support_form"}


@pytest.mark.asyncio
async def test_support_message_links_known_user_and_creates_notification(db_session):
    current_user = UserModel(id="u-support", email="member@example.com", is_active=True)
    db_session.add(current_user)
    await db_session.commit()

    app = _build_app(db_session)
    client = TestClient(app)

    payload = {
        "message": "Please help with billing",
        "email": "member@example.com",
        "category": "account",
    }

    response = client.post("/api/v1/support/message", json=payload)
    assert response.status_code == 200

    ticket_result = await db_session.execute(
        select(SupportTicketModel).where(SupportTicketModel.message == payload["message"])
    )
    ticket = ticket_result.scalar_one()
    assert ticket.user_id == current_user.id

    notification_result = await db_session.execute(
        select(NotificationModel).where(NotificationModel.user_id == current_user.id)
    )
    notification = notification_result.scalar_one()
    assert notification.title == "Support request received"
    assert notification.category == "support"
    assert notification.metadata_ == {
        "source": "support_form",
        "support_ticket_id": ticket.ticket_id,
        "support_category": "account",
    }


@pytest.mark.asyncio
async def test_beta_signal_persists_support_ticket_metadata(db_session):
    app = _build_app(db_session)
    client = TestClient(app)

    payload = {
        "page": "/chat",
        "name": "Ava",
        "email": "ava@example.com",
        "note": "Which model am I using?",
        "tag": "which-model",
    }

    response = client.post("/api/v1/support/beta-signal", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "logged"
    assert body["id"]

    result = await db_session.execute(
        select(SupportTicketModel).where(SupportTicketModel.category == "beta_signal")
    )
    ticket = result.scalar_one()
    assert ticket.message == "Which model am I using?"
    assert ticket.subject == "Pilot signal: which-model"
    assert ticket.email == "ava@example.com"
    assert ticket.metadata_ == {
        "source": "beta_signal",
        "page": "/chat",
        "tag": "which-model",
        "name": "Ava",
        "email": "ava@example.com",
        "user_agent": "testclient",
    }


@pytest.mark.asyncio
async def test_support_message_surfaces_5xx_on_persistence_failure(db_session):
    app = _build_app(db_session)
    client = TestClient(app)

    with patch(
        "api.routes.support_router.SaaSSettingsService.create_support_ticket",
        new_callable=AsyncMock,
        side_effect=RuntimeError("db offline"),
    ):
        response = client.post("/api/v1/support/message", json={"message": "Need help"})

    assert response.status_code == 500
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "SUPPORT_SUBMIT_FAILED"
    assert body["error"]["details"]["reason"] == "db offline"
