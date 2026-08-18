"""
Sandbox API router for secure code execution
Provides endpoints for submitting, monitoring, and managing sandbox jobs
"""

import asyncio
import os
import shutil
import uuid
import json
from typing import Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, model_validator
import redis
import rq

from .core.contracts import SuccessEnvelope
from .config.redis_url import DEFAULT_REDIS_URL, resolve_redis_url

# Import from existing infrastructure
from .middleware.rate_limiter import RateLimiter
from .artifact_service import artifact_service
from .sandbox_metrics import (
    record_job_submitted, record_job_cancelled,
    get_metrics_endpoint
)
from .input_validation import InputSanitizer
from .observability.events import event_emitter

# Configuration from environment
REDIS_URL = os.getenv("REDIS_URL", DEFAULT_REDIS_URL)
SANDBOX_IMAGE = os.getenv("SANDBOX_IMAGE", "goblin-assistant-sandbox:latest")
API_KEY = os.getenv("API_AUTH_KEY")
JOBS_DIR = os.getenv("JOBS_DIR", "/tmp/goblin_sandbox")
SANDBOX_ENABLED = os.getenv("SANDBOX_ENABLED", "false").lower() == "true"
MAX_OUTPUT_SIZE = int(os.getenv("SANDBOX_MAX_OUTPUT_SIZE", str(1024 * 1024)))
MAX_CONCURRENT_PER_USER = int(os.getenv("SANDBOX_MAX_PER_USER", "5"))

# Initialize Redis and RQ
r = redis.from_url(resolve_redis_url(REDIS_URL, component="sandbox_api"))
queue = rq.Queue("sandbox-jobs", connection=r)

# Rate limiter for sandbox operations
sandbox_rate_limiter = RateLimiter(
    redis_url=resolve_redis_url(REDIS_URL, component="sandbox_api"),
    requests_per_minute=int(os.getenv("SANDBOX_RATE_LIMIT_PER_MINUTE", "10")),
    requests_per_hour=int(os.getenv("SANDBOX_RATE_LIMIT_PER_HOUR", "100")),
)

# Ensure jobs directory exists (fall back to /tmp if the configured path is unwritable)
try:
    os.makedirs(JOBS_DIR, exist_ok=True)
except PermissionError:
    JOBS_DIR = "/tmp/goblin_sandbox"
    os.makedirs(JOBS_DIR, exist_ok=True)

# Authentication dependency
def require_api_key(x_api_key: str = Header(...)):
    if SANDBOX_ENABLED and os.getenv("ENVIRONMENT", "development") == "development":
        return
    if not API_KEY:
        raise HTTPException(status_code=500, detail="API_AUTH_KEY is not configured")
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="unauthorized")

# Pydantic models for API
class SubmitJobRequest(BaseModel):
    language: str
    source: str = ""
    code: Optional[str] = None
    timeout: Optional[int] = 10
    runtime_args: Optional[str] = ""

    @model_validator(mode="before")
    @classmethod
    def _alias_code_to_source(cls, values):
        if isinstance(values, dict) and not values.get("source") and values.get("code"):
            values["source"] = values["code"]
        return values

class JobStatus(BaseModel):
    job_id: str
    status: str  # queued, running, finished, failed, cancelled
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    exit_code: Optional[int] = None
    error: Optional[str] = None

class SubmitJobResponse(BaseModel):
    job_id: str

class ArtifactInfo(BaseModel):
    name: str
    size: int
    url: str
    created_at: str

class JobLogsResponse(BaseModel):
    logs: str
    truncated: bool = False
    original_size: Optional[int] = None
    truncated_size: Optional[int] = None

class CancelJobResponse(BaseModel):
    message: str

class SandboxHealthResponse(BaseModel):
    status: str
    redis_connected: bool = True
    redis_error: Optional[str] = None
    image_configured: bool = True
    queue_depth: int = 0
    enabled: bool = True
    max_concurrent_per_user: int = 0
    max_output_size: int = 0
    message: Optional[str] = None

class JobListResponse(BaseModel):
    jobs: list
    total: int

class ArtifactListResponse(BaseModel):
    artifacts: list


def _read_text_file(path: str, max_bytes: Optional[int] = None) -> str:
    with open(path, "r") as f:
        if max_bytes is not None:
            return f.read(max_bytes)
        return f.read()


def _decode_job_data(raw: Dict[bytes, bytes]) -> Dict[str, str]:
    return {k.decode("utf-8"): v.decode("utf-8") for k, v in raw.items()}


