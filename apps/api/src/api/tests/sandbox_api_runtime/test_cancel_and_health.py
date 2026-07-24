"""Cancel And Health sandbox API runtime tests."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from .conftest import _FakeQueue, _FakeRedis, sandbox_api


async def test_cancel_job_marks_job_cancelled() -> None:
    fake_redis = _FakeRedis()
    fake_redis.store["sandbox:job:abc"] = {
        "status": "running",
        "created_at": "2025-01-01T00:00:00",
    }

    with (
        patch.object(sandbox_api, "r", fake_redis),
        patch.object(
            sandbox_api,
            "API_KEY",
            "secret",
        ),
        patch("api.sandbox_api.record_job_cancelled", MagicMock()),
        patch.object(
            sandbox_api.event_emitter,
            "emit",
            AsyncMock(),
        ),
    ):
        resp = await sandbox_api.cancel_job("abc", x_api_key="secret")

    assert resp.data.message == "job cancelled successfully"
    assert fake_redis.store["sandbox:job:abc"]["status"] == "cancelled"


async def test_cancel_job_rejects_missing_and_non_cancellable_jobs() -> None:
    fake_redis = _FakeRedis()
    fake_redis.store["sandbox:job:done"] = {"status": "finished"}

    with patch.object(sandbox_api, "r", fake_redis), patch.object(sandbox_api, "API_KEY", "secret"):
        with pytest.raises(HTTPException) as missing:
            await sandbox_api.cancel_job("missing", x_api_key="secret")
        with pytest.raises(HTTPException) as done:
            await sandbox_api.cancel_job("done", x_api_key="secret")

    assert missing.value.status_code == 404
    assert done.value.status_code == 400


async def test_cancel_job_tolerates_container_kill_failure() -> None:
    fake_redis = _FakeRedis()
    fake_redis.store["sandbox:job:abc"] = {
        "status": "running",
        "container_id": "container-1",
        "created_at": "2025-01-01T00:00:00",
    }
    proc = MagicMock()
    proc.communicate = AsyncMock(side_effect=RuntimeError("kill failed"))

    with (
        patch.object(sandbox_api, "r", fake_redis),
        patch.object(sandbox_api, "API_KEY", "secret"),
        patch("api.sandbox_api.record_job_cancelled", MagicMock()),
        patch.object(sandbox_api.event_emitter, "emit", AsyncMock()),
        patch("api.sandbox_api.asyncio.create_subprocess_exec", AsyncMock(return_value=proc)),
        patch("api.sandbox_api.asyncio.wait_for", AsyncMock(side_effect=RuntimeError("timeout"))),
        patch("shutil.which", return_value="/usr/bin/docker"),
    ):
        resp = await sandbox_api.cancel_job("abc", x_api_key="secret")

    assert resp.data.message == "job cancelled successfully"


async def test_sandbox_health_disabled_and_degraded_paths() -> None:
    fake_redis = _FakeRedis()
    fake_queue = _FakeQueue()

    with patch.object(sandbox_api, "SANDBOX_ENABLED", False):
        disabled = await sandbox_api.sandbox_health()
    assert disabled.data.status == "disabled"

    fake_redis.should_fail_ping = True
    with (
        patch.object(sandbox_api, "SANDBOX_ENABLED", True),
        patch.object(
            sandbox_api,
            "r",
            fake_redis,
        ),
        patch.object(sandbox_api, "queue", fake_queue),
    ):
        degraded = await sandbox_api.sandbox_health()

    assert degraded.data.status == "degraded"
    assert degraded.data.redis_connected is False
    assert degraded.data.redis_error is not None


async def test_sandbox_health_healthy_and_unhealthy_paths() -> None:
    fake_redis = _FakeRedis()
    fake_queue = _FakeQueue()
    fake_queue.depth = 3

    with (
        patch.object(sandbox_api, "SANDBOX_ENABLED", True),
        patch.object(sandbox_api, "r", fake_redis),
        patch.object(sandbox_api, "queue", fake_queue),
        patch.object(sandbox_api, "SANDBOX_IMAGE", "sandbox:latest"),
    ):
        healthy = await sandbox_api.sandbox_health()

    assert healthy.data.status == "healthy"
    assert healthy.data.queue_depth == 3

    with (
        patch.object(sandbox_api, "SANDBOX_ENABLED", True),
        patch.object(sandbox_api, "r", fake_redis),
        patch.object(sandbox_api, "queue", fake_queue),
        patch.object(sandbox_api, "SANDBOX_IMAGE", ""),
    ):
        unhealthy = await sandbox_api.sandbox_health()

    assert unhealthy.data.status == "unhealthy"
