"""
Shared fixtures for real integration tests.

These tests use the full app (create_app()), a real SQLite in-memory DB,
and real JWT tokens obtained through the actual auth flow. Only LLM provider
network calls are intercepted — routing, auth, storage, and sanitization all run real.

Env vars are set here BEFORE any api.* imports so that database.py and
auth/router/config.py read the right values at module import time.
"""

import os

# Must be set before api.* imports — read at import time by auth/router/config.py
os.environ["JWT_SECRET_KEY"] = "integration-test-secret-key-min-32-chars!!"
# Disables pgvector so Base.metadata.create_all works on SQLite
os.environ["USE_PGVECTOR"] = "false"
# InMemoryConversationStore (no DATABASE_URL + non-prod env) for chat router
os.environ["ENVIRONMENT"] = "test"
os.environ.setdefault("LOCAL_LLM_API_KEY", "test-local-llm-key")
# Point the module-level engine at in-memory SQLite for lifespan init_db
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

import pytest
import pytest_asyncio
import httpx
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


@pytest_asyncio.fixture
async def test_engine():
    """Fresh SQLite in-memory engine with full schema per test."""
    from api.storage.models import Base
    # Also import vector_models to ensure those tables (MemoryFactModel, EmbeddingModel,
    # ConversationSummaryModel) are registered with Base before create_all.
    import api.storage.vector_models as _vm  # noqa: F401 — registers models
    _vm.add_vector_relationships()

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    """Per-test DB session that rolls back at the end for isolation."""
    factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def app(db_session):
    """Full application with auth DB dependencies overridden to the test engine."""
    from api.app_factory import create_app
    from api.storage.database import get_db, get_readonly_db

    application = create_app()

    async def _override_db():
        yield db_session

    application.dependency_overrides[get_db] = _override_db
    application.dependency_overrides[get_readonly_db] = _override_db
    yield application
    application.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app):
    """Async HTTP client wired to the test app via ASGI transport."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


async def _get_csrf(client: httpx.AsyncClient) -> str:
    """Helper: fetch a real CSRF token from the in-memory fallback store."""
    r = await client.get("/v1/auth/csrf-token")
    assert r.status_code == 200, f"CSRF fetch failed: {r.text}"
    return r.json()["data"]["csrf_token"]


async def _register(client: httpx.AsyncClient, email: str, password: str = "TestPass123!"):
    csrf = await _get_csrf(client)
    r = await client.post(
        "/v1/auth/register",
        json={"email": email, "password": password, "csrf_token": csrf},
    )
    return r


@pytest_asyncio.fixture
async def registered_user(client):
    """A registered user with valid tokens, ready for use in tests."""
    r = await _register(client, "integration@test.example")
    assert r.status_code == 200, f"Registration failed: {r.text}"
    data = r.json()["data"]
    return {
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "user": data["user"],
    }


@pytest_asyncio.fixture
async def auth_headers(registered_user):
    return {"Authorization": f"Bearer {registered_user['access_token']}"}


@pytest_asyncio.fixture
async def conversation(client, auth_headers):
    """A conversation owned by the registered user."""
    r = await client.post(
        "/v1/chat/conversations",
        json={"title": "Integration Test Conversation"},
        headers=auth_headers,
    )
    assert r.status_code == 200, f"Conversation creation failed: {r.text}"
    return r.json()["data"]
