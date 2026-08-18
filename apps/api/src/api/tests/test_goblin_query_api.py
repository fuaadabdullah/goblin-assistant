from __future__ import annotations

import inspect
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Iterable

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import api_router
from api.api_models import GoblinHistoryEntry
from api.auth.router.dependencies import get_readonly_db
from api.exception_handlers import register_exception_handlers
from api.services.goblin_query_service import (
    GoblinQueryService,
    build_goblin_query_service,
)


class FakeGoblinHistoryRepository:
    def __init__(self, entries: Iterable[GoblinHistoryEntry] = ()):
        self.entries = list(entries)

    async def list_history(self, *, user_id: str, goblin_id: str, scan_limit: int):
        assert user_id == "user-1"
        assert scan_limit > 0
        return [entry for entry in self.entries if entry.goblin_id == goblin_id]


class FailingGoblinHistoryRepository:
    async def list_history(self, *, user_id: str, goblin_id: str, scan_limit: int):
        del user_id, goblin_id, scan_limit
        raise RuntimeError("repository offline")


def _service(repo) -> GoblinQueryService:
    return build_goblin_query_service(
        user_id="user-1",
        history_repository=repo,
        stats_repository=repo,
    )


def _client(service: GoblinQueryService | None = None) -> TestClient:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(api_router.router, prefix="/api/v1")
    if service is not None:
        app.dependency_overrides[api_router.get_goblin_query_service] = lambda: service
    return TestClient(app)


def _entry(
    entry_id: str,
    *,
    goblin_id: str = "coding",
    minutes_ago: int = 0,
    status: str = "completed",
) -> GoblinHistoryEntry:
    return GoblinHistoryEntry(
        id=entry_id,
        goblin_id=goblin_id,
        task=f"task {entry_id}",
        response=f"response {entry_id}",
        timestamp=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
        status=status,
        kpis=f"status:{status}",
    )


def test_get_goblins_returns_bounded_stable_catalog():
    client = _client(_service(FakeGoblinHistoryRepository()))

    response = client.get("/api/v1/api/goblins")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["limit"] == 100
    assert data["order"] == "catalog_order"
    assert [item["id"] for item in data["items"]] == [
        "research",
        "coding",
        "finance",
        "strategy",
        "operations",
        "general",
    ]
    assert data["items"][0]["status"] == "active"
    assert "provider" not in data["items"][0]


def test_get_history_returns_newest_first_page():
    entries = [_entry("old", minutes_ago=10), _entry("new", minutes_ago=1)]
    client = _client(_service(FakeGoblinHistoryRepository(entries)))

    response = client.get("/api/v1/api/history/coding?limit=1")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["limit"] == 1
    assert data["order"] == "newest_first"
    assert data["items"][0]["id"] == "new"
    assert data["next_cursor"]


def test_empty_repository_history_returns_empty_collection():
    client = _client(_service(FakeGoblinHistoryRepository()))

    response = client.get("/api/v1/api/history/coding")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["items"] == []
    assert body["data"]["total"] == 0


def test_unknown_goblin_uses_canonical_404_envelope():
    client = _client(_service(FakeGoblinHistoryRepository()))

    response = client.get("/api/v1/api/history/unknown")

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "GOBLIN_NOT_FOUND"
    assert body["error"]["details"] == {"goblin_id": "unknown"}


def test_invalid_limit_uses_validation_envelope():
    client = _client(_service(FakeGoblinHistoryRepository()))

    response = client.get("/api/v1/api/history/coding?limit=0")

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_repository_failure_uses_canonical_500_envelope():
    client = _client(_service(FailingGoblinHistoryRepository()))

    response = client.get("/api/v1/api/stats/coding")

    assert response.status_code == 500
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "GOBLIN_STATS_REPOSITORY_FAILED"


