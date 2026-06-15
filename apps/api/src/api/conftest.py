import os
import sys
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

# Ensure the package root (apps/goblin-assistant) is on sys.path so relative imports work
pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, pkg_root)
sys.modules.setdefault("conftest", sys.modules[__name__])

# Set test environment BEFORE any app imports
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")


@pytest.fixture(autouse=True)
def set_local_llm_api_key(monkeypatch):
    """Ensure LOCAL_LLM_API_KEY is always set so the auth middleware doesn't 500."""
    if not os.getenv("LOCAL_LLM_API_KEY"):
        monkeypatch.setenv("LOCAL_LLM_API_KEY", "test-local-llm-key")


@pytest.fixture(autouse=True)
def in_memory_conversation_store():
    from api.storage.conversations import conversation_store

    store = conversation_store._store
    if hasattr(store, "_conversations"):
        store._conversations.clear()
    elif hasattr(store, "clear"):
        store.clear()

    try:
        yield store
    finally:
        if hasattr(store, "_conversations"):
            store._conversations.clear()
        elif hasattr(store, "clear"):
            store.clear()


@pytest.fixture
def client(monkeypatch):
    # Main app routes include AuthenticationMiddleware; provide a deterministic
    # test key unless a caller explicitly sets one.
    if not os.getenv("LOCAL_LLM_API_KEY"):
        monkeypatch.setenv("LOCAL_LLM_API_KEY", "test-local-llm-key")

    # Import using package name so relative imports resolve inside the 'api' package
    from importlib import import_module

    mod = import_module("api.main")
    app = getattr(mod, "app")

    with TestClient(app) as client:
        yield client


@contextmanager
def _build_authenticated_client(user_id: str, email: str):
    from importlib import import_module

    from api.auth.router import User, get_current_user
    from api.services import embedding_service
    from api.services.embedding_service import AsyncEmbeddingWorker

    mod = import_module("api.main")
    app = getattr(mod, "app")
    original_local_llm_key = os.getenv("LOCAL_LLM_API_KEY")
    if not original_local_llm_key:
        os.environ["LOCAL_LLM_API_KEY"] = "test-local-llm-key"

    async def override_current_user():
        return User(id=user_id, email=email)

    original_service_worker = embedding_service.embedding_worker
    fresh_worker = AsyncEmbeddingWorker()

    app.dependency_overrides[get_current_user] = override_current_user
    embedding_service.embedding_worker = fresh_worker

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        embedding_service.embedding_worker = original_service_worker
        if original_local_llm_key is None:
            os.environ.pop("LOCAL_LLM_API_KEY", None)


@pytest.fixture
def authenticated_client():
    with _build_authenticated_client("test-user", "test@example.com") as test_client:
        yield test_client


@pytest.fixture
def other_authenticated_client():
    with _build_authenticated_client("other-user", "other@example.com") as test_client:
        yield test_client
