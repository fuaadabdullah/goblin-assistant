from fastapi import FastAPI
from fastapi.routing import APIRouter
from fastapi.testclient import TestClient

from api.api_router import router as api_router
from api.bootstrap.middleware import rewrite_legacy_path_to_v1
from api.chat_router import router as chat_router
from api.route_mounting import mount_versioned_primary_routes


def test_public_routes_are_registered_once_under_v1_prefix() -> None:
    app = FastAPI()
    app.include_router(chat_router, prefix="/api/v1")
    app.include_router(api_router, prefix="/api/v1")

    paths = {route.path for route in app.routes}

    assert "/api/v1/chat/conversations" in paths
    assert "/api/v1/api/chat" in paths
    assert "/chat/conversations" not in paths
    assert "/api/chat" not in paths


def test_guest_chat_validation_parity_for_v1_alias() -> None:
    app = FastAPI()
    app.middleware("http")(rewrite_legacy_path_to_v1)
    app.include_router(api_router, prefix="/api/v1")
    client = TestClient(app)

    legacy = client.post("/api/chat", json={})
    alias = client.post("/api/v1/api/chat", json={})

    assert legacy.status_code == alias.status_code


def test_chat_conversation_auth_parity_for_v1_alias() -> None:
    app = FastAPI()
    app.middleware("http")(rewrite_legacy_path_to_v1)
    app.include_router(chat_router, prefix="/api/v1")
    client = TestClient(app)

    legacy = client.get("/chat/conversations")
    alias = client.get("/api/v1/chat/conversations")

    assert legacy.status_code == alias.status_code


def test_mount_versioned_primary_routes_includes_all_public_v1_routes() -> None:
    app = FastAPI()

    def _mk_router(prefix: str, route: str):
        sub = APIRouter(prefix=prefix)

        @sub.get(route)
        async def _handler():
            return {"ok": True}

        return sub

    health = _mk_router("", "/health")
    settings = _mk_router("/settings", "/")
    providers = _mk_router("", "/providers/models")
    chat = _mk_router("/chat", "/conversations")
    api = _mk_router("/api", "/chat")
    auth = _mk_router("/auth", "/login")
    search = _mk_router("/search", "/query")
    sandbox = _mk_router("/sandbox", "/run")
    account = _mk_router("/account", "/profile")
    support = _mk_router("/support", "/message")
    raptor = _mk_router("/raptor", "/status")
    api_keys = _mk_router("/api-keys", "/provider")
    privacy = _mk_router("/api/privacy", "/export")

    mount_versioned_primary_routes(
        app,
        health_router=health,
        settings_router=settings,
        providers_models_router=providers,
        chat_router=chat,
        api_router=api,
        auth_router=auth,
        search_router=search,
        sandbox_router=sandbox,
        account_router=account,
        support_router=support,
        raptor_router=raptor,
        api_keys_router=api_keys,
        privacy_router=privacy,
    )

    paths = {route.path for route in app.routes}
    assert "/api/v1/health" in paths
    assert "/api/v1/settings/" in paths
    assert "/api/v1/providers/models" in paths
    assert "/api/v1/chat/conversations" in paths
    assert "/api/v1/api/chat" in paths
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/search/query" in paths
    assert "/api/v1/sandbox/run" in paths
    assert "/api/v1/account/profile" in paths
    assert "/api/v1/support/message" in paths
    assert "/api/v1/raptor/status" in paths
    assert "/api/v1/api-keys/provider" in paths
    assert "/api/v1/api/privacy/export" in paths
    assert "/chat/conversations" not in paths
    assert "/api/chat" not in paths
