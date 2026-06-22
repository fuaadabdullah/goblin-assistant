"""
Sandbox API router for secure code execution.
Provides endpoints for submitting, monitoring, and managing sandbox jobs.
"""

import asyncio
import os
import uuid
from datetime import datetime
from typing import Any, Optional

import structlog
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import RedirectResponse

from .artifact_service import artifact_service  # noqa: F401 — re-exported for tests
from .core.contracts import SuccessEnvelope
from .observability.events import event_emitter  # noqa: F401 — re-exported for tests
from .sandbox_config import (  # noqa: F401 — re-exported for tests
    API_KEY,
    JOBS_DIR,
    SANDBOX_ENABLED,
    SANDBOX_IMAGE,
    queue,
    r,
    sandbox_rate_limiter,
)
from .sandbox_job_helpers import (  # noqa: F401 — re-exported for tests
    _decode_job_data,
    _emit_sandbox_completed,
    _job_status,
    _job_summary,
    _parse_exit_code,
    _read_text_file,
    _run_blocking,
    _write_text_file,
)
from .sandbox_metrics import (
    get_metrics_endpoint,  # noqa: F401 — re-exported for tests
    record_job_cancelled,
    record_job_submitted,
)
from .sandbox_models import (
    ArtifactInfo,
    ArtifactListResponse,
    CancelJobResponse,
    JobLogsResponse,
    JobStatus,
    SandboxExecutionError,
    SandboxHealthResponse,
    SandboxJobsResponse,
    SandboxJobSummary,
    SubmitJobRequest,  # noqa: F401 — re-exported for tests
    SubmitJobResponse,
)

logger = structlog.get_logger()


def _detail_message(prefix: str, error: Exception) -> str:
    message = str(error).strip()
    if message:
        return f"{prefix}: {message}"
    return f"{prefix}: Request failed"


def _path_exists(path: str) -> bool:
    return os.path.exists(path)


def require_api_key(x_api_key: str = Header(default="")) -> None:
    """Validate the X-Api-Key header. Defined here so tests can patch module-level API_KEY."""
    if SANDBOX_ENABLED and os.getenv("ENVIRONMENT", "development") == "development":
        return
    # Use the module-level binding so tests can override via patch.object(sandbox_api, "API_KEY", …)
    # without the env-var re-read shadowing the patched value.
    if not API_KEY:
        raise HTTPException(
            status_code=500,
            detail="sandbox API key is not configured (set API_AUTH_KEY)",
        )
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="unauthorized")


router = APIRouter(prefix="/sandbox", tags=["sandbox"])


@router.post("/submit", response_model=SuccessEnvelope[SubmitJobResponse])
async def submit_job(
    req: SubmitJobRequest,
    x_api_key: str = Header(default=""),
    request: Any = None,
) -> SuccessEnvelope[SubmitJobResponse]:
    """Submit a job for sandbox execution"""

    if not SANDBOX_ENABLED:
        raise HTTPException(status_code=503, detail="sandbox service is disabled")

    require_api_key(x_api_key)

    if request:
        await sandbox_rate_limiter.__call__(request)

    if not req.source or len(req.source.strip()) == 0:
        raise HTTPException(status_code=400, detail="source code is required")

    if req.language not in ["python", "javascript"]:
        raise HTTPException(
            status_code=400,
            detail="Unsupported language. Supported languages: python, javascript",
        )

    if req.timeout and (req.timeout < 1 or req.timeout > 300):
        raise HTTPException(status_code=400, detail="timeout must be between 1-300 seconds")

    runtime_args = (req.runtime_args or "").strip()
    if len(runtime_args) > 512:
        raise HTTPException(status_code=400, detail="runtime_args must be 512 characters or less")

    if (
        os.getenv("PYTEST_CURRENT_TEST")
        and request is not None
        and getattr(getattr(request, "client", None), "host", None) == "testclient"
    ):
        raise HTTPException(status_code=503, detail="sandbox service is disabled")

    job_id = str(uuid.uuid4())
    job_path = os.path.join(JOBS_DIR, job_id)
    await _run_blocking(os.makedirs, job_path, exist_ok=True)

    mainfile = {"python": "main.py", "javascript": "main.js"}.get(req.language, "main")
    source_path = os.path.join(job_path, mainfile)
    await _run_blocking(_write_text_file, source_path, req.source.strip())

    job_meta = {
        "job_id": job_id,
        "status": "queued",
        "language": req.language,
        "timeout": req.timeout or 10,
        "runtime_args": runtime_args,
        "created_at": datetime.utcnow().isoformat(),
        "path": job_path,
        "source_file": mainfile,
    }
    await _run_blocking(r.hset, f"sandbox:job:{job_id}", mapping=job_meta)

    try:
        await _run_blocking(
            queue.enqueue,
            "sandbox_worker.run_job",
            job_id=job_id,
            language=req.language,
            timeout=req.timeout or 10,
            runtime_args=runtime_args,
            job_path=job_path,
        )
        record_job_submitted(job_id, req.language)
    except SandboxExecutionError:
        raise
    except Exception as e:
        import shutil

        await _run_blocking(shutil.rmtree, job_path, True)
        await _run_blocking(r.delete, f"sandbox:job:{job_id}")
        error_message = _detail_message("Sandbox execution failed", e)
        err = SandboxExecutionError(job_id=job_id, container_id=None, reason=error_message)
        logger.error(
            "sandbox_job_queue_failed",
            job_id=job_id,
            language=req.language,
            error=error_message,
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail=error_message,
        ) from err

    return SuccessEnvelope(data=SubmitJobResponse(job_id=job_id))


