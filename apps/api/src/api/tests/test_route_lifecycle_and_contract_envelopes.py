from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from api.core.contracts import ErrorEnvelope
from api.core.errors import DomainError
from api.routes import account_router as account_module
from api.routes import support_router as support_module
from api.search_router import router as search_router
from api.main import add_contract_lifecycle_headers
from api.observability.migration_metrics import migration_metrics


def _client() -> TestClient:
    migration_metrics.reset_for_tests()
    app = FastAPI()

    @app.exception_handler(DomainError)
    async def _domain_error_handler(_, exc: DomainError):
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorEnvelope(
                error={"code": exc.code, "message": exc.message, "details": exc.details}
            ).model_dump(exclude_none=True),
        )

    app.middleware("http")(add_contract_lifecycle_headers)
    app.include_router(search_router)
    app.include_router(support_module.router)
    app.include_router(account_module.router)
    app.include_router(search_router, prefix="/api/v1")
    app.include_router(support_module.router, prefix="/api/v1")
    app.include_router(account_module.router, prefix="/api/v1")

    app.dependency_overrides[account_module.get_current_user] = lambda: SimpleNamespace(id="u-1")

    return TestClient(app)


def test_search_route_returns_success_envelope_and_lifecycle_headers():
    client = _client()
    response = client.post("/search/query", json={"query": "hello", "collection_name": "docs"})

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert "data" in response.json()
    assert response.headers["X-API-Lifecycle"] == "legacy"
    assert response.headers["Deprecation"] == "true"
    assert response.headers["Sunset"] == "2026-12-31T00:00:00Z"


def test_search_v1_alias_is_stable():
    client = _client()
    response = client.post(
        "/api/v1/search/query", json={"query": "hello", "collection_name": "docs"}
    )
    assert response.status_code == 200
    assert response.headers["X-API-Lifecycle"] == "stable"


def test_support_router_error_envelope_on_validation_failure():
    client = _client()
    response = client.post("/support/message", json={"message": ""})
    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "SUPPORT_MESSAGE_REQUIRED"


def test_account_preferences_returns_success_envelope():
    client = _client()
    response = client.put("/account/preferences", json={"theme": "dark"})
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["theme"] == "dark"
    assert response.headers["X-API-Lifecycle"] == "legacy"
    snapshot = migration_metrics.snapshot()
    assert snapshot["requests"]["total"] >= 1
    assert snapshot["lifecycle_totals"]["legacy"] >= 1
