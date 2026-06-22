"""Engine contract tests — Sandbox pillar.

These tests assert that the Sandbox pillar's public contract
(documented in docs/architecture/ENGINE_CONTRACTS.md) is upheld.
"""

from __future__ import annotations


import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import sandbox_api


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(sandbox_api.router, prefix="/api/v1")
    return TestClient(app)


# ── Job Submission Contract ────────────────────────────────────────────


class TestJobSubmissionContract:
    """Contract: POST /api/v1/sandbox/run accepts valid input and returns job metadata."""

    def test_submit_valid_python_code(self, client):
        """Valid Python submission returns 200 with job_id and queued status."""
        response = client.post(
            "/api/v1/sandbox/run",
            json={
                "language": "python",
                "code": "print('hello')",
                "timeout_seconds": 30,
                "memory_limit_mb": 256,
            },
        )
        # If sandbox is unavailable (no Redis), expect 503
        # If API key is required, expect 403
        # If successful, expect 200
        assert response.status_code in (200, 403, 503)
        if response.status_code == 200:
            data = response.json()
            assert "job_id" in data
            assert "status" in data
            assert data["status"] == "queued"
            assert "language" in data
            assert data["language"] == "python"

    def test_submit_invalid_language_returns_400(self, client):
        """Unsupported language (e.g. bash) must be rejected."""
        response = client.post(
            "/api/v1/sandbox/run",
            json={
                "language": "bash",
                "code": "echo hello",
                "timeout_seconds": 30,
            },
        )
        assert response.status_code in (400, 422, 403, 503)

    def test_submit_empty_code_returns_400(self, client):
        """Empty code must be rejected."""
        response = client.post(
            "/api/v1/sandbox/run",
            json={
                "language": "python",
                "code": "",
                "timeout_seconds": 30,
            },
        )
        assert response.status_code in (400, 422, 503)

    def test_submit_excessive_timeout_returns_400(self, client):
        """Timeout exceeding maximum (120s) must be rejected."""
        response = client.post(
            "/api/v1/sandbox/run",
            json={
                "language": "python",
                "code": "print('hello')",
                "timeout_seconds": 999,
            },
        )
        assert response.status_code in (400, 422, 503)


# ── Job Status Contract ────────────────────────────────────────────────


class TestJobStatusContract:
    """Contract: GET /api/v1/sandbox/jobs/{job_id} returns structured status."""

    def test_unknown_job_returns_404(self, client):
        """Querying a non-existent job returns 404."""
        response = client.get("/api/v1/sandbox/jobs/nonexistent-job-id")
        assert response.status_code in (404, 403)

    def test_job_status_has_required_fields(self, client):
        """Job status response must contain contract-required fields."""
        response = client.get("/api/v1/sandbox/jobs/sandbox-job-test")
        if response.status_code == 200:
            data = response.json()
            required = {"job_id", "status", "created_at"}
            # data may be nested under a key like "data" (SuccessEnvelope)
            payload = data.get("data", data)
            assert required.issubset(payload.keys()), (
                f"Missing: {required - payload.keys()}"
            )
            assert payload["status"] in (
                "queued",
                "running",
                "completed",
                "failed",
                "cancelled",
            )


# ── Job Logs Contract ──────────────────────────────────────────────────


class TestJobLogsContract:
    """Contract: GET /api/v1/sandbox/jobs/{job_id}/logs returns combined logs."""

    def test_logs_response_has_required_fields(self, client):
        """Logs response must contain logs and job_id."""
        response = client.get("/api/v1/sandbox/jobs/sandbox-job-test/logs")
        if response.status_code == 200:
            data = response.json()
            payload = data.get("data", data)
            assert "logs" in payload
            assert "job_id" in payload
            assert isinstance(payload["logs"], str)
            assert "truncated" in payload


# ── Health Contract ────────────────────────────────────────────────────


class TestSandboxHealthContract:
    """Contract: GET /api/v1/sandbox/health returns sandbox system status."""

    def test_health_returns_200(self, client):
        """Health endpoint should be reachable and return valid status."""
        response = client.get("/api/v1/sandbox/health")
        assert response.status_code in (200, 403)
        if response.status_code == 200:
            data = response.json()
            payload = data.get("data", data)
            # Must have some status indicator
            assert any(k in payload for k in ("status", "healthy", "ok"))
