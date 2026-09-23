"""Tests for api.artifact_service — S3/MinIO artifact storage for sandbox jobs.

ArtifactService talks to two external systems (S3-compatible storage and
Redis for metadata), both faked here. is_available() gates most public
methods, so each of those has an "S3 unavailable" test alongside its happy
path, matching how the service behaves without credentials configured.
"""

from __future__ import annotations

import importlib
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api import artifact_service as artifact_service_module
from api.artifact_service import ArtifactService


def test_artifact_service_ignores_invalid_redis_url(monkeypatch) -> None:
    monkeypatch.setenv("REDIS_URL", "not-a-redis-url")

    module = importlib.reload(artifact_service_module)

    assert module._resolve_redis_url("not-a-redis-url") == "redis://localhost:6379/0"
    assert module.artifact_service.redis_client is not None


def _service(*, s3_configured: bool = True) -> ArtifactService:
    with patch("api.artifact_service.redis.from_url", return_value=MagicMock()):
        if s3_configured:
            with (
                patch.dict(
                    "os.environ",
                    {"S3_ACCESS_KEY": "ak", "S3_SECRET_KEY": "sk", "S3_BUCKET": "test-bucket"},
                ),
                patch("api.artifact_service.boto3.client") as client_factory,
            ):
                service = ArtifactService()
                service.s3_client = client_factory.return_value
        else:
            with patch.dict("os.environ", {"S3_ACCESS_KEY": "", "S3_SECRET_KEY": ""}, clear=False):
                service = ArtifactService()
    service.redis_client = AsyncMock()
    return service


# ---------------------------------------------------------------------------
# S3 client initialization
# ---------------------------------------------------------------------------


class TestInitS3Client:
    def test_missing_credentials_leave_s3_disabled(self):
        service = _service(s3_configured=False)

        assert service.is_available() is False

    def test_configured_credentials_create_a_client(self):
        service = _service(s3_configured=True)

        assert service.is_available() is True

    def test_a_construction_error_disables_storage_rather_than_raising(self):
        with (
            patch("api.artifact_service.redis.from_url", return_value=MagicMock()),
            patch.dict("os.environ", {"S3_ACCESS_KEY": "ak", "S3_SECRET_KEY": "sk"}, clear=False),
            patch("api.artifact_service.boto3.client", side_effect=RuntimeError("bad config")),
        ):
            service = ArtifactService()

        assert service.is_available() is False


# ---------------------------------------------------------------------------
# calculate_file_hash / validate_artifact_size
# ---------------------------------------------------------------------------


class TestFileHelpers:
    def test_hashes_file_contents(self, tmp_path):
        service = _service()
        path = tmp_path / "artifact.txt"
        path.write_bytes(b"hello world")

        import hashlib

        expected = hashlib.sha256(b"hello world").hexdigest()

        assert service.calculate_file_hash(str(path)) == expected

    def test_validates_a_small_file(self, tmp_path):
        service = _service()
        service.max_artifact_size_mb = 10
        path = tmp_path / "small.txt"
        path.write_bytes(b"x" * 1024)

        assert service.validate_artifact_size(str(path)) is True

    def test_rejects_a_file_over_the_limit(self, tmp_path):
        service = _service()
        service.max_artifact_size_mb = 0  # anything nonzero fails the limit
        path = tmp_path / "big.txt"
        path.write_bytes(b"x" * 2048)

        assert service.validate_artifact_size(str(path)) is False

    def test_a_missing_file_fails_validation_rather_than_raising(self):
        service = _service()

        assert service.validate_artifact_size("/no/such/file") is False


# ---------------------------------------------------------------------------
# upload_artifact
# ---------------------------------------------------------------------------


