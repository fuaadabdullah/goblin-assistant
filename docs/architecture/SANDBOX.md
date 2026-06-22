# Sandbox — Engine Pillar

## Purpose

The Sandbox pillar provides secure, isolated code execution for untrusted user code. It uses Docker containerisation with resource limits, an RQ/Redis job queue for async processing, S3 artifact storage, and comprehensive security hardening to prevent host system compromise.

---

## Architecture

```
Client
  │
  │ POST /api/v1/sandbox/run
  │ GET  /api/v1/sandbox/jobs/{job_id}
  │ GET  /api/v1/sandbox/jobs/{job_id}/logs
  │ GET  /api/v1/sandbox/jobs/{job_id}/artifacts
  ▼
┌────────────────────────────────────┐
│        sandbox_api.py              │
│   FastAPI router                   │
│   • submit_job()                   │
│   • get_job_status()              │
│   • get_job_logs()                │
│   • list_job_artifacts()          │
│   • download_artifact()           │
│   • cancel_job()                  │
│   • sandbox_health()              │
└──────┬───────────────────────────-┘
       │
       ▼
┌────────────────────────────────────┐
│          Redis + RQ                │
│   • Job queue: sandbox-jobs       │
│   • Job state: sandbox:job:{id}   │
│   • Artifact metadata            │
└──────┬───────────────────────────-┘
       │
       ▼
┌────────────────────────────────────┐
│        RQ Worker                   │
│   run_job(job_id)                 │
│                                    │
│   1. Write code to JOBS_DIR/{id}/  │
│   2. docker run [hardened]         │
│   3. Capture stdout/stderr        │
│   4. Upload artifacts to S3       │
│   5. Update job status            │
└────────────────────────────────────┘
       │
       ▼
┌────────────────────────────────────┐
│     Docker Container              │
│   goblin-assistant-sandbox        │
│                                    │
│   • --rm (auto cleanup)           │
│   • --network none                 │
│   • --cap-drop ALL                 │
│   • --security-opt no-new-priv    │
│   • Root FS: read-only             │
│   • /tmp: tmpfs (64 MB)            │
│   • /work: job bind mount          │
│   • Inner timeout via entrypoint   │
└────────────────────────────────────┘
       │
       ▼
┌────────────────────────────────────┐
│        S3 Artifact Store          │
│   • Non-log artifacts uploaded    │
│   • TTL: 7 days                   │
│   • Presigned URLs: 5 min         │
└────────────────────────────────────┘
```

---

## Core Components

### 1. Sandbox API Router (`sandbox_api.py`)

The FastAPI router exposes the sandbox as RESTful endpoints. All sandbox endpoints require `X-API-Key` header authentication (separate from user auth).

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/v1/sandbox/run` | POST | Submit code for execution |
| `/api/v1/sandbox/jobs/{job_id}` | GET | Get job status |
| `/api/v1/sandbox/jobs/{job_id}/logs` | GET | Get combined stdout+stderr |
| `/api/v1/sandbox/jobs/{job_id}/artifacts` | GET | List output artifacts |
| `/api/v1/sandbox/jobs/{job_id}/artifacts/{filename}` | GET | Download artifact |
| `/api/v1/sandbox/jobs/{job_id}/cancel` | POST | Cancel queued job |
| `/api/v1/sandbox/jobs` | GET | List all sandbox jobs |
| `/api/v1/sandbox/health` | GET | Sandbox health check |
| `/api/v1/sandbox/metrics` | GET | Prometheus metrics |

### 2. Job Queue (Redis + RQ)

Jobs are managed through Redis-backed RQ queues:

- **Queue name**: `sandbox-jobs`
- **Job state keys**: `sandbox:job:{job_id}` (Redis hash)
- **State fields**: `status`, `language`, `exit_code`, `error`, `created_at`, `completed_at`, `execution_time`

**Job lifecycle states**:
```
queued ──► running ──► completed (exit_code=0)
queued ──► running ──► completed (exit_code!=0)
queued ──► running ──► failed (timeout/container error)
queued ──► cancelled
```

### 3. Sandbox Models (`sandbox_models.py`)

Pydantic models for request/response contracts:

```python
class SubmitJobRequest(BaseModel):
    language: str           # python, javascript, typescript, go, ruby, rust
    code: str               # source code to execute
    timeout_seconds: int = 30   # max 120
    memory_limit_mb: int = 256  # max 1024

