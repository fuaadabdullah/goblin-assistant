"""
Sandbox API router for secure code execution
Provides endpoints for submitting, monitoring, and managing sandbox jobs
"""

import os
import uuid
import json
import time
from typing import Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Header, Depends, Query
from pydantic import BaseModel
import redis
import rq
from rq import Queue, Worker

# Import from existing infrastructure
from .storage.cache import cache
from .middleware.rate_limiter import RateLimiter
from .artifact_service import artifact_service
from .sandbox_metrics import (
    record_job_submitted, record_job_cancelled,
    get_metrics_endpoint, update_rq_metrics
)

# Configuration from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
SANDBOX_IMAGE = os.getenv("SANDBOX_IMAGE", "ghcr.io/yourorg/sandbox:latest")
API_KEY = os.getenv("API_AUTH_KEY", "devkey")
JOBS_DIR = os.getenv("JOBS_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sandbox_jobs"))
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
os.makedirs(JOBS_DIR, exist_ok=True)

# Authentication dependency
def require_api_key(x_api_key: str = Header(...)):
    # Skip authentication in development mode
    if SANDBOX_ENABLED and os.getenv("ENVIRONMENT", "development") == "development":
        return
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

    if req.language not in ["python", "javascript", "bash"]:
        raise HTTPException(status_code=400, detail="unsupported language")

    if req.timeout and (req.timeout < 1 or req.timeout > 300):
        raise HTTPException(status_code=400, detail="timeout must be between 1-300 seconds")

    # Generate job ID and paths
    job_id = str(uuid.uuid4())
    job_path = os.path.join(JOBS_DIR, job_id)
    os.makedirs(job_path, exist_ok=True)

    # Determine main file based on language
    mainfile = {
        "python": "main.py",
        "javascript": "main.js",
        "bash": "script.sh"
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
        "source_file": mainfile
    }

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
        # Cleanup on failure
        import shutil
        shutil.rmtree(job_path, ignore_errors=True)
        r.delete(f"sandbox:job:{job_id}")
        raise HTTPException(status_code=500, detail=f"failed to queue job: {str(e)}")

    return {"job_id": job_id}

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

    return JobStatus(
        job_id=job_id,
        status=job_info.get("status", "unknown"),
        created_at=job_info.get("created_at", ""),
        started_at=job_info.get("started_at"),
        finished_at=job_info.get("finished_at"),
        exit_code=int(job_info.get("exit_code")) if job_info.get("exit_code") else None,
        error=job_info.get("error")
    )

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
        return {"logs": ""}

    try:
        with open(log_file, "r") as f:
            logs = f.read()
        return {"logs": logs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to read logs: {str(e)}")

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
    artifacts = artifact_service.list_job_artifacts(job_id)

    # Convert to API format
    api_artifacts = []
    for artifact in artifacts:
        api_artifacts.append(ArtifactInfo(
            name=artifact.get("filename", ""),
            size=int(artifact.get("size_bytes", 0)),
            url=artifact.get("url", ""),
            created_at=artifact.get("uploaded_at", "")
        ))

    return {"artifacts": api_artifacts}

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
    artifact_meta = artifact_service.get_artifact_metadata(job_id, safe_filename)
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

    # TODO: If running in container, kill the container

    return {"message": "job cancelled successfully"}

@router.get("/health/status")
async def sandbox_health():
    """Get sandbox service health status"""

    if not SANDBOX_ENABLED:
        return {
            "status": "disabled",
            "message": "sandbox service is disabled"
        }

    # Check Redis connectivity
    redis_ok = False
    try:
        r.ping()
        redis_ok = True
    except:
        pass

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

    return {
        "status": status,
        "redis_connected": redis_ok,
        "image_configured": image_configured,
        "queue_depth": queue_size,
        "enabled": SANDBOX_ENABLED
    }

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
):
    """Get list of sandbox jobs (placeholder)"""
    if not SANDBOX_ENABLED:
        raise HTTPException(status_code=503, detail="sandbox service is disabled")
    
    # Basic auth check if API key provided
    if x_api_key and x_api_key != API_KEY:
        if os.getenv("ENVIRONMENT", "development") != "development":
            raise HTTPException(status_code=401, detail="Unauthorized")
    
    # In a real implementation, query Redis/database for job list
    return {"jobs": [], "total": 0}

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