class TestUploadArtifact:
    @pytest.mark.asyncio
    async def test_skipped_when_s3_is_unavailable(self):
        service = _service(s3_configured=False)

        assert await service.upload_artifact("job-1", "/tmp/f.txt", "f.txt") is None

    @pytest.mark.asyncio
    async def test_returns_none_when_the_file_does_not_exist(self):
        service = _service()

        assert await service.upload_artifact("job-1", "/no/such/file", "f.txt") is None

    @pytest.mark.asyncio
    async def test_returns_none_when_the_file_is_too_large(self, tmp_path):
        service = _service()
        service.max_artifact_size_mb = 0
        path = tmp_path / "big.txt"
        path.write_bytes(b"x" * 1024)

        assert await service.upload_artifact("job-1", str(path), "big.txt") is None

    @pytest.mark.asyncio
    async def test_uploads_and_records_metadata(self, tmp_path):
        service = _service()
        path = tmp_path / "log.txt"
        path.write_bytes(b"job output")

        result = await service.upload_artifact("job-1", str(path), "log.txt")

        assert result is not None
        assert result["job_id"] == "job-1"
        assert result["filename"] == "log.txt"
        assert result["s3_key"] == "jobs/job-1/log.txt"
        assert result["size_bytes"] == len(b"job output")
        service.s3_client.upload_file.assert_called_once()
        service.redis_client.hset.assert_awaited_once()
        service.redis_client.expire.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_content_type_is_derived_from_the_extension(self, tmp_path):
        service = _service()
        path = tmp_path / "data.json"
        path.write_bytes(b"{}")

        await service.upload_artifact("job-1", str(path), "data.json")

        extra_args = service.s3_client.upload_file.call_args.kwargs["ExtraArgs"]
        assert extra_args["ContentType"] == "application/json"

    @pytest.mark.asyncio
    async def test_an_upload_failure_is_swallowed(self, tmp_path):
        service = _service()
        service.s3_client.upload_file.side_effect = RuntimeError("network down")
        path = tmp_path / "f.txt"
        path.write_bytes(b"data")

        assert await service.upload_artifact("job-1", str(path), "f.txt") is None

    @pytest.mark.asyncio
    async def test_the_expiry_matches_the_configured_ttl(self, tmp_path):
        service = _service()
        service.ttl_days = 3
        path = tmp_path / "f.txt"
        path.write_bytes(b"data")

        before = datetime.utcnow()
        result = await service.upload_artifact("job-1", str(path), "f.txt")
        expires_at = datetime.fromisoformat(result["expires_at"])

        assert expires_at - before >= timedelta(days=3) - timedelta(seconds=5)


# ---------------------------------------------------------------------------
# get_artifact_metadata
# ---------------------------------------------------------------------------


class TestGetArtifactMetadata:
    @pytest.mark.asyncio
    async def test_returns_the_stored_metadata(self):
        service = _service()
        service.redis_client.hgetall.return_value = {"filename": "f.txt"}

        result = await service.get_artifact_metadata("job-1", "f.txt")

        assert result == {"filename": "f.txt"}

    @pytest.mark.asyncio
    async def test_returns_none_for_an_empty_result(self):
        service = _service()
        service.redis_client.hgetall.return_value = {}

        assert await service.get_artifact_metadata("job-1", "f.txt") is None

    @pytest.mark.asyncio
    async def test_a_redis_failure_returns_none_rather_than_raising(self):
        service = _service()
        service.redis_client.hgetall.side_effect = RuntimeError("conn refused")

        assert await service.get_artifact_metadata("job-1", "f.txt") is None


# ---------------------------------------------------------------------------
# generate_presigned_url
# ---------------------------------------------------------------------------


class TestGeneratePresignedUrl:
    def test_returns_none_when_s3_is_unavailable(self):
        service = _service(s3_configured=False)

        assert service.generate_presigned_url("jobs/1/f.txt") is None

    def test_returns_the_generated_url(self):
        service = _service()
        service.s3_client.generate_presigned_url.return_value = "https://signed.example/f.txt"

        url = service.generate_presigned_url("jobs/1/f.txt", expiration_seconds=60)

        assert url == "https://signed.example/f.txt"
        kwargs = service.s3_client.generate_presigned_url.call_args.kwargs
        assert kwargs["ExpiresIn"] == 60
        assert kwargs["Params"]["Key"] == "jobs/1/f.txt"

    def test_a_generation_error_returns_none(self):
        service = _service()
        service.s3_client.generate_presigned_url.side_effect = RuntimeError("denied")

        assert service.generate_presigned_url("jobs/1/f.txt") is None


# ---------------------------------------------------------------------------
# list_job_artifacts
# ---------------------------------------------------------------------------


class _AsyncIter:
    def __init__(self, items):
        self._items = list(items)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._items:
            raise StopAsyncIteration
        return self._items.pop(0)


