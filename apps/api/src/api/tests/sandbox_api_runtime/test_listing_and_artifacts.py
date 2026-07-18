"""Listing And Artifacts sandbox API runtime tests."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from .conftest import _FakeRedis, sandbox_api


async def test_list_sandbox_jobs_failure_surfaces_http_500() -> None:
    fake_redis = _FakeRedis()

    def broken_scan_iter(*args, **kwargs):
        raise RuntimeError("boom")

    fake_redis.scan_iter = broken_scan_iter  # type: ignore[assignment]

    with (
        patch.object(sandbox_api, "SANDBOX_ENABLED", True),
        patch.object(sandbox_api, "API_KEY", "secret"),
        patch.object(sandbox_api, "r", fake_redis),
    ):
        with pytest.raises(HTTPException) as exc:
            await sandbox_api.list_sandbox_jobs(x_api_key="secret")

    assert exc.value.status_code == 500
    assert exc.value.detail == "Failed to list jobs: boom"


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
