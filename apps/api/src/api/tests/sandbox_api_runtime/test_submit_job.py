"""Submit Job sandbox API runtime tests."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from .conftest import _FakeQueue, _FakeRedis, sandbox_api


async def test_submit_job_rejects_when_sandbox_disabled() -> None:
    req = sandbox_api.SubmitJobRequest(language="python", source="print(1)")

    with patch.object(sandbox_api, "SANDBOX_ENABLED", False):
        with pytest.raises(HTTPException) as exc:
            await sandbox_api.submit_job(req, x_api_key="any-key")

    assert exc.value.status_code == 503


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


def test_submit_job_request_accepts_code_alias() -> None:
    req = sandbox_api.SubmitJobRequest(language="python", code="print(1)")
    assert req.source == "print(1)"


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
    assert exc.value.detail == "Sandbox execution failed: rq down"
    assert "sandbox:job:job-456" in fake_redis.deleted
    assert not (tmp_path / "job-456").exists()