class TestListJobArtifacts:
    @pytest.mark.asyncio
    async def test_lists_artifacts_with_a_presigned_url_each(self):
        service = _service()
        service.redis_client.scan_iter = MagicMock(
            return_value=_AsyncIter(["artifact:job-1:a.txt"])
        )
        service.redis_client.hgetall.return_value = {"s3_key": "jobs/1/a.txt"}
        service.s3_client.generate_presigned_url.return_value = "https://signed.example/a.txt"

        artifacts = await service.list_job_artifacts("job-1")

        assert artifacts == [{"s3_key": "jobs/1/a.txt", "url": "https://signed.example/a.txt"}]

    @pytest.mark.asyncio
    async def test_no_artifacts_yields_an_empty_list(self):
        service = _service()
        service.redis_client.scan_iter = MagicMock(return_value=_AsyncIter([]))

        assert await service.list_job_artifacts("job-1") == []

    @pytest.mark.asyncio
    async def test_entries_without_data_are_skipped(self):
        service = _service()
        service.redis_client.scan_iter = MagicMock(
            return_value=_AsyncIter(["artifact:job-1:a.txt"])
        )
        service.redis_client.hgetall.return_value = {}

        assert await service.list_job_artifacts("job-1") == []

    @pytest.mark.asyncio
    async def test_a_scan_failure_returns_an_empty_list(self):
        service = _service()
        service.redis_client.scan_iter = MagicMock(side_effect=RuntimeError("conn refused"))

        assert await service.list_job_artifacts("job-1") == []


# ---------------------------------------------------------------------------
# delete_expired_artifacts
# ---------------------------------------------------------------------------


class TestDeleteExpiredArtifacts:
    @pytest.mark.asyncio
    async def test_returns_zero_when_s3_is_unavailable(self):
        service = _service(s3_configured=False)

        assert await service.delete_expired_artifacts() == 0

    @pytest.mark.asyncio
    async def test_deletes_only_expired_entries(self):
        service = _service()
        past = (datetime.utcnow() - timedelta(days=1)).isoformat()
        future = (datetime.utcnow() + timedelta(days=1)).isoformat()
        service.redis_client.scan_iter = MagicMock(
            return_value=_AsyncIter(["artifact:1:a", "artifact:1:b"])
        )
        service.redis_client.hgetall.side_effect = [
            {"expires_at": past, "s3_key": "jobs/1/a"},
            {"expires_at": future, "s3_key": "jobs/1/b"},
        ]

        deleted = await service.delete_expired_artifacts()

        assert deleted == 1
        service.s3_client.delete_object.assert_called_once_with(
            Bucket=service.bucket_name, Key="jobs/1/a"
        )
        service.redis_client.delete.assert_awaited_once_with("artifact:1:a")

    @pytest.mark.asyncio
    async def test_entries_without_data_are_skipped(self):
        service = _service()
        service.redis_client.scan_iter = MagicMock(return_value=_AsyncIter(["artifact:1:a"]))
        service.redis_client.hgetall.return_value = {}

        assert await service.delete_expired_artifacts() == 0

    @pytest.mark.asyncio
    async def test_one_bad_entry_does_not_stop_the_sweep(self):
        service = _service()
        past = (datetime.utcnow() - timedelta(days=1)).isoformat()
        service.redis_client.scan_iter = MagicMock(
            return_value=_AsyncIter(["artifact:1:a", "artifact:1:b"])
        )
        service.redis_client.hgetall.side_effect = [
            RuntimeError("corrupt entry"),
            {"expires_at": past, "s3_key": "jobs/1/b"},
        ]

        deleted = await service.delete_expired_artifacts()

        assert deleted == 1

    @pytest.mark.asyncio
    async def test_a_top_level_failure_returns_zero(self):
        service = _service()
        service.redis_client.scan_iter = MagicMock(side_effect=RuntimeError("conn refused"))

        assert await service.delete_expired_artifacts() == 0


# ---------------------------------------------------------------------------
# _guess_content_type
# ---------------------------------------------------------------------------


class TestGuessContentType:
    @pytest.mark.parametrize(
        "filename,expected",
        [
            ("out.log", "text/plain"),
            ("notes.txt", "text/plain"),
            ("data.json", "application/json"),
            ("bundle.zip", "application/zip"),
            ("archive.tar", "application/x-tar"),
            ("archive.tar.gz", "application/gzip"),
            ("report.pdf", "application/pdf"),
            ("shot.png", "image/png"),
            ("shot.jpg", "image/jpeg"),
            ("shot.jpeg", "image/jpeg"),
        ],
    )
    def test_maps_known_extensions(self, filename, expected):
        service = _service()

        assert service._guess_content_type(filename) == expected

    def test_unknown_extensions_default_to_octet_stream(self):
        service = _service()

        assert service._guess_content_type("binary.bin") == "application/octet-stream"

    def test_extension_matching_is_case_insensitive(self):
        service = _service()

        assert service._guess_content_type("REPORT.PDF") == "application/pdf"
