"""
S3/MinIO artifact storage service for sandbox jobs
Provides secure upload, download, and lifecycle management for job artifacts
"""

import os
import boto3
import json
import hashlib
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import redis
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
        self.redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))

        # Configuration
        self.max_artifact_size_mb = int(os.getenv("MAX_ARTIFACT_SIZE_MB", "10"))
        self.ttl_days = int(os.getenv("ARTIFACT_TTL_DAYS", "7"))

        # Initialize S3 client
        self._init_s3_client()

    def _init_s3_client(self):
        """Initialize S3 client with proper configuration (lazy — no network calls on startup)."""
        try:
            if not all([self.access_key, self.secret_key]):
                logger.warning("S3 credentials not configured", feature="artifact storage", status="disabled")
                return

            self.s3_client = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,  # None = use real AWS; set S3_ENDPOINT_URL for MinIO/custom
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region,
            )
            logger.info("S3 client initialized", endpoint=self.endpoint_url or "AWS", bucket=self.bucket_name)

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

    def upload_artifact(self, job_id: str, file_path: str, filename: str) -> Optional[Dict[str, Any]]:
        """
        Upload artifact to S3 and store metadata
        Returns artifact metadata on success, None on failure
        """
        if not self.is_available():
            print(f"⚠️  S3 not available, skipping upload of {filename}")
            return None

        try:
            # Validate file exists and size
            if not os.path.exists(file_path):
                print(f"❌ Artifact file not found: {file_path}")
                return None

            if not self.validate_artifact_size(file_path):
                print(f"❌ Artifact too large: {filename} ({os.path.getsize(file_path)/(1024*1024):.1f}MB > {self.max_artifact_size_mb}MB)")
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

            self.s3_client.upload_file(
                file_path,
                self.bucket_name,
                s3_key,
                ExtraArgs=extra_args
            )

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
            self.redis_client.hset(meta_key, mapping=artifact_meta)
            self.redis_client.expire(meta_key, self.ttl_days * 24 * 60 * 60)

            print(f"✅ Uploaded artifact: {s3_key} ({file_size} bytes, TTL: {self.ttl_days}d)")

            return artifact_meta

        except Exception as e:
            print(f"❌ Failed to upload artifact {filename}: {e}")
            return None

    def get_artifact_metadata(self, job_id: str, filename: str) -> Optional[Dict[str, Any]]:
        """Get artifact metadata from Redis"""
        try:
            meta_key = f"artifact:{job_id}:{filename}"
            data = self.redis_client.hgetall(meta_key)

            if not data:
                return None

            # Convert bytes to strings
            return {k.decode('utf-8'): v.decode('utf-8') for k, v in data.items()}

        except Exception as e:
            print(f"❌ Failed to get artifact metadata: {e}")
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
                ExpiresIn=expiration_seconds
            )
            return url

        except Exception as e:
            print(f"❌ Failed to generate presigned URL for {s3_key}: {e}")
            return None

    def list_job_artifacts(self, job_id: str) -> List[Dict[str, Any]]:
        """List all artifacts for a job"""
        try:
            # Get all artifact keys for this job
            pattern = f"artifact:{job_id}:*"
            keys = self.redis_client.keys(pattern)

            artifacts = []
            for key in keys:
                data = self.redis_client.hgetall(key)
                if data:
                    artifact = {k.decode('utf-8'): v.decode('utf-8') for k, v in data.items()}

                    # Generate presigned URL
                    s3_key = artifact.get("s3_key")
                    if s3_key:
                        url = self.generate_presigned_url(s3_key)
                        if url:
                            artifact["url"] = url

                    artifacts.append(artifact)

            return artifacts

        except Exception as e:
            print(f"❌ Failed to list artifacts for job {job_id}: {e}")
            return []

    def delete_expired_artifacts(self) -> int:
        """Delete artifacts that have exceeded TTL (for cleanup)"""
        if not self.is_available():
            return 0

        try:
            deleted_count = 0
            current_time = datetime.utcnow()

            # Find expired artifacts in Redis
            pattern = "artifact:*:*:*"
            keys = self.redis_client.keys(pattern)

            for key in keys:
                try:
                    data = self.redis_client.hgetall(key)
                    if data:
                        expires_at_str = data.get(b"expires_at")
                        if expires_at_str:
                            expires_at = datetime.fromisoformat(expires_at_str.decode('utf-8'))
                            if current_time > expires_at:
                                # Delete from S3
                                s3_key = data.get(b"s3_key")
                                if s3_key:
                                    self.s3_client.delete_object(
                                        Bucket=self.bucket_name,
                                        Key=s3_key.decode('utf-8')
                                    )

                                # Delete from Redis
                                self.redis_client.delete(key)
                                deleted_count += 1

                except Exception as e:
                    print(f"❌ Error deleting expired artifact {key}: {e}")

            if deleted_count > 0:
                print(f"🧹 Cleaned up {deleted_count} expired artifacts")

            return deleted_count

        except Exception as e:
            print(f"❌ Failed to cleanup expired artifacts: {e}")
            return 0

    def _guess_content_type(self, filename: str) -> str:
        """Guess content type based on file extension"""
        ext = filename.lower().split('.')[-1]

        content_types = {
            'log': 'text/plain',
            'txt': 'text/plain',
            'json': 'application/json',
            'zip': 'application/zip',
            'tar': 'application/x-tar',
            'gz': 'application/gzip',
            'pdf': 'application/pdf',
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
        }

        return content_types.get(ext, 'application/octet-stream')


# Global instance
artifact_service = ArtifactService()