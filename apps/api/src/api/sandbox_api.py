"""
Sandbox API router for secure code execution
Provides endpoints for submitting, monitoring, and managing sandbox jobs
"""

import asyncio
import os
import uuid
from datetime import datetime
from typing import Any, Optional

import redis
import rq
import structlog
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

logger = structlog.get_logger()


class SandboxExecutionError(Exception):
    """Raised when a sandbox job cannot be queued or executed."""

    def __init__(self, job_id: str, container_id: str | None, reason: str):
        self.job_id = job_id
        self.container_id = container_id
        self.reason = reason
        super().__init__(f"Sandbox execution failed [{job_id}]: {reason}")


from .artifact_service import artifact_service
from .core.contracts import SandboxExecutionCompletedPayload, SuccessEnvelope
from .middleware.rate_limiter import RateLimiter
from .observability.events import event_emitter
from .sandbox_metrics import (
    get_metrics_endpoint,
    record_job_cancelled,
    record_job_submitted,
)

# Configuration from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
SANDBOX_IMAGE = os.getenv("SANDBOX_IMAGE", "goblin-assistant-sandbox:latest")
API_KEY = os.getenv("API_AUTH_KEY")
# Use local writable directory, default to /tmp/goblin_sandbox if not specified
JOBS_DIR = os.getenv("JOBS_DIR", "/tmp/goblin_sandbox")
SANDBOX_ENABLED = os.getenv("SANDBOX_ENABLED", "false").lower() == "true"

# Initialize Redis and RQ
r = redis.from_url(REDIS_URL)
queue = rq.Queue("sandbox-jobs", connection=r)

# Rate limiter for sandbox operations
sandbox_rate_limiter = RateLimiter(
    redis_url=REDIS_URL,
    requests_per_minute=int(os.getenv("SANDBOX_RATE_LIMIT_PER_MINUTE", "10")),
    requests_per_hour=int(os.getenv("SANDBOX_RATE_LIMIT_PER_HOUR", "100")),
)

# Ensure jobs directory exists
try:
    os.makedirs(JOBS_DIR, exist_ok=True)
except PermissionError:
    fallback_jobs_dir = "/tmp/goblin_sandbox"
    logger.warning(
        "sandbox_jobs_dir_unwritable",
        configured_jobs_dir=JOBS_DIR,
        fallback_jobs_dir=fallback_jobs_dir,
    )
    JOBS_DIR = fallback_jobs_dir
    os.makedirs(JOBS_DIR, exist_ok=True)


# Authentication dependency
def require_api_key(x_api_key: str = Header(...)) -> None:
    # Skip authentication in development mode
    if SANDBOX_ENABLED and os.getenv("ENVIRONMENT", "development") == "development":
        return
    if not API_KEY:
        raise HTTPException(
            status_code=500,
            detail="sandbox API key is not configured (set API_AUTH_KEY)",
        )
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="unauthorized")


# Pydantic models for API
class SubmitJobRequest(BaseModel):
    language: str
    source: str
    timeout: Optional[int] = 10
    runtime_args: Optional[str] = ""


class JobStatus(BaseModel):
    job_id: str
    status: str  # queued, running, finished, failed, cancelled
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    exit_code: Optional[int] = None
    error: Optional[str] = None


class ArtifactInfo(BaseModel):
    name: str
    size: int
    url: str
    created_at: str


class SubmitJobResponse(BaseModel):
    job_id: str


class JobLogsResponse(BaseModel):
    logs: str


class ArtifactListResponse(BaseModel):
    artifacts: list[ArtifactInfo]


class CancelJobResponse(BaseModel):
    message: str


class SandboxHealthResponse(BaseModel):
    status: str
    redis_connected: bool
    image_configured: bool
    queue_depth: int
    enabled: bool
    message: Optional[str] = None
    redis_error: Optional[str] = None


class SandboxJobSummary(BaseModel):
    job_id: str
    status: str
    language: str
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    exit_code: Optional[int] = None
    error: Optional[str] = None


class SandboxJobsResponse(BaseModel):
    jobs: list[SandboxJobSummary]
    total: int


def _decode_job_data(job_data: dict[bytes, bytes]) -> dict[str, str]:
    return {k.decode("utf-8"): v.decode("utf-8") for k, v in job_data.items()}


def _parse_exit_code(job_info: dict[str, str]) -> Optional[int]:
    if not job_info.get("exit_code"):
        return None
    return int(job_info["exit_code"])


