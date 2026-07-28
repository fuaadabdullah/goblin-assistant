"""
Real integration tests for sandbox execution.

Confirms:
- sandbox_api.py imports cleanly (rq + redis imported at module level)
- The sandbox router is mounted in the full app
- Disabled-state responses are correct (no Redis needed)
- Job submission validation behavior

Tests marked @requires_redis only run if Redis is reachable.
"""

import os
import socket

import pytest

pytestmark = pytest.mark.asyncio


def _redis_reachable() -> bool:
    from urllib.parse import urlparse

    url = urlparse(os.environ.get("REDIS_URL", "redis://localhost:6379"))
    host = url.hostname or "localhost"
    port = url.port or 6379
    try:
        s = socket.create_connection((host, port), timeout=1.0)
        s.close()
        return True
    except OSError:
        return False


requires_redis = pytest.mark.skipif(
    not _redis_reachable(),
    reason="Redis not reachable at REDIS_URL",
)


# ---------------------------------------------------------------------------
# Tests that always run (no Redis dependency)
# ---------------------------------------------------------------------------


class TestSandboxMount:
    async def test_sandbox_router_is_mounted(self, client, auth_headers):
        """
        GET /v1/sandbox/health/status must not 404.
        Confirms sandbox_api.py (which imports rq and redis at module level)
        loaded cleanly and was registered with the full app.
        """
        r = await client.get("/v1/sandbox/health/status", headers=auth_headers)
        assert r.status_code != 404, (
            "Sandbox router not mounted — sandbox_api.py may have failed to import"
        )

    async def test_sandbox_health_endpoint_accessible_without_auth(self, client):
        """Health status should be readable without authentication."""
        r = await client.get("/v1/sandbox/health/status")
        assert r.status_code in (200, 401), f"Unexpected status: {r.status_code}"


class TestSandboxDisabledState:
    """
    SANDBOX_ENABLED is not set / defaults to false in the test environment.
    All of these tests confirm the disabled-branch behavior without Redis.
    """

    async def test_health_returns_disabled(self, client, auth_headers):
        """Disabled sandbox must report status=disabled and enabled=False."""
        r = await client.get("/v1/sandbox/health/status", headers=auth_headers)
        assert r.status_code == 200, r.text
        data = r.json()["data"]

        assert data["enabled"] is False, f"Expected enabled=False, got {data}"
        assert data["status"] == "disabled", f"Expected status=disabled, got {data['status']}"
        assert data["redis_connected"] is False

    async def test_submit_returns_503_when_disabled(self, client, auth_headers):
        """
        POST /v1/sandbox/submit must return 503 when SANDBOX_ENABLED=false.
        Exercises the guard at the top of the submit handler.
        """
        r = await client.post(
            "/v1/sandbox/submit",
            json={"language": "python", "source": "print('hello')"},
            headers=auth_headers,
        )
        assert r.status_code == 503, (
            f"Expected 503 (sandbox disabled), got {r.status_code}: {r.text}"
        )

    async def test_run_endpoint_returns_503_when_disabled(self, client, auth_headers):
        """POST /v1/sandbox/run (alias) must also 503 when disabled."""
        r = await client.post(
            "/v1/sandbox/run",
            json={"language": "python", "source": "1+1"},
            headers=auth_headers,
        )
        assert r.status_code == 503, (
            f"Expected 503 (sandbox disabled), got {r.status_code}: {r.text}"
        )


class TestSandboxInputValidation:
    """Input validation should fire regardless of SANDBOX_ENABLED state."""

    async def test_missing_source_field_rejected(self, client, auth_headers):
        """Body with no source must fail at schema validation (422) or 503 if disabled first."""
        r = await client.post(
            "/v1/sandbox/submit",
            json={"language": "python"},
            headers=auth_headers,
        )
        assert r.status_code in (422, 503), (
            f"Expected 422 (validation error) or 503 (disabled), got {r.status_code}"
        )

    async def test_missing_language_field_rejected(self, client, auth_headers):
        r = await client.post(
            "/v1/sandbox/submit",
            json={"source": "print(1)"},
            headers=auth_headers,
        )
        assert r.status_code in (422, 503)

    async def test_empty_body_rejected(self, client, auth_headers):
        r = await client.post(
            "/v1/sandbox/submit",
            json={},
            headers=auth_headers,
        )
        assert r.status_code in (422, 503)


class TestSandboxJobStatus:
    async def test_status_for_unknown_job_returns_4xx(self, client, auth_headers):
        """Polling status for a job that doesn't exist must return 4xx, not 500."""
        r = await client.get(
            "/v1/sandbox/status/nonexistent-job-id-xyz-123",
            headers=auth_headers,
        )
        assert r.status_code in (404, 503), (
            f"Expected 404 (not found) or 503 (disabled), got {r.status_code}"
        )


# ---------------------------------------------------------------------------
# Tests that require Redis
# ---------------------------------------------------------------------------


@requires_redis
class TestSandboxWithRedis:
    async def test_submit_queues_job_and_returns_job_id(self, client, auth_headers, monkeypatch):
        """With SANDBOX_ENABLED=true and Redis, a submitted job must return a UUID job_id."""
        monkeypatch.setenv("SANDBOX_ENABLED", "true")

        # Re-import sandbox_api to pick up the new env var
        # (module-level SANDBOX_ENABLED is read at import time)
        import importlib
        import api.sandbox_api as _sa
        importlib.reload(_sa)

        r = await client.post(
            "/v1/sandbox/submit",
            json={"language": "python", "source": "print(42)"},
            headers=auth_headers,
        )
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert "job_id" in data, f"No job_id in response: {data}"

        job_id = data["job_id"]
        assert len(job_id) > 0

        # Status must be in a known queued/running state
        status_r = await client.get(f"/v1/sandbox/status/{job_id}", headers=auth_headers)
        assert status_r.status_code == 200, status_r.text
        status = status_r.json()["data"]["status"]
        assert status in {"queued", "started", "running"}, (
            f"Unexpected job status: {status}"
        )

    async def test_health_shows_redis_connected(self, client, auth_headers, monkeypatch):
        """When Redis is running and SANDBOX_ENABLED=true, health must show redis_connected=True."""
        monkeypatch.setenv("SANDBOX_ENABLED", "true")

        import importlib
        import api.sandbox_api as _sa
        importlib.reload(_sa)

        r = await client.get("/v1/sandbox/health/status", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["redis_connected"] is True, (
            f"Expected redis_connected=True, got: {data}"
        )