def _parse_exit_code(job_info: Dict[str, str]) -> Optional[int]:
    value = job_info.get("exit_code")
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _job_status(job_id: str, job_info: Dict[str, str]) -> JobStatus:
    return JobStatus(
        job_id=job_id,
        status=job_info.get("status", "unknown"),
        created_at=job_info.get("created_at", ""),
        started_at=job_info.get("started_at"),
        finished_at=job_info.get("finished_at"),
        exit_code=_parse_exit_code(job_info),
        error=job_info.get("error"),
    )


def _job_summary(job_info: Dict[str, str]) -> JobStatus:
    return _job_status(job_info.get("job_id", ""), job_info)

# Create router
router = APIRouter(prefix="/sandbox", tags=["sandbox"])

@router.post("/submit", response_model=Dict[str, str])
async def submit_job(
    req: SubmitJobRequest,
    x_api_key: str = Header(...),
    request: Any = None  # For rate limiting
):
    """Submit a job for sandbox execution"""

    # Check if sandbox is enabled
    if not SANDBOX_ENABLED:
        raise HTTPException(status_code=503, detail="sandbox service is disabled")

    # Authenticate
    require_api_key(x_api_key)

    # Apply rate limiting
    if request:
        await sandbox_rate_limiter.__call__(request)

    # Validate input
    if not req.source or len(req.source.strip()) == 0:
        raise HTTPException(status_code=400, detail="source code is required")

    if req.language not in ["python", "javascript"]:
        raise HTTPException(status_code=400, detail="Unsupported language. Supported languages: python, javascript")

    if req.timeout and (req.timeout < 1 or req.timeout > 300):
        raise HTTPException(status_code=400, detail="timeout must be between 1-300 seconds")

    # Validate source code for dangerous patterns
    req.source, code_validation = InputSanitizer.validate_code_source(req.source, req.language)

    # Per-user concurrency limit
    if x_api_key:
        user_key = f"sandbox:user:{x_api_key}:active_jobs"
        active_jobs = int(r.get(user_key) or 0)
        if active_jobs >= MAX_CONCURRENT_PER_USER:
            raise HTTPException(
                status_code=429,
                detail=f"Too many active sandbox jobs ({active_jobs}). Maximum {MAX_CONCURRENT_PER_USER} concurrent jobs per user."
            )

    # Generate job ID and paths
    job_id = str(uuid.uuid4())
    job_path = os.path.join(JOBS_DIR, job_id)
    os.makedirs(job_path, exist_ok=True)

    # Determine main file based on language
    mainfile = {
        "python": "main.py",
        "javascript": "main.js"
    }.get(req.language, "main")

    # Write source code to file
    source_path = os.path.join(job_path, mainfile)
    with open(source_path, "w") as f:
        f.write(req.source)

    # Prepare job metadata
    job_meta = {
        "job_id": job_id,
        "status": "queued",
        "language": req.language,
        "timeout": req.timeout or 10,
        "runtime_args": req.runtime_args or "",
        "created_at": datetime.utcnow().isoformat(),
        "path": job_path,
        "source_file": mainfile,
        "code_validation": json.dumps(code_validation) if code_validation else "{}",
    }

    # Track per-user active job count
    if x_api_key:
        user_key = f"sandbox:user:{x_api_key}:active_jobs"
        r.incr(user_key)
        r.expire(user_key, 3600)  # Auto-expire after 1 hour

    # Store job metadata in Redis
    r.hset(f"sandbox:job:{job_id}", mapping=job_meta)

    # Queue the job
    try:
        queue.enqueue(
            "sandbox_worker.run_job",
            job_id=job_id,
            language=req.language,
            timeout=req.timeout or 10,
            runtime_args=req.runtime_args or "",
            job_path=job_path
        )

        # Record job submission metrics
        record_job_submitted(job_id, req.language)

    except Exception as e:
        shutil.rmtree(job_path, ignore_errors=True)
        r.delete(f"sandbox:job:{job_id}")
        if x_api_key:
            user_key = f"sandbox:user:{x_api_key}:active_jobs"
            r.decr(user_key)
        raise HTTPException(status_code=500, detail=f"Sandbox execution failed: {str(e)}")

    return SuccessEnvelope(data=SubmitJobResponse(job_id=job_id))