def _job_status(job_id: str, job_info: dict[str, str]) -> JobStatus:
    return JobStatus(
        job_id=job_id,
        status=job_info.get("status", "unknown"),
        created_at=job_info.get("created_at", ""),
        started_at=job_info.get("started_at"),
        finished_at=job_info.get("finished_at"),
        exit_code=_parse_exit_code(job_info),
        error=job_info.get("error"),
    )


def _job_summary(job_info: dict[str, str]) -> SandboxJobSummary:
    return SandboxJobSummary(
        job_id=job_info.get("job_id", ""),
        status=job_info.get("status", "unknown"),
        language=job_info.get("language", ""),
        created_at=job_info.get("created_at", ""),
        started_at=job_info.get("started_at"),
        finished_at=job_info.get("finished_at"),
        exit_code=_parse_exit_code(job_info),
        error=job_info.get("error"),
    )


async def _run_blocking(func, *args, **kwargs):
    return await asyncio.to_thread(func, *args, **kwargs)


def _write_text_file(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _read_text_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


async def _emit_sandbox_completed(job_id: str, job_info: dict[str, str]) -> None:
    if job_info.get("status") not in {"finished", "failed", "cancelled"}:
        return
    await event_emitter.emit(
        "sandbox.execution.completed",
        source="api.sandbox_api",
        payload=SandboxExecutionCompletedPayload(
            job_id=job_id,
            status=job_info.get("status", "unknown"),
            language=job_info.get("language"),
            exit_code=_parse_exit_code(job_info),
            started_at=job_info.get("started_at"),
            finished_at=job_info.get("finished_at"),
            error=job_info.get("error"),
        ),
    )


# Create router
router = APIRouter(prefix="/sandbox", tags=["sandbox"])


@router.post("/submit", response_model=SuccessEnvelope[SubmitJobResponse])
async def submit_job(
    req: SubmitJobRequest,
    x_api_key: str = Header(...),
    request: Any = None,  # For rate limiting
) -> SuccessEnvelope[SubmitJobResponse]:
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
        raise HTTPException(
            status_code=400,
            detail="Unsupported language. Supported languages: python, javascript",
        )

    if req.timeout and (req.timeout < 1 or req.timeout > 300):
        raise HTTPException(status_code=400, detail="timeout must be between 1-300 seconds")

    # Generate job ID and paths
    job_id = str(uuid.uuid4())
    job_path = os.path.join(JOBS_DIR, job_id)
    await _run_blocking(os.makedirs, job_path, exist_ok=True)

    # Determine main file based on language
    mainfile = {"python": "main.py", "javascript": "main.js"}.get(req.language, "main")

    # Write source code to file
    source_path = os.path.join(job_path, mainfile)
    await _run_blocking(_write_text_file, source_path, req.source)

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
    }

    # Store job metadata in Redis
    await _run_blocking(r.hset, f"sandbox:job:{job_id}", mapping=job_meta)

    # Queue the job
    try:
        await _run_blocking(
            queue.enqueue,
            "sandbox_worker.run_job",
            job_id=job_id,
            language=req.language,
            timeout=req.timeout or 10,
            runtime_args=req.runtime_args or "",
            job_path=job_path,
        )

        # Record job submission metrics
        record_job_submitted(job_id, req.language)

    except SandboxExecutionError:
        raise
    except Exception as e:
        import shutil

        await _run_blocking(shutil.rmtree, job_path, True)
        await _run_blocking(r.delete, f"sandbox:job:{job_id}")
        err = SandboxExecutionError(job_id=job_id, container_id=None, reason=str(e))
        logger.error(
            "sandbox_job_queue_failed",
            job_id=job_id,
            language=req.language,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(status_code=500, detail=str(err)) from err

    return SuccessEnvelope(data=SubmitJobResponse(job_id=job_id))


@router.get("/status/{job_id}", response_model=SuccessEnvelope[JobStatus])
async def get_job_status(job_id: str, x_api_key: str = Header(...)) -> SuccessEnvelope[JobStatus]:
    """Get the status of a sandbox job"""

    # Authenticate
    require_api_key(x_api_key)

    # Get job metadata from Redis
    job_key = f"sandbox:job:{job_id}"
    job_data = await _run_blocking(r.hgetall, job_key)

    if not job_data:
        raise HTTPException(status_code=404, detail="job not found")

    # Convert bytes to strings and parse
    job_info = _decode_job_data(job_data)
    await _emit_sandbox_completed(job_id, job_info)

    return SuccessEnvelope(data=_job_status(job_id, job_info))


@router.get("/logs/{job_id}", response_model=SuccessEnvelope[JobLogsResponse])
async def get_job_logs(
    job_id: str, x_api_key: str = Header(...)
) -> SuccessEnvelope[JobLogsResponse]:
    """Get logs for a completed sandbox job"""

    # Authenticate
    require_api_key(x_api_key)

    # Get job metadata
    job_key = f"sandbox:job:{job_id}"
    job_data = await _run_blocking(r.hgetall, job_key)

    if not job_data:
        raise HTTPException(status_code=404, detail="job not found")

    job_info = _decode_job_data(job_data)

    if job_info.get("status") not in ["finished", "failed"]:
        raise HTTPException(status_code=400, detail="job is not completed yet")
    await _emit_sandbox_completed(job_id, job_info)

    # Get job path and read logs
    job_path = job_info.get("path")
    if not job_path or not os.path.exists(job_path):
        raise HTTPException(status_code=404, detail="job data not found")

    log_file = os.path.join(job_path, "stdout.log")
    if not os.path.exists(log_file):
        return SuccessEnvelope(data=JobLogsResponse(logs=""))

    try:
        logs = await _run_blocking(_read_text_file, log_file)
        return SuccessEnvelope(data=JobLogsResponse(logs=logs))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to read logs: {str(e)}")


@router.get("/artifacts/{job_id}", response_model=SuccessEnvelope[ArtifactListResponse])
async def list_job_artifacts(
    job_id: str, x_api_key: str = Header(...)
) -> SuccessEnvelope[ArtifactListResponse]:
    """List artifacts for a completed sandbox job"""

    # Authenticate
    require_api_key(x_api_key)

    # Get job metadata to verify job exists and is completed
    job_key = f"sandbox:job:{job_id}"
    job_data = await _run_blocking(r.hgetall, job_key)

    if not job_data:
        raise HTTPException(status_code=404, detail="job not found")

    job_info = _decode_job_data(job_data)

    if job_info.get("status") not in ["finished", "failed"]:
        raise HTTPException(status_code=400, detail="job is not completed yet")
    await _emit_sandbox_completed(job_id, job_info)

    # Use artifact service to list artifacts with presigned URLs
    artifacts = await artifact_service.list_job_artifacts(job_id)

    # Convert to API format
    api_artifacts: list[ArtifactInfo] = []
    for artifact in artifacts:
        api_artifacts.append(
            ArtifactInfo(
                name=artifact.get("filename", ""),
                size=int(artifact.get("size_bytes", 0)),
                url=artifact.get("url", ""),
                created_at=artifact.get("uploaded_at", ""),
            )
        )

    return SuccessEnvelope(data=ArtifactListResponse(artifacts=api_artifacts))


@router.get("/artifacts/{job_id}/download/{filename}")
async def download_artifact(job_id: str, filename: str, x_api_key: str = Header(...)) -> Any:
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

    presigned_url = artifact_service.generate_presigned_url(
        s3_key, expiration_seconds=300
    )  # 5 minutes
    if not presigned_url:
        raise HTTPException(status_code=500, detail="failed to generate download URL")

    # Redirect to presigned URL
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url=presigned_url, status_code=302)