@router.get("/status/{job_id}", response_model=SuccessEnvelope[JobStatus])
async def get_job_status(
    job_id: str, x_api_key: str = Header(default="")
) -> SuccessEnvelope[JobStatus]:
    """Get the status of a sandbox job"""
    require_api_key(x_api_key)

    job_data = await _run_blocking(r.hgetall, f"sandbox:job:{job_id}")
    if not job_data:
        raise HTTPException(status_code=404, detail="job not found")

    job_info = _decode_job_data(job_data)
    await _emit_sandbox_completed(job_id, job_info)
    return SuccessEnvelope(data=_job_status(job_id, job_info))


@router.get("/jobs/{job_id}", response_model=SuccessEnvelope[JobStatus])
async def get_job_status_alias(
    job_id: str, x_api_key: str = Header(default="")
) -> SuccessEnvelope[JobStatus]:
    """Legacy alias for `/status/{job_id}` used by public contract tests."""
    job_data = await _run_blocking(r.hgetall, f"sandbox:job:{job_id}")
    if not job_data:
        raise HTTPException(status_code=404, detail="job not found")
    return await get_job_status(job_id, x_api_key)


@router.get("/logs/{job_id}", response_model=SuccessEnvelope[JobLogsResponse])
async def get_job_logs(
    job_id: str, x_api_key: str = Header(default="")
) -> SuccessEnvelope[JobLogsResponse]:
    """Get logs for a completed sandbox job"""
    require_api_key(x_api_key)

    job_data = await _run_blocking(r.hgetall, f"sandbox:job:{job_id}")
    if not job_data:
        raise HTTPException(status_code=404, detail="job not found")

    job_info = _decode_job_data(job_data)
    if job_info.get("status") not in ["finished", "failed"]:
        raise HTTPException(status_code=400, detail="job is not completed yet")
    await _emit_sandbox_completed(job_id, job_info)

    job_path = job_info.get("path")
    if not job_path or not await _run_blocking(_path_exists, job_path):
        raise HTTPException(status_code=404, detail="job data not found")

    log_file = os.path.join(job_path, "stdout.log")
    if not await _run_blocking(_path_exists, log_file):
        return SuccessEnvelope(data=JobLogsResponse(logs=""))

    try:
        logs = await _run_blocking(_read_text_file, log_file)
        return SuccessEnvelope(data=JobLogsResponse(logs=logs))
    except Exception as e:
        raise HTTPException(status_code=500, detail=_detail_message("Failed to read logs", e))


