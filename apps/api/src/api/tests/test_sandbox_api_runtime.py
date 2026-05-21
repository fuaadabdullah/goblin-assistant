"""Focused runtime tests for api.sandbox_api."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from api import sandbox_api


class _FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, dict[str, str]] = {}
        self.deleted: list[str] = []
        self.should_fail_ping = False

    def hset(self, key: str, *args, mapping=None):
        if mapping is not None:
            self.store.setdefault(key, {})
            for k, v in mapping.items():
                self.store[key][str(k)] = str(v)
            return
        field, value = args
        self.store.setdefault(key, {})
        self.store[key][str(field)] = str(value)

    def hgetall(self, key: str):
        payload = self.store.get(key, {})
        return {
            k.encode("utf-8"): v.encode("utf-8")
            for k, v in payload.items()
        }

    def delete(self, key: str):
        self.deleted.append(key)
        self.store.pop(key, None)

    def scan_iter(self, _pattern: str):
        for key in self.store.keys():
            if key.startswith("sandbox:job:"):
                yield key.encode("utf-8")

    def ping(self):
        if self.should_fail_ping:
            raise ConnectionError("redis down")
        return True


class _FakeQueue:
    def __init__(self) -> None:
        self.enqueued: list[dict] = []
        self.depth = 0

    def enqueue(self, *args, **kwargs):
        self.enqueued.append({"args": args, "kwargs": kwargs})

    def __len__(self) -> int:
        return self.depth


@pytest.mark.asyncio
async def test_submit_job_rejects_when_sandbox_disabled() -> None:
    req = sandbox_api.SubmitJobRequest(language="python", source="print(1)")

    with patch.object(sandbox_api, "SANDBOX_ENABLED", False):
        with pytest.raises(HTTPException) as exc:
            await sandbox_api.submit_job(req, x_api_key="devkey")

    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_submit_job_validates_language_and_timeout() -> None:
    with patch.object(sandbox_api, "SANDBOX_ENABLED", True), patch.object(
        sandbox_api,
        "API_KEY",
        "secret",
    ):
        with pytest.raises(HTTPException) as bad_lang:
            await sandbox_api.submit_job(
                sandbox_api.SubmitJobRequest(
                    language="go",
                    source="fmt.Println(1)",
                ),
                x_api_key="secret",
            )

        with pytest.raises(HTTPException) as bad_timeout:
            await sandbox_api.submit_job(
                sandbox_api.SubmitJobRequest(
                    language="python",
                    source="print(1)",
                    timeout=500,
                ),
                x_api_key="secret",
            )

    assert bad_lang.value.status_code == 400
    assert bad_timeout.value.status_code == 400


@pytest.mark.asyncio
async def test_submit_job_stores_metadata_and_enqueues(tmp_path: Path) -> None:
    fake_redis = _FakeRedis()
    fake_queue = _FakeQueue()
    req = sandbox_api.SubmitJobRequest(
        language="python",
        source="print('ok')",
        timeout=9,
    )

    with patch.object(sandbox_api, "SANDBOX_ENABLED", True), patch.object(
        sandbox_api,
        "API_KEY",
        "secret",
    ), patch.object(
        sandbox_api,
        "JOBS_DIR",
        str(tmp_path),
    ), patch.object(
        sandbox_api,
        "r",
        fake_redis,
    ), patch.object(
        sandbox_api,
        "queue",
        fake_queue,
    ), patch(
        "api.sandbox_api.record_job_submitted",
        MagicMock(),
    ), patch(
        "api.sandbox_api.uuid.uuid4",
        return_value="job-123",
    ):
        result = await sandbox_api.submit_job(req, x_api_key="secret")

    assert result == {"job_id": "job-123"}
    assert "sandbox:job:job-123" in fake_redis.store
    assert fake_queue.enqueued
    source_file = tmp_path / "job-123" / "main.py"
    assert source_file.exists()


@pytest.mark.asyncio
async def test_get_job_status_returns_404_for_missing_job() -> None:
    fake_redis = _FakeRedis()

    with patch.object(sandbox_api, "r", fake_redis), patch.object(
        sandbox_api,
        "API_KEY",
        "secret",
    ):
        with pytest.raises(HTTPException) as exc:
            await sandbox_api.get_job_status("missing", x_api_key="secret")

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_job_status_decodes_redis_payload() -> None:
    fake_redis = _FakeRedis()
    fake_redis.store["sandbox:job:abc"] = {
        "job_id": "abc",
        "status": "finished",
        "created_at": "2025-01-01T00:00:00",
        "exit_code": "0",
    }

    with patch.object(sandbox_api, "r", fake_redis), patch.object(
        sandbox_api,
        "API_KEY",
        "secret",
    ):
        status = await sandbox_api.get_job_status("abc", x_api_key="secret")

    assert status.job_id == "abc"
    assert status.status == "finished"
    assert status.exit_code == 0


@pytest.mark.asyncio
async def test_cancel_job_marks_job_cancelled() -> None:
    fake_redis = _FakeRedis()
    fake_redis.store["sandbox:job:abc"] = {
        "status": "running",
        "created_at": "2025-01-01T00:00:00",
    }

    with patch.object(sandbox_api, "r", fake_redis), patch.object(
        sandbox_api,
        "API_KEY",
        "secret",
    ), patch("api.sandbox_api.record_job_cancelled", MagicMock()):
        resp = await sandbox_api.cancel_job("abc", x_api_key="secret")

    assert resp["message"] == "job cancelled successfully"
    assert fake_redis.store["sandbox:job:abc"]["status"] == "cancelled"


@pytest.mark.asyncio
async def test_sandbox_health_disabled_and_degraded_paths() -> None:
    fake_redis = _FakeRedis()
    fake_queue = _FakeQueue()

    with patch.object(sandbox_api, "SANDBOX_ENABLED", False):
        disabled = await sandbox_api.sandbox_health()
    assert disabled["status"] == "disabled"

    fake_redis.should_fail_ping = True
    with patch.object(sandbox_api, "SANDBOX_ENABLED", True), patch.object(
        sandbox_api,
        "r",
        fake_redis,
    ), patch.object(sandbox_api, "queue", fake_queue):
        degraded = await sandbox_api.sandbox_health()

    assert degraded["status"] == "degraded"
    assert degraded["redis_connected"] is False
    assert "redis_error" in degraded


@pytest.mark.asyncio
async def test_list_jobs_filters_by_status_and_limit() -> None:
    fake_redis = _FakeRedis()
    fake_redis.store["sandbox:job:1"] = {
        "job_id": "1",
        "status": "finished",
        "language": "python",
        "created_at": "2025-01-01T00:00:00",
    }
    fake_redis.store["sandbox:job:2"] = {
        "job_id": "2",
        "status": "queued",
        "language": "javascript",
        "created_at": "2025-01-02T00:00:00",
    }

    with patch.object(sandbox_api, "SANDBOX_ENABLED", True), patch.object(
        sandbox_api,
        "r",
        fake_redis,
    ):
        resp = await sandbox_api.list_sandbox_jobs(
            status="queued",
            limit=1,
        )

    assert resp["total"] == 1
    assert resp["jobs"][0]["job_id"] == "2"
