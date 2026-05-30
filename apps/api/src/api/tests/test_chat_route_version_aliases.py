from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.api_router import router as api_router
from api.chat_router import router as chat_router


def test_chat_and_guest_routes_have_v1_aliases() -> None:
    app = FastAPI()
    app.include_router(chat_router)
    app.include_router(api_router)
    app.include_router(chat_router, prefix="/api/v1")
    app.include_router(api_router, prefix="/api/v1")

    paths = {route.path for route in app.routes}

    assert "/chat/conversations" in paths
    assert "/api/v1/chat/conversations" in paths
    assert "/api/chat" in paths
    assert "/api/v1/api/chat" in paths


def test_guest_chat_validation_parity_for_v1_alias() -> None:
    app = FastAPI()
    app.include_router(api_router)
    app.include_router(api_router, prefix="/api/v1")
    client = TestClient(app)

    legacy = client.post("/api/chat", json={})
    alias = client.post("/api/v1/api/chat", json={})

    assert legacy.status_code == alias.status_code


def test_chat_conversation_auth_parity_for_v1_alias() -> None:
    app = FastAPI()
    app.include_router(chat_router)
    app.include_router(chat_router, prefix="/api/v1")
    client = TestClient(app)

    legacy = client.get("/chat/conversations")
    alias = client.get("/api/v1/chat/conversations")

    assert legacy.status_code == alias.status_code
