from __future__ import annotations

from types import SimpleNamespace

from fastapi import APIRouter, FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from api.core.contracts import ErrorEnvelope
from api.core.error_types import ErrorType
from api.core.errors import DomainError
from api.main import add_contract_lifecycle_headers
from api.observability.migration_metrics import migration_metrics
from api.routes import account_router as account_module
from api.routes import support_router as support_module
from api.search_router import router as search_router


def _client() -> TestClient:
    migration_metrics.reset_for_tests()
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

    app.middleware("http")(add_contract_lifecycle_headers)
    app.include_router(search_router, prefix="/api/v1")
    app.include_router(support_module.router, prefix="/api/v1")
    app.include_router(account_module.router, prefix="/api/v1")

    app.dependency_overrides[account_module.get_current_user] = lambda: SimpleNamespace(id="u-1")

    return TestClient(app)


def test_legacy_search_route_is_not_mounted():
    client = _client()
    response = client.post("/search/query", json={"query": "hello", "collection_name": "docs"})

    assert response.status_code == 404


def test_search_v1_alias_is_stable():
    client = _client()
    response = client.post(
        "/api/v1/search/query", json={"query": "hello", "collection_name": "docs"}
    )
    assert response.status_code == 200
    assert response.headers["X-API-Lifecycle"] == "stable"


def test_support_router_error_envelope_on_validation_failure():
    client = _client()
    response = client.post("/api/v1/support/message", json={"message": ""})
    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "SUPPORT_MESSAGE_REQUIRED"


def test_account_preferences_returns_success_envelope():
    client = _client()
    response = client.put("/api/v1/account/preferences", json={"theme": "dark"})
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["theme"] == "dark"
    assert response.headers["X-API-Lifecycle"] == "stable"
    snapshot = migration_metrics.snapshot()
    assert snapshot["requests"]["total"] >= 1
    assert snapshot["lifecycle_totals"]["stable"] >= 1


def test_versioned_aliases_preserve_semantic_lifecycle_classes():
    migration_metrics.reset_for_tests()
    app = FastAPI()
    app.middleware("http")(add_contract_lifecycle_headers)

    experimental_router = APIRouter(prefix="/routing")
    internal_ops_router = APIRouter(prefix="/ops")
    internal_secrets_router = APIRouter(prefix="/secrets")
    stable_router = APIRouter(prefix="/search")

    @experimental_router.get("/providers")
    async def _experimental():
        return {"ok": True}

    @internal_ops_router.get("/aggregated")
    async def _internal_ops():
        return {"ok": True}

    @internal_secrets_router.get("/health")
    async def _internal_secrets():
        return {"ok": True}

    @stable_router.post("/query")
    async def _stable():
        return {"ok": True}

    app.include_router(experimental_router, prefix="/api/v1")
    app.include_router(internal_ops_router, prefix="/api/v1")
    app.include_router(internal_secrets_router, prefix="/api/v1")
    app.include_router(stable_router, prefix="/api/v1")

    client = TestClient(app)
    routing = client.get("/api/v1/routing/providers")
    ops = client.get("/api/v1/ops/aggregated")
    secrets = client.get("/api/v1/secrets/health")
    stable = client.post("/api/v1/search/query")

    assert routing.headers["X-API-Lifecycle"] == "experimental"
    assert ops.headers["X-API-Lifecycle"] == "internal"
    assert secrets.headers["X-API-Lifecycle"] == "internal"
    assert stable.headers["X-API-Lifecycle"] == "stable"
