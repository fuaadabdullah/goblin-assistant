"""Focused runtime tests for api.sandbox_api."""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

sys.modules.pop("api.sandbox_api", None)
sandbox_api = importlib.import_module("api.sandbox_api")


def test_sandbox_image_default_when_env_unset() -> None:
    expected_default = "goblin-assistant-sandbox:latest"
    original = os.environ.pop("SANDBOX_IMAGE", None)
    try:
        module = importlib.reload(sandbox_api)
        assert expected_default == module.SANDBOX_IMAGE
    finally:
        if original is None:
            os.environ.pop("SANDBOX_IMAGE", None)
        else:
            os.environ["SANDBOX_IMAGE"] = original
        importlib.reload(sandbox_api)


def test_sandbox_api_key_default_when_env_unset() -> None:
    original = os.environ.pop("API_AUTH_KEY", None)
    try:
        module = importlib.reload(sandbox_api)
        assert module.API_KEY is None
    finally:
        if original is None:
            os.environ.pop("API_AUTH_KEY", None)
        else:
            os.environ["API_AUTH_KEY"] = original
        importlib.reload(sandbox_api)


def test_require_api_key_fails_closed_when_key_missing() -> None:
    with (
        patch.object(sandbox_api, "SANDBOX_ENABLED", False),
        patch.object(sandbox_api, "API_KEY", None),
        pytest.raises(HTTPException) as exc,
    ):
        sandbox_api.require_api_key("any-key")

    assert exc.value.status_code == 500
    assert "API_AUTH_KEY" in str(exc.value.detail)


def test_require_api_key_validates_when_key_configured() -> None:
    with (
        patch.object(sandbox_api, "SANDBOX_ENABLED", False),
        patch.object(sandbox_api, "API_KEY", "secret"),
    ):
        with pytest.raises(HTTPException) as exc:
            sandbox_api.require_api_key("wrong")
        sandbox_api.require_api_key("secret")

    assert exc.value.status_code == 401


def test_require_api_key_skips_auth_in_development_when_enabled() -> None:
    with (
        patch.object(sandbox_api, "SANDBOX_ENABLED", True),
        patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=False),
    ):
        sandbox_api.require_api_key("anything")


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
        return {k.encode("utf-8"): v.encode("utf-8") for k, v in payload.items()}

    def delete(self, key: str):
        self.deleted.append(key)
        self.store.pop(key, None)

    def scan_iter(self, _pattern: str):
        for key in self.store:
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
    app.include_router(sandbox_api.router)
    client = TestClient(app)

    with patch.object(sandbox_api, "SANDBOX_ENABLED", False):
        response = client.get("/sandbox/health/status")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "disabled"