class JobStatus(BaseModel):
    job_id: str
    status: str             # queued, running, completed, failed, cancelled
    exit_code: Optional[int]
    created_at: datetime
    completed_at: Optional[datetime]
    execution_time_seconds: Optional[float]

class JobLogsResponse(BaseModel):
    logs: str               # combined stdout + stderr
    job_id: str
    truncated: bool         # true if logs exceeded max size

class ArtifactInfo(BaseModel):
    filename: str
    size_bytes: int
    content_type: str
    presigned_url: Optional[str]
```

### 4. Sandbox Metrics (`sandbox_metrics.py`)

Prometheus-compatible metrics for monitoring sandbox operations:

| Metric | Type | Labels |
|---|---|---|
| `sandbox_jobs_submitted_total` | Counter | language |
| `sandbox_jobs_started_total` | Counter | language |
| `sandbox_jobs_completed_total` | Counter | exit_code |
| `sandbox_jobs_failed_total` | Counter | failure_type |
| `sandbox_jobs_cancelled_total` | Counter | — |
| `sandbox_containers_killed_total` | Counter | reason |
| `sandbox_artifact_uploads_total` | Counter | success |
| `sandbox_cleanup_runs_total` | Counter | success |
| `sandbox_queue_depth` | Gauge | — |

### 5. Artifact Service (`artifact_service.py`)

Manages S3-based artifact storage with TTL-based cleanup:

- **Upload**: After job completion, non-log output files are uploaded to S3
- **Presigned URLs**: Download endpoints return S3 presigned URLs with 5-minute TTL
- **TTL Cleanup**: Background task deletes artifacts older than 7 days
- **File hash**: SHA256 hash computed for each uploaded artifact
- **Content types**: Auto-detected from filename extension

---

## Sandbox Execution Flow

### Job Submission

1. Client sends `POST /api/v1/sandbox/run` with `{language, code, timeout_seconds, memory_limit_mb}`
2. Router validates: language is supported, code is non-empty, timeout within limits
3. Job ID is generated (`sandbox-job-{uuid}`)
4. Job is enqueued on the `sandbox-jobs` RQ queue with metadata
5. Redis state is set to `queued`
6. Response returns `{job_id, status: "queued", language, created_at}`

### Job Execution (RQ Worker)

1. Worker picks up the job from the queue
2. Status updates to `running` in Redis
3. Code is written to `JOBS_DIR/{job_id}/main.{ext}`
4. Docker container is launched with hardened parameters:
   ```
   docker run --rm \
     --network none \
     --cap-drop ALL \
     --security-opt no-new-privileges \
     --memory {memory_limit_mb}m \
     --cpus 1 \
     -v {job_dir}:/work:rw \
     goblin-assistant-sandbox \
     {language} {timeout_seconds}
   ```
5. `sandbox_entrypoint.sh` compiles/executes the code with an inner timeout
6. stdout+stderr are captured to log files
7. On completion:
   - Exit code and combined logs are stored in Redis
   - Non-log artifact files are uploaded to S3
   - Status updates to `completed` (exit_code=0) or `completed` (exit_code≠0)
   - `sandbox.execution.completed` event is emitted
8. On timeout or container error:
   - Status updates to `failed`
   - `sandbox.job_failed` event is emitted
   - Container is force-removed

### Artifact Retrieval

1. Client calls `GET /api/v1/sandbox/jobs/{job_id}/artifacts`
2. Router queries S3 for artifacts matching the job ID prefix
3. Returns list with filenames, sizes, content types, and presigned URLs
4. Client downloads artifacts directly from S3 using presigned URLs (5 min TTL)

### Job Cancellation

1. Client calls `POST /api/v1/sandbox/jobs/{job_id}/cancel`
2. If job is still `queued`, it is removed from the RQ queue
3. Status updates to `cancelled`
4. `sandbox.job_cancelled` event is emitted

---

## Security Hardening

### Docker Runtime Security

| Control | Implementation |
|---|---|
| **Container isolation** | `--rm` for auto-cleanup, `--network none` for network isolation |
| **Capability drop** | `--cap-drop ALL` removes all Linux capabilities |
| **Privilege escalation** | `--security-opt no-new-privileges` prevents privilege escalation |
| **Filesystem** | Root FS is read-only in the Docker image; only `/work` is writable (job bind mount) |
| **Memory limit** | Configurable per job via `--memory` (default 256 MB, max 1024 MB) |
| **CPU limit** | Limited to 1 CPU core via `--cpus 1` |

### Additional Hardening (Optional)

| Control | Location | Purpose |
|---|---|---|
| **Seccomp profile** | `/etc/sandbox/seccomp.json` | Restricts available system calls |
| **AppArmor profile** | `sandbox-runner` | Mandatory access control for container |
| **Inner timeout** | `sandbox_entrypoint.sh` | Prevents runaway processes (default 20s) |
| **Artifact TTL** | S3 lifecycle policy | Auto-deletes artifacts after 7 days |

### Supported Languages

| Language | Extension | Entry Point |
|---|---|---|
| Python | `.py` | `python3 /work/main.py` |
| JavaScript | `.js` | `node /work/main.js` |
| TypeScript | `.ts` | `npx ts-node /work/main.ts` |
| Go | `.go` | `go run /work/main.go` |
| Ruby | `.rb` | `ruby /work/main.rb` |
| Rust | `.rs` | `rustc /work/main.rs -o /work/main && /work/main` |

**Bash is explicitly not supported** — shell execution is too powerful to sandbox safely in this model.

---

## Failure Mode Matrix

| Failure | Detection | Action | Metric Event |
|---|---|---|---|
| Language not supported | Router validation | Return 400 | — |
| Code too large | Router validation (configurable limit) | Return 413 | — |
| RQ queue full | Queue enqueue failure | Return 503 | — |
| Docker daemon unavailable | Container start failure | Job → `failed` | `sandbox_jobs_failed_total` |
| Code timeout | Inner timeout fires | Job → `failed` | `sandbox_jobs_failed_total` |
| Container OOM | Docker exit code 137 | Job → `failed` | `sandbox_jobs_failed_total` |
| Compile error (Go/Rust) | Non-zero exit code | Job → `completed` (exit_code≠0) | `sandbox_jobs_completed_total` |
| Runtime error | Non-zero exit code | Job → `completed` (exit_code≠0) | `sandbox_jobs_completed_total` |
| S3 upload failure | Upload exception | Job completed, artifact missing | `sandbox_artifact_uploads_total` |
| Artifact TTL expiry | S3 lifecycle policy | Artifact deleted | — |

---

## Key Configuration

```python
# From environment / config
JOBS_DIR = "/tmp/sandbox-jobs"          # Working directory for job files
SANDBOX_TIMEOUT_SECONDS = 30            # Default timeout (max 120)
SANDBOX_MEMORY_LIMIT_MB = 256           # Default memory limit (max 1024)
INNER_TIMEOUT = 20                      # Container inner timeout (entrypoint)
ARTIFACT_TTL_DAYS = 7                   # S3 artifact retention
S3_BUCKET = "goblin-sandbox-artifacts"  # S3 bucket name
RQ_QUEUE_NAME = "sandbox-jobs"         # RQ queue name
```

---

## Testing Guidance

### Unit Tests
- `tests/contract/test_sandbox_contract.py`: Assert request/response shape
- `apps/api/src/api/tests/test_auth_security.py`: Sandbox security tests (bash rejected, valid languages accepted)

### Integration Tests
- `tests/integration/engine/test_sandbox_submit_and_poll.py`: Submit Python code, poll for completion, verify logs
- `tests/integration/engine/test_sandbox_timeout.py`: Submit infinite loop, verify timeout failure
- `tests/integration/engine/test_sandbox_artifacts.py`: Submit code that produces a file, verify artifact list
- `tests/integration/engine/test_sandbox_cancellation.py`: Submit slow job, cancel, verify cancelled status

### Performance Tests
- `tests/performance/test_sandbox_throughput.py`: Submit N jobs, measure throughput (target > 10 jobs/min under Docker)

---

## Related Documents

- `ENGINE_CONTRACTS.md` — Canonical interface contract for this pillar
- `Dockerfile.sandbox` — Sandbox container image definition
- `docker/sandbox/` — Sandbox entrypoint and config
- `apps/api/src/api/sandbox_api.py` — Sandbox API router
- `apps/api/src/api/sandbox_models.py` — Request/response models
- `apps/api/src/api/sandbox_metrics.py` — Prometheus metrics collector
- `apps/api/src/api/sandbox_job_helpers.py` — Job lifecycle helpers
- `apps/api/src/api/artifact_service.py` — S3 artifact management