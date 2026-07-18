"""Decode And Requests sandbox API runtime tests."""

from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from .conftest import sandbox_api


def test_decode_helpers_cover_empty_and_numeric_exit_code() -> None:
    decoded = sandbox_api._decode_job_data({b"status": b"finished", b"exit_code": b"7"})
    assert decoded == {"status": "finished", "exit_code": "7"}
    assert sandbox_api._parse_exit_code(decoded) == 7
    assert sandbox_api._parse_exit_code({"status": "finished"}) is None

    status = sandbox_api._job_status("job-1", decoded | {"created_at": "now"})
    summary = sandbox_api._job_summary(decoded | {"job_id": "job-1", "created_at": "now"})
    assert status.job_id == "job-1"
    assert summary.job_id == "job-1"


def test_sandbox_health_http_response_uses_success_envelope() -> None:
    app = FastAPI()
    app.include_router(sandbox_api.router, prefix="/api/v1")
    client = TestClient(app)

    with patch.object(sandbox_api, "SANDBOX_ENABLED", False):
        response = client.get("/api/v1/sandbox/health/status")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "disabled"