def test_stats_have_explicit_window_and_null_unavailable_metrics():
    client = _client(
        _service(
            FakeGoblinHistoryRepository(
                [_entry("ok"), _entry("failed", status="failed"), _entry("outside", minutes_ago=90)]
            )
        )
    )

    response = client.get("/api/v1/api/stats/coding?window_hours=1")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["goblin_id"] == "coding"
    assert data["window"]["hours"] == 1
    assert data["counters"] == {
        "total_tasks": 2,
        "completed_tasks": 1,
        "failed_tasks": 1,
    }
    assert data["latency"]["average_duration_ms"] is None
    assert data["total_cost"] is None


def test_goblin_query_routes_require_authorization_without_override():
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(api_router.router, prefix="/api/v1")

    async def _readonly_db():
        yield SimpleNamespace()

    app.dependency_overrides[get_readonly_db] = _readonly_db
    client = TestClient(app)

    for path in (
        "/api/v1/api/goblins",
        "/api/v1/api/history/coding",
        "/api/v1/api/stats/coding",
    ):
        response = client.get(path)
        assert response.status_code == 401
        assert response.json()["success"] is False


def test_openapi_schema_has_typed_200_responses_and_no_501():
    app = FastAPI()
    app.include_router(api_router.router, prefix="/api/v1")
    schema = app.openapi()

    goblins_get = schema["paths"]["/api/v1/api/goblins"]["get"]
    history_get = schema["paths"]["/api/v1/api/history/{goblin_id}"]["get"]
    stats_get = schema["paths"]["/api/v1/api/stats/{goblin_id}"]["get"]

    assert "501" not in goblins_get["responses"]
    assert "501" not in history_get["responses"]
    assert "501" not in stats_get["responses"]
    assert (
        goblins_get["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/GoblinListSuccessResponse"
    )
    assert (
        history_get["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/GoblinHistorySuccessResponse"
    )
    assert (
        stats_get["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/GoblinStatsSuccessResponse"
    )
    # Verify the envelope shape is present in the schema components
    assert "success" in schema["components"]["schemas"]["GoblinListSuccessResponse"]["properties"]
    assert "data" in schema["components"]["schemas"]["GoblinListSuccessResponse"]["properties"]


def test_api_router_does_not_import_storage_for_goblin_reads():
    router_source = inspect.getsource(api_router)

    goblin_route_source = router_source[router_source.index('@router.get("/goblins"') :]
    assert "api.storage" not in goblin_route_source
    assert "from .storage" not in goblin_route_source


def test_cursor_following_returns_next_page():
    entries = [_entry(f"e{i}", minutes_ago=i) for i in range(5)]
    client = _client(_service(FakeGoblinHistoryRepository(entries)))

    first = client.get("/api/v1/api/history/coding?limit=3").json()["data"]
    assert len(first["items"]) == 3
    assert first["next_cursor"]

    second = client.get(f"/api/v1/api/history/coding?limit=3&cursor={first['next_cursor']}").json()[
        "data"
    ]
    assert len(second["items"]) == 2
    assert second["next_cursor"] is None
    assert second["items"][0]["id"] not in {item["id"] for item in first["items"]}


def test_malformed_cursor_returns_400_domain_error():
    client = _client(_service(FakeGoblinHistoryRepository([_entry("x")])))

    response = client.get("/api/v1/api/history/coding?cursor=not@@a-valid-cursor!!")

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "GOBLIN_HISTORY_CURSOR_INVALID"


def test_stats_window_hours_below_minimum_returns_422():
    client = _client(_service(FakeGoblinHistoryRepository()))

    response = client.get("/api/v1/api/stats/coding?window_hours=0")

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_stats_window_hours_above_maximum_returns_422():
    client = _client(_service(FakeGoblinHistoryRepository()))

    response = client.get("/api/v1/api/stats/coding?window_hours=8761")

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_history_limit_above_maximum_returns_422():
    client = _client(_service(FakeGoblinHistoryRepository()))

    response = client.get("/api/v1/api/history/coding?limit=101")

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