@pytest.mark.asyncio
async def test_submit_job_rejects_when_sandbox_disabled() -> None:
    req = sandbox_api.SubmitJobRequest(language="python", source="print(1)")

    with patch.object(sandbox_api, "SANDBOX_ENABLED", False):
        with pytest.raises(HTTPException) as exc:
            await sandbox_api.submit_job(req, x_api_key="any-key")

    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_submit_job_validates_language_and_timeout() -> None:
    with (
        patch.object(sandbox_api, "SANDBOX_ENABLED", True),
        patch.object(
            sandbox_api,
            "API_KEY",
            "secret",
        ),
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
async def test_submit_job_validates_missing_source_and_applies_rate_limit() -> None:
    rate_limit = AsyncMock()

    with (
        patch.object(sandbox_api, "SANDBOX_ENABLED", True),
        patch.object(sandbox_api, "API_KEY", "secret"),
        patch.object(sandbox_api, "sandbox_rate_limiter", MagicMock(__call__=rate_limit)),
    ):
        with pytest.raises(HTTPException) as exc:
            await sandbox_api.submit_job(
                sandbox_api.SubmitJobRequest(language="python", source="   "),
                x_api_key="secret",
                request=object(),
            )

    assert exc.value.status_code == 400
    rate_limit.assert_awaited_once()


@pytest.mark.asyncio
async def test_submit_job_stores_metadata_and_enqueues(tmp_path: Path) -> None:
    fake_redis = _FakeRedis()
    fake_queue = _FakeQueue()
    req = sandbox_api.SubmitJobRequest(
        language="python",
        source="print('ok')",
        timeout=9,
    )

    with (
        patch.object(sandbox_api, "SANDBOX_ENABLED", True),
        patch.object(
            sandbox_api,
            "API_KEY",
            "secret",
        ),
        patch.object(
            sandbox_api,
            "JOBS_DIR",
            str(tmp_path),
        ),
        patch.object(
            sandbox_api,
            "r",
            fake_redis,
        ),
        patch.object(
            sandbox_api,
            "queue",
            fake_queue,
        ),
        patch(
            "api.sandbox_api.record_job_submitted",
            MagicMock(),
        ),
        patch(
            "api.sandbox_api.uuid.uuid4",
            return_value="job-123",
        ),
    ):
        result = await sandbox_api.submit_job(req, x_api_key="secret")

    assert result.data.job_id == "job-123"
    assert "sandbox:job:job-123" in fake_redis.store
    assert fake_queue.enqueued
    source_file = tmp_path / "job-123" / "main.py"
    assert source_file.exists()


@pytest.mark.asyncio
async def test_submit_job_cleans_up_when_queue_enqueue_fails(tmp_path: Path) -> None:
    fake_redis = _FakeRedis()
    fake_queue = _FakeQueue()
    fake_queue.enqueue = MagicMock(side_effect=RuntimeError("rq down"))

    with (
        patch.object(sandbox_api, "SANDBOX_ENABLED", True),
        patch.object(sandbox_api, "API_KEY", "secret"),
        patch.object(sandbox_api, "JOBS_DIR", str(tmp_path)),
        patch.object(sandbox_api, "r", fake_redis),
        patch.object(sandbox_api, "queue", fake_queue),
        patch("api.sandbox_api.uuid.uuid4", return_value="job-456"),
    ):
        with pytest.raises(HTTPException) as exc:
            await sandbox_api.submit_job(
                sandbox_api.SubmitJobRequest(language="python", source="print(1)"),
                x_api_key="secret",
            )

    assert exc.value.status_code == 500
    assert "Sandbox execution failed [job-456]" in str(exc.value.detail)
    assert "sandbox:job:job-456" in fake_redis.deleted
    assert not (tmp_path / "job-456").exists()


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
async def test_list_job_artifacts_and_download_paths() -> None:
    fake_redis = _FakeRedis()
    fake_redis.store["sandbox:job:abc"] = {"status": "finished"}

    with (
        patch.object(sandbox_api, "API_KEY", "secret"),
        patch.object(sandbox_api, "r", fake_redis),
        patch.object(sandbox_api.event_emitter, "emit", AsyncMock()),
        patch.object(
            sandbox_api.artifact_service,
            "list_job_artifacts",
            AsyncMock(
                return_value=[
                    {
                        "filename": "report.csv",
                        "size_bytes": 12,
                        "url": "https://download.example/report.csv",
                        "uploaded_at": "2025-01-01T00:00:00",
                    }
                ]
            ),
        ),
        patch.object(
            sandbox_api.artifact_service,
            "get_artifact_metadata",
            AsyncMock(return_value={"s3_key": "artifacts/report.csv"}),
        ),
        patch.object(
            sandbox_api.artifact_service,
            "generate_presigned_url",
            return_value="https://signed.example/report.csv",
        ),
    ):
        artifacts = await sandbox_api.list_job_artifacts("abc", x_api_key="secret")
        redirect = await sandbox_api.download_artifact("abc", "report.csv", x_api_key="secret")

    assert artifacts.data.artifacts[0].name == "report.csv"
    assert redirect.status_code == 302
    assert redirect.headers["location"] == "https://signed.example/report.csv"


@pytest.mark.asyncio
async def test_download_artifact_rejects_invalid_and_missing_cases() -> None:
    with patch.object(sandbox_api, "API_KEY", "secret"):
        with pytest.raises(HTTPException) as invalid_name:
            await sandbox_api.download_artifact("job", "../secret", x_api_key="secret")
    assert invalid_name.value.status_code == 400

    with (
        patch.object(sandbox_api, "API_KEY", "secret"),
        patch.object(
            sandbox_api.artifact_service,
            "get_artifact_metadata",
            AsyncMock(return_value=None),
        ),
    ):
        with pytest.raises(HTTPException) as missing_artifact:
            await sandbox_api.download_artifact("job", "report.csv", x_api_key="secret")
    assert missing_artifact.value.status_code == 404

    with (
        patch.object(sandbox_api, "API_KEY", "secret"),
        patch.object(
            sandbox_api.artifact_service,
            "get_artifact_metadata",
            AsyncMock(return_value={"filename": "report.csv"}),
        ),
    ):
        with pytest.raises(HTTPException) as missing_key:
            await sandbox_api.download_artifact("job", "report.csv", x_api_key="secret")
    assert missing_key.value.status_code == 404

    with (
        patch.object(sandbox_api, "API_KEY", "secret"),
        patch.object(
            sandbox_api.artifact_service,
            "get_artifact_metadata",
            AsyncMock(return_value={"s3_key": "artifacts/report.csv"}),
        ),
        patch.object(sandbox_api.artifact_service, "generate_presigned_url", return_value=""),
    ):
        with pytest.raises(HTTPException) as unsigned:
            await sandbox_api.download_artifact("job", "report.csv", x_api_key="secret")
    assert unsigned.value.status_code == 500


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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

    with (
        patch.object(sandbox_api, "SANDBOX_ENABLED", True),
        patch.object(
            sandbox_api,
            "r",
            fake_redis,
        ),
        patch.object(sandbox_api.event_emitter, "emit", AsyncMock()),
    ):
        resp = await sandbox_api.list_sandbox_jobs(
            status="queued",
            limit=1,
        )

    assert resp.data.total == 1
    assert resp.data.jobs[0].job_id == "2"


@pytest.mark.asyncio
async def test_run_and_logs_aliases_and_list_jobs_error_paths(tmp_path: Path) -> None:
    fake_redis = _FakeRedis()
    job_path = tmp_path / "job-1"
    job_path.mkdir()
    (job_path / "stdout.log").write_text("alias logs", encoding="utf-8")
    fake_redis.store["sandbox:job:1"] = {
        "job_id": "1",
        "status": "finished",
        "language": "python",
        "created_at": "2025-01-01T00:00:00",
        "path": str(job_path),
    }

    with (
        patch.object(sandbox_api, "SANDBOX_ENABLED", True),
        patch.object(sandbox_api, "API_KEY", "secret"),
        patch.object(sandbox_api, "r", fake_redis),
        patch.object(sandbox_api.event_emitter, "emit", AsyncMock()),
        patch(
            "api.sandbox_api.submit_job",
            AsyncMock(return_value=MagicMock(data=MagicMock(job_id="alias"))),
        ),
    ):
        alias = await sandbox_api.run_sandbox_code(
            sandbox_api.SubmitJobRequest(language="python", source="print(1)"),
            x_api_key="secret",
        )
        logs = await sandbox_api.get_job_logs_alias("1", x_api_key="secret")

    assert alias.data.job_id == "alias"
    assert logs.data.logs == "alias logs"

    with patch.object(sandbox_api, "SANDBOX_ENABLED", False):
        with pytest.raises(HTTPException) as disabled:
            await sandbox_api.list_sandbox_jobs()
    assert disabled.value.status_code == 503

    with (
        patch.object(sandbox_api, "SANDBOX_ENABLED", True),
        patch.object(sandbox_api, "API_KEY", "secret"),
        patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=False),
    ):
        with pytest.raises(HTTPException) as unauthorized:
            await sandbox_api.list_sandbox_jobs(x_api_key="wrong")
    assert unauthorized.value.status_code == 401

    with (
        patch.object(sandbox_api, "SANDBOX_ENABLED", True),
        patch.object(
            sandbox_api,
            "r",
            MagicMock(scan_iter=MagicMock(side_effect=RuntimeError("scan failed"))),
        ),
    ):
        with pytest.raises(HTTPException) as list_error:
            await sandbox_api.list_sandbox_jobs()
    assert list_error.value.status_code == 500

    with patch.object(sandbox_api, "SANDBOX_ENABLED", False):
        with pytest.raises(HTTPException) as alias_disabled:
            await sandbox_api.get_job_logs_alias("1")
    assert alias_disabled.value.status_code == 503


@pytest.mark.asyncio
async def test_sandbox_metrics_delegates_to_metrics_endpoint() -> None:
    with patch("api.sandbox_api.get_metrics_endpoint", return_value={"metrics": "ok"}):
        assert await sandbox_api.sandbox_metrics() == {"metrics": "ok"}
