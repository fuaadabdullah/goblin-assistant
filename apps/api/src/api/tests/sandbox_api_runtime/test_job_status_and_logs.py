"""Job Status And Logs sandbox API runtime tests."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from .conftest import _FakeRedis, sandbox_api


async def test_get_job_status_returns_404_for_missing_job() -> None:
    fake_redis = _FakeRedis()

    with (
        patch.object(sandbox_api, "r", fake_redis),
        patch.object(
            sandbox_api,
            "API_KEY",
            "secret",
        ),
        pytest.raises(HTTPException) as exc,
    ):
        await sandbox_api.get_job_status("missing", x_api_key="secret")

    assert exc.value.status_code == 404


async def test_get_job_status_decodes_redis_payload() -> None:
    fake_redis = _FakeRedis()
    fake_redis.store["sandbox:job:abc"] = {
        "job_id": "abc",
        "status": "finished",
        "created_at": "2025-01-01T00:00:00",
        "exit_code": "0",
    }

    with (
        patch.object(sandbox_api, "r", fake_redis),
        patch.object(
            sandbox_api,
            "API_KEY",
            "secret",
        ),
        patch.object(sandbox_api.event_emitter, "emit", AsyncMock()),
    ):
        status = await sandbox_api.get_job_status("abc", x_api_key="secret")

    assert status.data.job_id == "abc"
    assert status.data.status == "finished"
    assert status.data.exit_code == 0


async def test_get_job_logs_paths(tmp_path: Path) -> None:
    fake_redis = _FakeRedis()
    job_path = tmp_path / "job-logs"
    job_path.mkdir()
    fake_redis.store["sandbox:job:abc"] = {
        "job_id": "abc",
        "status": "finished",
        "created_at": "2025-01-01T00:00:00",
        "path": str(job_path),
    }

    with (
        patch.object(sandbox_api, "r", fake_redis),
        patch.object(sandbox_api, "API_KEY", "secret"),
        patch.object(sandbox_api.event_emitter, "emit", AsyncMock()),
    ):
        empty = await sandbox_api.get_job_logs("abc", x_api_key="secret")

    assert empty.data.logs == ""

    stdout_log = job_path / "stdout.log"
    stdout_log.write_text("done", encoding="utf-8")
    with (
        patch.object(sandbox_api, "r", fake_redis),
        patch.object(sandbox_api, "API_KEY", "secret"),
        patch.object(sandbox_api.event_emitter, "emit", AsyncMock()),
    ):
        loaded = await sandbox_api.get_job_logs("abc", x_api_key="secret")

    assert loaded.data.logs == "done"


async def test_get_job_logs_rejects_incomplete_and_missing_path() -> None:
    fake_redis = _FakeRedis()
    fake_redis.store["sandbox:job:incomplete"] = {"status": "running", "path": "/tmp/missing"}
    fake_redis.store["sandbox:job:missing-path"] = {"status": "finished"}

    with patch.object(sandbox_api, "API_KEY", "secret"), patch.object(sandbox_api, "r", fake_redis):
        with pytest.raises(HTTPException) as incomplete:
            await sandbox_api.get_job_logs("incomplete", x_api_key="secret")
        with pytest.raises(HTTPException) as missing_path:
            await sandbox_api.get_job_logs("missing-path", x_api_key="secret")

    assert incomplete.value.status_code == 400
    assert missing_path.value.status_code == 404


async def test_get_job_logs_read_failure_surfaces_http_500(tmp_path: Path) -> None:
    fake_redis = _FakeRedis()
    job_path = tmp_path / "job-read-fail"
    job_path.mkdir()
    (job_path / "stdout.log").write_text("x", encoding="utf-8")
    fake_redis.store["sandbox:job:abc"] = {"status": "finished", "path": str(job_path)}

    with (
        patch.object(sandbox_api, "API_KEY", "secret"),
        patch.object(sandbox_api, "r", fake_redis),
        patch.object(sandbox_api.event_emitter, "emit", AsyncMock()),
        patch("api.sandbox_api._read_text_file", side_effect=RuntimeError("boom")),
    ):
        with pytest.raises(HTTPException) as exc:
            await sandbox_api.get_job_logs("abc", x_api_key="secret")

    assert exc.value.status_code == 500
    assert exc.value.detail == "Failed to read logs: boom"