@router.get("/status/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str, x_api_key: str = Header(...)):
    """Get the status of a sandbox job"""

    # Authenticate
    require_api_key(x_api_key)

    # Get job metadata from Redis
    job_key = f"sandbox:job:{job_id}"
    job_data = r.hgetall(job_key)

    if not job_data:
        raise HTTPException(status_code=404, detail="job not found")

    # Convert bytes to strings and parse
    job_info = {k.decode('utf-8'): v.decode('utf-8') for k, v in job_data.items()}

    return SuccessEnvelope(data=JobStatus(
        job_id=job_id,
        status=job_info.get("status", "unknown"),
        created_at=job_info.get("created_at", ""),
        started_at=job_info.get("started_at"),
        finished_at=job_info.get("finished_at"),
        exit_code=int(job_info.get("exit_code")) if job_info.get("exit_code") else None,
        error=job_info.get("error"),
    ))

@router.get("/logs/{job_id}")
async def get_job_logs(job_id: str, x_api_key: str = Header(...)):
    """Get logs for a completed sandbox job"""

    # Authenticate
    require_api_key(x_api_key)

    # Get job metadata
    job_key = f"sandbox:job:{job_id}"
    job_data = r.hgetall(job_key)

    if not job_data:
        raise HTTPException(status_code=404, detail="job not found")

    job_info = {k.decode('utf-8'): v.decode('utf-8') for k, v in job_data.items()}

    if job_info.get("status") not in ["finished", "failed"]:
        raise HTTPException(status_code=400, detail="job is not completed yet")

    # Get job path and read logs
    job_path = job_info.get("path")
    if not job_path or not os.path.exists(job_path):
        raise HTTPException(status_code=404, detail="job data not found")

    log_file = os.path.join(job_path, "stdout.log")
    if not os.path.exists(log_file):
        return SuccessEnvelope(data=JobLogsResponse(logs=""))

    try:
        file_size = os.path.getsize(log_file)
        if file_size > MAX_OUTPUT_SIZE:
            logs = _read_text_file(log_file, MAX_OUTPUT_SIZE)
            return SuccessEnvelope(data=JobLogsResponse(
                logs=logs,
                truncated=True,
                original_size=file_size,
                truncated_size=MAX_OUTPUT_SIZE,
            ))
        logs = _read_text_file(log_file)
        return SuccessEnvelope(data=JobLogsResponse(logs=logs))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read logs: {str(e)}")

@router.get("/artifacts/{job_id}")
async def list_job_artifacts(job_id: str, x_api_key: str = Header(...)):
    """List artifacts for a completed sandbox job"""

    # Authenticate
    require_api_key(x_api_key)

    # Get job metadata to verify job exists and is completed
    job_key = f"sandbox:job:{job_id}"
    job_data = r.hgetall(job_key)

    if not job_data:
        raise HTTPException(status_code=404, detail="job not found")

    job_info = {k.decode('utf-8'): v.decode('utf-8') for k, v in job_data.items()}

    if job_info.get("status") not in ["finished", "failed"]:
        raise HTTPException(status_code=400, detail="job is not completed yet")

    # Use artifact service to list artifacts with presigned URLs
    artifacts = await artifact_service.list_job_artifacts(job_id)

    api_artifacts = [
        ArtifactInfo(
            name=artifact.get("filename", ""),
            size=int(artifact.get("size_bytes", 0)),
            url=artifact.get("url", ""),
            created_at=artifact.get("uploaded_at", ""),
        )
        for artifact in artifacts
    ]

    return SuccessEnvelope(data=ArtifactListResponse(artifacts=api_artifacts))

@router.get("/artifacts/{job_id}/download/{filename}")
async def download_artifact(
    job_id: str,
    filename: str,
    x_api_key: str = Header(...)
):
    """Download a specific artifact file via presigned URL"""

    # Authenticate
    require_api_key(x_api_key)

    # Security: prevent directory traversal
    safe_filename = os.path.basename(filename)
    if safe_filename != filename:
        raise HTTPException(status_code=400, detail="invalid filename")

    # Get artifact metadata
    artifact_meta = await artifact_service.get_artifact_metadata(job_id, safe_filename)
    if not artifact_meta:
        raise HTTPException(status_code=404, detail="artifact not found")

    # Generate fresh presigned URL for download
    s3_key = artifact_meta.get("s3_key")
    if not s3_key:
        raise HTTPException(status_code=404, detail="artifact storage key not found")

    presigned_url = artifact_service.generate_presigned_url(s3_key, expiration_seconds=300)  # 5 minutes
    if not presigned_url:
        raise HTTPException(status_code=500, detail="failed to generate download URL")

    # Redirect to presigned URL
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=presigned_url, status_code=302)

