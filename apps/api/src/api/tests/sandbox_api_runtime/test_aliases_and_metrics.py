"""Aliases And Metrics sandbox API runtime tests."""

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from .conftest import _FakeRedis, sandbox_api


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
    assert unauthorized.value.status_code in (401, 403)

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


async def test_sandbox_metrics_delegates_to_metrics_endpoint() -> None:
    with patch("api.sandbox_api.get_metrics_endpoint", return_value={"metrics": "ok"}):
        assert await sandbox_api.sandbox_metrics() == {"metrics": "ok"}
