"""Error-detail regressions for observability debug routers."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.observability import (
    debug_context_router,
    debug_retrieval_router,
    debug_system_router,
    debug_write_router,
)


@pytest.fixture(autouse=True)
def _disable_ops_auth(monkeypatch):
    monkeypatch.setattr("api.ops.security.OpsSecurityConfig.REQUIRE_AUTH", False)
    monkeypatch.setattr("api.ops.security.OpsSecurityConfig.ENVIRONMENT", "development")
    monkeypatch.setattr(
        "api.ops.security.OpsSecurityConfig.OPS_ALLOWED_ENVIRONMENTS", ["development"]
    )
    monkeypatch.setattr(
        "api.ops.security.ops_security.check_environment_access", AsyncMock(return_value=True)
    )
    monkeypatch.setattr("api.ops.security.ops_security.log_audit_event", AsyncMock())
    yield


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(debug_context_router.router, prefix="/api/v1")
    app.include_router(debug_retrieval_router.router, prefix="/api/v1")
    app.include_router(debug_system_router.router, prefix="/api/v1")
    app.include_router(debug_write_router.router, prefix="/api/v1")
    return TestClient(app, raise_server_exceptions=False)


def test_context_snapshot_failure_detail(client):
    with patch(
        "api.observability.debug_context_router.context_snapshotter.get_context_snapshot",
        AsyncMock(side_effect=Exception("boom")),
    ):
        response = client.get("/api/v1/context/snapshot/request-1")

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to get context snapshot: boom"


def test_retrieval_trace_failure_detail(client):
    with patch(
        "api.observability.debug_retrieval_router.retrieval_tracer.get_retrieval_trace",
        AsyncMock(side_effect=Exception("boom")),
    ):
        response = client.get("/api/v1/retrieval/trace/request-1")

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to get retrieval trace: boom"


def test_observability_summary_failure_detail(client):
    with patch(
        "api.observability.debug_system_router.decision_logger.get_decision_stats",
        AsyncMock(side_effect=Exception("boom")),
    ):
        response = client.get("/api/v1/system/observability/summary")

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to get observability summary: boom"


def test_observability_tool_trace_failure_detail(client):
    with patch(
        "api.observability.debug_system_router.tool_tracer.get_tool_trace",
        side_effect=Exception("boom"),
    ):
        response = client.get("/api/v1/tool-trace/request-1")

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to get tool trace: boom"


def test_write_decisions_failure_detail(client):
    with patch(
        "api.observability.debug_write_router.decision_logger.get_decision_history",
        AsyncMock(side_effect=Exception("boom")),
    ):
        response = client.get("/api/v1/write/decisions/conv-1")

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to get write decisions: boom"


def test_memory_health_failure_detail(client):
    with patch(
        "api.observability.debug_write_router.memory_promotion_logger.get_memory_health_report",
        AsyncMock(side_effect=Exception("boom")),
    ):
        response = client.get("/api/v1/memory/health/user-1")

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to get memory health: boom"
