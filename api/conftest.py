import pytest
from fastapi.testclient import TestClient
import sys
import os
from contextlib import contextmanager

# Ensure the package root (apps/goblin-assistant) is on sys.path so relative imports work
pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, pkg_root)


@pytest.fixture(autouse=True)
def in_memory_conversation_store():
    from api.storage.conversations import (
        InMemoryConversationStore,
        conversation_store,
    )

    original_store = conversation_store._store
    conversation_store._store = InMemoryConversationStore()

    try:
        yield conversation_store._store
    finally:
        conversation_store._store = original_store


@pytest.fixture
def client():
    # Import using package name so relative imports resolve inside the 'api' package
    from importlib import import_module

    mod = import_module("api.main")
    app = getattr(mod, "app")

    with TestClient(app) as client:
        yield client


@contextmanager
def _build_authenticated_client(user_id: str, email: str):
    from importlib import import_module
    import redis.asyncio as redis
    from api.auth.router import User, get_current_user
    from api import semantic_chat_router
    from api.services import embedding_service
    from api.services.embedding_service import AsyncEmbeddingWorker

    mod = import_module("api.main")
    app = getattr(mod, "app")

    async def override_current_user():
        return User(id=user_id, email=email)

    original_semantic_worker = semantic_chat_router.embedding_worker
    original_service_worker = embedding_service.embedding_worker
    fresh_worker = AsyncEmbeddingWorker()
    fresh_rate_limiter_client = None

    app.dependency_overrides[get_current_user] = override_current_user
    semantic_chat_router.embedding_worker = fresh_worker
    embedding_service.embedding_worker = fresh_worker

    if hasattr(mod, "rate_limiter"):
        fresh_rate_limiter_client = redis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379"),
            decode_responses=True,
        )
        mod.rate_limiter.redis_client = fresh_rate_limiter_client

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        if fresh_rate_limiter_client is not None:
            try:
                import asyncio

                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                loop.run_until_complete(fresh_rate_limiter_client.aclose())
            except Exception:
                pass
        app.dependency_overrides.pop(get_current_user, None)
        semantic_chat_router.embedding_worker = original_semantic_worker
        embedding_service.embedding_worker = original_service_worker


@pytest.fixture
def authenticated_client():
    with _build_authenticated_client("test-user", "test@example.com") as test_client:
        yield test_client


@pytest.fixture
def other_authenticated_client():
    with _build_authenticated_client(
        "other-user", "other@example.com"
    ) as test_client:
        yield test_client