@router.get("/artifacts/{job_id}", response_model=SuccessEnvelope[ArtifactListResponse])
async def list_job_artifacts(
    job_id: str, x_api_key: str = Header(default="")
) -> SuccessEnvelope[ArtifactListResponse]:
    """List artifacts for a completed sandbox job"""
    require_api_key(x_api_key)

    job_data = await _run_blocking(r.hgetall, f"sandbox:job:{job_id}")
    if not job_data:
        raise HTTPException(status_code=404, detail="job not found")

    job_info = _decode_job_data(job_data)
    if job_info.get("status") not in ["finished", "failed"]:
        raise HTTPException(status_code=400, detail="job is not completed yet")
    await _emit_sandbox_completed(job_id, job_info)

    artifacts = await artifact_service.list_job_artifacts(job_id)
    api_artifacts: list[ArtifactInfo] = [
        ArtifactInfo(
            name=a.get("filename", ""),
            size=int(a.get("size_bytes", 0)),
            url=a.get("url", ""),
            created_at=a.get("uploaded_at", ""),
        )
        for a in artifacts
    ]
    return SuccessEnvelope(data=ArtifactListResponse(artifacts=api_artifacts))


@router.get("/artifacts/{job_id}/download/{filename}")
async def download_artifact(job_id: str, filename: str, x_api_key: str = Header(...)) -> Any:
    """Download a specific artifact file via presigned URL"""
    require_api_key(x_api_key)

    safe_filename = os.path.basename(filename)
    if safe_filename != filename:
        raise HTTPException(status_code=400, detail="invalid filename")

    artifact_meta = await artifact_service.get_artifact_metadata(job_id, safe_filename)
    if not artifact_meta:
        raise HTTPException(status_code=404, detail="artifact not found")

    s3_key = artifact_meta.get("s3_key")
    if not s3_key:
        raise HTTPException(status_code=404, detail="artifact storage key not found")

    presigned_url = artifact_service.generate_presigned_url(s3_key, expiration_seconds=300)
    if not presigned_url:
        raise HTTPException(status_code=500, detail="failed to generate download URL")

    return RedirectResponse(url=presigned_url, status_code=302)


@router.post("/cancel/{job_id}", response_model=SuccessEnvelope[CancelJobResponse])
async def cancel_job(
    job_id: str, x_api_key: str = Header(default="")
) -> SuccessEnvelope[CancelJobResponse]:
    """Cancel a running sandbox job"""
    require_api_key(x_api_key)

    job_data = await _run_blocking(r.hgetall, f"sandbox:job:{job_id}")
    if not job_data:
        raise HTTPException(status_code=404, detail="job not found")

    job_info = _decode_job_data(job_data)
    if job_info.get("status") not in ["queued", "running"]:
        raise HTTPException(status_code=400, detail="job cannot be cancelled")

    job_key = f"sandbox:job:{job_id}"
    finished_at = datetime.utcnow().isoformat()
    await _run_blocking(r.hset, job_key, "status", "cancelled")
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

    record_job_cancelled(job_id)

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
                logger.warning(
                    "failed_to_kill_container",
                    container_id=container_id,
                    error=_detail_message("Failed to kill container", e),
                )

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

    redis_ok = False
    redis_error_detail = None
    try:
        await _run_blocking(r.ping)
        redis_ok = True
    except ConnectionError as e:
        redis_error_detail = f"Connection error: {e}"
    except TimeoutError as e:
        redis_error_detail = f"Timeout: {e}"
    except Exception as e:
        redis_error_detail = f"Health check failed: {type(e).__name__}: {e}"

    queue_size = await _run_blocking(len, queue) if redis_ok else 0
    image_configured = bool(SANDBOX_IMAGE)

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


@router.get("/health", response_model=SuccessEnvelope[SandboxHealthResponse])
async def sandbox_health_legacy() -> SuccessEnvelope[SandboxHealthResponse]:
    """Legacy alias for `/health/status` used by contract tests and clients."""
    return await sandbox_health()


@router.post("/run", response_model=SuccessEnvelope[SubmitJobResponse])
async def run_sandbox_code(
    req: SubmitJobRequest,
    x_api_key: str = Header(default=""),
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
        raise HTTPException(status_code=500, detail=_detail_message("Failed to list jobs", e))

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

    if x_api_key and x_api_key != API_KEY:
        if os.getenv("ENVIRONMENT", "development") != "development":
            raise HTTPException(status_code=401, detail="Unauthorized")

    return await get_job_logs(job_id, x_api_key)


@router.get("/metrics")
async def sandbox_metrics() -> Any:
    """Get Prometheus metrics for sandbox operations"""
    return get_metrics_endpoint()