@router.post("/cancel/{job_id}")
async def cancel_job(job_id: str, x_api_key: str = Header(...)):
    """Cancel a running sandbox job"""

    # Authenticate
    require_api_key(x_api_key)

    # Get job metadata
    job_key = f"sandbox:job:{job_id}"
    job_data = r.hgetall(job_key)

    if not job_data:
        raise HTTPException(status_code=404, detail="job not found")

    job_info = {k.decode('utf-8'): v.decode('utf-8') for k, v in job_data.items()}

    if job_info.get("status") not in ["queued", "running"]:
        raise HTTPException(status_code=400, detail="job cannot be cancelled")

    # Mark job as cancelled
    r.hset(job_key, "status", "cancelled")
    r.hset(job_key, "finished_at", datetime.utcnow().isoformat())
    r.hset(job_key, "error", "job cancelled by user")

    # Record cancellation metrics
    record_job_cancelled(job_id)

    # Decrement per-user active job counter if we can find the API key
    # (The key isn't available on cancel, so we use a best-effort scan)
    try:
        api_key_from_meta = job_info.get("api_key")
        if api_key_from_meta:
            user_key = f"sandbox:user:{api_key_from_meta}:active_jobs"
            current = int(r.get(user_key) or 0)
            if current > 0:
                r.decr(user_key)
    except Exception:
        pass

    # If job has a container, attempt to kill it (best-effort)
    container_id = job_info.get("container_id")
    if container_id and shutil.which("docker"):
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "kill", container_id,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.communicate(), timeout=5)
        except Exception:
            pass

    return SuccessEnvelope(data=CancelJobResponse(message="job cancelled successfully"))

@router.get("/health/status")
async def sandbox_health():
    """Get sandbox service health status"""

    if not SANDBOX_ENABLED:
        return SuccessEnvelope(data=SandboxHealthResponse(
            status="disabled",
            message="sandbox service is disabled",
        ))

    # Check Redis connectivity
    redis_ok = False
    redis_error_detail = None
    try:
        r.ping()
        redis_ok = True
    except ConnectionError as e:
        redis_error_detail = f"Connection error: {e}"
    except TimeoutError as e:
        redis_error_detail = f"Timeout: {e}"
    except Exception as e:
        redis_error_detail = f"Health check failed: {type(e).__name__}: {e}"

    # Check queue status
    queue_size = len(queue) if redis_ok else 0

    # Check if sandbox image is configured
    image_configured = bool(SANDBOX_IMAGE)

    # Determine overall status
    if redis_ok and image_configured:
        status = "healthy"
    elif not redis_ok:
        status = "degraded"
    else:
        status = "unhealthy"

    return SuccessEnvelope(data=SandboxHealthResponse(
        status=status,
        redis_connected=redis_ok,
        redis_error=redis_error_detail if not redis_ok else None,
        image_configured=image_configured,
        queue_depth=queue_size,
        enabled=SANDBOX_ENABLED,
        max_concurrent_per_user=MAX_CONCURRENT_PER_USER,
        max_output_size=MAX_OUTPUT_SIZE,
    ))

@router.post("/run", response_model=Dict[str, str])
async def run_sandbox_code(
    req: SubmitJobRequest,
    x_api_key: str = Header(...),
):
    """Alias for /submit - Execute code in sandbox"""
    return await submit_job(req, x_api_key)

@router.get("/jobs")
async def list_sandbox_jobs(
    x_api_key: str = Header(default=""),
    status: Optional[str] = None,
    limit: int = 100,
):
    """Get list of sandbox jobs from Redis."""
    if not SANDBOX_ENABLED:
        raise HTTPException(status_code=503, detail="sandbox service is disabled")

    # Basic auth check if API key provided
    if x_api_key and x_api_key != API_KEY:
        if os.getenv("ENVIRONMENT", "development") != "development":
            raise HTTPException(status_code=401, detail="Unauthorized")

    jobs = []
    try:
        for key in r.scan_iter("sandbox:job:*"):
            str_key = key.decode("utf-8") if isinstance(key, bytes) else key
            raw = r.hgetall(str_key)
            if not raw:
                continue
            job_info = _decode_job_data(raw)
            if status and job_info.get("status") != status:
                continue
            jobs.append(_job_summary(job_info))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list jobs: {str(e)}")

    jobs.sort(key=lambda j: j.created_at, reverse=True)
    jobs = jobs[:limit]

    return SuccessEnvelope(data=JobListResponse(jobs=jobs, total=len(jobs)))

@router.get("/jobs/{job_id}/logs")
async def get_job_logs_alias(
    job_id: str,
    x_api_key: str = Header(default=""),
):
    """Alias for /logs/{job_id} - Get job execution logs"""
    if not SANDBOX_ENABLED:
        raise HTTPException(status_code=503, detail="sandbox service is disabled")

    # Basic auth check if API key provided
    if x_api_key and x_api_key != API_KEY:
        if os.getenv("ENVIRONMENT", "development") != "development":
            raise HTTPException(status_code=401, detail="Unauthorized")

    # Call the existing logs implementation with proper auth
    return await get_job_logs(job_id, x_api_key)

@router.get("/metrics")
async def sandbox_metrics():
    """Get Prometheus metrics for sandbox operations"""
    return get_metrics_endpoint()