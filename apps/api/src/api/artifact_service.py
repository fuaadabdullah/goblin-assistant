"""
S3/MinIO artifact storage service for sandbox jobs
Provides secure upload, download, and lifecycle management for job artifacts
"""

import os
import boto3
import hashlib
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import redis.asyncio as redis
import structlog

logger = structlog.get_logger()


class ArtifactService:
    """Service for managing job artifacts in S3-compatible storage"""

    def __init__(self):
        # S3/MinIO configuration
        self.s3_client = None
        self.bucket_name = os.getenv("S3_BUCKET", "goblin-sandbox")
        self.endpoint_url = os.getenv("ARTIFACT_S3_ENDPOINT")
        self.access_key = os.getenv("S3_ACCESS_KEY")
        self.secret_key = os.getenv("S3_SECRET_KEY")
        self.region = os.getenv("S3_REGION", "us-east-1")

        # Redis for metadata storage
        self.redis_client = redis.from_url(
            os.getenv("REDIS_URL", "redis://redis:6379/0"),
            decode_responses=True,
        )

        # Configuration
        self.max_artifact_size_mb = int(os.getenv("MAX_ARTIFACT_SIZE_MB", "10"))
        self.ttl_days = int(os.getenv("ARTIFACT_TTL_DAYS", "7"))

        # Initialize S3 client
        self._init_s3_client()

    def _init_s3_client(self):
        """Initialize S3 client with proper configuration (lazy — no network calls on startup)."""
        try:
            if not all([self.access_key, self.secret_key]):
                logger.warning(
                    "S3 credentials not configured",
                    feature="artifact storage",
                    status="disabled",
                )
                return

            self.s3_client = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,  # None = use real AWS; set S3_ENDPOINT_URL for MinIO/custom
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region,
            )
            logger.info(
                "S3 client initialized",
                endpoint=self.endpoint_url or "AWS",
                bucket=self.bucket_name,
            )

        except Exception as e:
            logger.warning("S3/MinIO not available — artifact storage disabled", error=str(e))
            self.s3_client = None

    def is_available(self) -> bool:
        """Check if S3 storage is available"""
        return self.s3_client is not None

    def calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of file for integrity checking"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    def validate_artifact_size(self, file_path: str) -> bool:
        """Validate artifact size against limits"""
        try:
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            return size_mb <= self.max_artifact_size_mb
        except OSError:
            return False

    async def upload_artifact(
        self, job_id: str, file_path: str, filename: str
    ) -> Optional[Dict[str, Any]]:
        """
        Upload artifact to S3 and store metadata
        Returns artifact metadata on success, None on failure
        """
        if not self.is_available():
            logger.warning("artifact_upload_skipped", filename=filename, reason="s3_unavailable")
            return None

        try:
            # Validate file exists and size
            if not os.path.exists(file_path):
                logger.warning("artifact_file_not_found", file_path=file_path, job_id=job_id)
                return None

            if not self.validate_artifact_size(file_path):
                size_mb = os.path.getsize(file_path) / (1024 * 1024)
                logger.warning(
                    "artifact_too_large",
                    filename=filename,
                    size_mb=round(size_mb, 1),
                    limit_mb=self.max_artifact_size_mb,
                    job_id=job_id,
                )
                return None

            # Generate S3 key
            s3_key = f"jobs/{job_id}/{filename}"

            # Calculate file hash and metadata
            file_hash = self.calculate_file_hash(file_path)
            file_size = os.path.getsize(file_path)
            upload_time = datetime.utcnow()

            # Set metadata with TTL
            expires_at = upload_time + timedelta(days=self.ttl_days)

            # Upload to S3 with metadata
            extra_args = {
                "Metadata": {
                    "job_id": job_id,
                    "filename": filename,
                    "sha256": file_hash,
                    "size_bytes": str(file_size),
                    "uploaded_at": upload_time.isoformat(),
                    "expires_at": expires_at.isoformat(),
                },
                "ContentType": self._guess_content_type(filename),
            }

            self.s3_client.upload_file(file_path, self.bucket_name, s3_key, ExtraArgs=extra_args)

            # Store metadata in Redis
            artifact_meta = {
                "job_id": job_id,
                "filename": filename,
                "s3_key": s3_key,
                "sha256": file_hash,
                "size_bytes": file_size,
                "uploaded_at": upload_time.isoformat(),
                "expires_at": expires_at.isoformat(),
            }

            # Store in Redis with TTL
            meta_key = f"artifact:{job_id}:{filename}"
            await self.redis_client.hset(meta_key, mapping=artifact_meta)
            await self.redis_client.expire(meta_key, self.ttl_days * 24 * 60 * 60)

            logger.info(
                "artifact_uploaded",
                s3_key=s3_key,
                size_bytes=file_size,
                ttl_days=self.ttl_days,
            )

            return artifact_meta

        except Exception as e:
            logger.error(
                "artifact_upload_failed",
                filename=filename,
                job_id=job_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    async def get_artifact_metadata(self, job_id: str, filename: str) -> Optional[Dict[str, Any]]:
        """Get artifact metadata from Redis"""
        try:
            meta_key = f"artifact:{job_id}:{filename}"
            data = await self.redis_client.hgetall(meta_key)
            return data or None
        except Exception as e:
            logger.error(
                "artifact_metadata_fetch_failed",
                job_id=job_id,
                filename=filename,
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    def generate_presigned_url(self, s3_key: str, expiration_seconds: int = 300) -> Optional[str]:
        """
        Generate presigned URL for secure artifact access
        Default expiration: 5 minutes
        """
        if not self.is_available():
            return None

        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": s3_key},
                ExpiresIn=expiration_seconds,
            )
            return url

        except Exception as e:
            logger.error(
                "presigned_url_generation_failed",
                s3_key=s3_key,
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    async def list_job_artifacts(self, job_id: str) -> List[Dict[str, Any]]:
        """List all artifacts for a job"""
        try:
            pattern = f"artifact:{job_id}:*"
            artifacts = []
            async for key in self.redis_client.scan_iter(pattern):
                data = await self.redis_client.hgetall(key)
                if data:
                    s3_key = data.get("s3_key")
                    if s3_key:
                        url = self.generate_presigned_url(s3_key)
                        if url:
                            data["url"] = url
                    artifacts.append(data)
            return artifacts
        except Exception as e:
            logger.error(
                "artifact_list_failed",
                job_id=job_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            return []

    async def delete_expired_artifacts(self) -> int:
        """Delete artifacts that have exceeded TTL (for cleanup)"""
        if not self.is_available():
            return 0

        try:
            deleted_count = 0
            current_time = datetime.utcnow()

            async for key in self.redis_client.scan_iter("artifact:*"):
                try:
                    data = await self.redis_client.hgetall(key)
                    if not data:
                        continue
                    expires_at_str = data.get("expires_at")
                    if expires_at_str and current_time > datetime.fromisoformat(expires_at_str):
                        s3_key = data.get("s3_key")
                        if s3_key:
                            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
                        await self.redis_client.delete(key)
                        deleted_count += 1
                except Exception as e:
                    logger.error(
                        "artifact_delete_failed",
                        key=key,
                        error=str(e),
                        error_type=type(e).__name__,
                    )

            if deleted_count > 0:
                logger.info("artifacts_cleaned_up", count=deleted_count)

            return deleted_count

        except Exception as e:
            logger.error(
                "artifact_cleanup_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            return 0

    def _guess_content_type(self, filename: str) -> str:
        """Guess content type based on file extension"""
        ext = filename.lower().split(".")[-1]

        content_types = {
            "log": "text/plain",
            "txt": "text/plain",
            "json": "application/json",
            "zip": "application/zip",
            "tar": "application/x-tar",
            "gz": "application/gzip",
            "pdf": "application/pdf",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
        }

        return content_types.get(ext, "application/octet-stream")


# Global instance
artifact_service = ArtifactService()