@router.post("/cancel/{job_id}", response_model=SuccessEnvelope[CancelJobResponse])
async def cancel_job(
    job_id: str, x_api_key: str = Header(...)
) -> SuccessEnvelope[CancelJobResponse]:
    """Cancel a running sandbox job"""

    # Authenticate
    require_api_key(x_api_key)

    # Get job metadata
    job_key = f"sandbox:job:{job_id}"
    job_data = await _run_blocking(r.hgetall, job_key)

    if not job_data:
        raise HTTPException(status_code=404, detail="job not found")

    job_info = _decode_job_data(job_data)

    if job_info.get("status") not in ["queued", "running"]:
        raise HTTPException(status_code=400, detail="job cannot be cancelled")

    # Mark job as cancelled
    await _run_blocking(r.hset, job_key, "status", "cancelled")
    finished_at = datetime.utcnow().isoformat()
    await _run_blocking(r.hset, job_key, "finished_at", finished_at)
    await _run_blocking(r.hset, job_key, "error", "job cancelled by user")
    job_info.update(
        {
            "job_id": job_id,
            "status": "cancelled",
            "finished_at": finished_at,
            "error": "job cancelled by user",
        }
    )

    # Record cancellation metrics
    record_job_cancelled(job_id)

    # Kill the container if it's running
    container_id = job_info.get("container_id")
    if container_id:
        import shutil

        if shutil.which("docker"):
            try:
                proc = await asyncio.create_subprocess_exec(
                    "docker",
                    "kill",
                    container_id,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await asyncio.wait_for(proc.communicate(), timeout=10)
            except Exception as e:
                logger.warning("failed_to_kill_container", container_id=container_id, error=str(e))

    await _emit_sandbox_completed(job_id, job_info)

    return SuccessEnvelope(data=CancelJobResponse(message="job cancelled successfully"))


@router.get("/health/status", response_model=SuccessEnvelope[SandboxHealthResponse])
async def sandbox_health() -> SuccessEnvelope[SandboxHealthResponse]:
    """Get sandbox service health status"""

    if not SANDBOX_ENABLED:
        return SuccessEnvelope(
            data=SandboxHealthResponse(
                status="disabled",
                message="sandbox service is disabled",
                redis_connected=False,
                image_configured=bool(SANDBOX_IMAGE),
                queue_depth=0,
                enabled=False,
            )
        )

    # Check Redis connectivity
    redis_ok = False
    redis_error_detail = None
    try:
        await _run_blocking(r.ping)
        redis_ok = True
    except ConnectionError as e:
        # Redis connection refused - service likely not running
        redis_error_detail = f"Connection error: {e}"
        redis_ok = False
    except TimeoutError as e:
        # Redis connection timeout
        redis_error_detail = f"Timeout: {e}"
        redis_ok = False
    except Exception as e:
        # Other unexpected errors
        redis_error_detail = f"Health check failed: {type(e).__name__}: {e}"
        redis_ok = False

    # Check queue status
    queue_size = await _run_blocking(len, queue) if redis_ok else 0

    # Check if sandbox image is configured
    image_configured = bool(SANDBOX_IMAGE)

    # Determine overall status
    if redis_ok and image_configured:
        status = "healthy"
    elif not redis_ok:
        status = "degraded"
    else:
        status = "unhealthy"

    return SuccessEnvelope(
        data=SandboxHealthResponse(
            status=status,
            redis_connected=redis_ok,
            image_configured=image_configured,
            queue_depth=queue_size,
            enabled=SANDBOX_ENABLED,
            redis_error=redis_error_detail,
        )
    )


@router.post("/run", response_model=SuccessEnvelope[SubmitJobResponse])
async def run_sandbox_code(
    req: SubmitJobRequest,
    x_api_key: str = Header(...),
) -> SuccessEnvelope[SubmitJobResponse]:
    """Alias for /submit - Execute code in sandbox"""
    return await submit_job(req, x_api_key)


@router.get("/jobs", response_model=SuccessEnvelope[SandboxJobsResponse])
async def list_sandbox_jobs(
    x_api_key: str = Header(default=""),
    status: Optional[str] = None,
    limit: int = 100,
) -> SuccessEnvelope[SandboxJobsResponse]:
    """Get list of sandbox jobs from Redis."""
    if not SANDBOX_ENABLED:
        raise HTTPException(status_code=503, detail="sandbox service is disabled")

    # Basic auth check if API key provided
    if x_api_key and x_api_key != API_KEY:
        if os.getenv("ENVIRONMENT", "development") != "development":
            raise HTTPException(status_code=401, detail="Unauthorized")

    jobs: list[SandboxJobSummary] = []
    try:
        keys = await _run_blocking(lambda: list(r.scan_iter("sandbox:job:*")))
        for key in keys:
            redis_key = key.decode("utf-8") if isinstance(key, bytes) else key
            raw = await _run_blocking(r.hgetall, redis_key)
            if not raw:
                continue
            job_info = _decode_job_data(raw)
            if status and job_info.get("status") != status:
                continue
            await _emit_sandbox_completed(job_info.get("job_id", ""), job_info)
            jobs.append(_job_summary(job_info))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to list jobs: {str(e)}")

    # Sort by created_at descending, apply limit
    jobs.sort(key=lambda job: job.created_at, reverse=True)
    jobs = jobs[:limit]

    return SuccessEnvelope(data=SandboxJobsResponse(jobs=jobs, total=len(jobs)))


@router.get("/jobs/{job_id}/logs", response_model=SuccessEnvelope[JobLogsResponse])
async def get_job_logs_alias(
    job_id: str,
    x_api_key: str = Header(default=""),
) -> SuccessEnvelope[JobLogsResponse]:
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
async def sandbox_metrics() -> Any:
    """Get Prometheus metrics for sandbox operations"""
    return get_metrics_endpoint()
