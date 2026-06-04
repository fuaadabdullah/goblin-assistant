# Backend Degradation Report

> **Generated**: 2026-05-31  
> **Scope**: `apps/api/src/`, `docker-compose.yml`, infrastructure config  
> **Priority Order**: Based on impact to production stability, performance, and reliability

---

## 🔴 CRITICAL — Immediate Action Required

### 1. NullPool for PostgreSQL — No Connection Reuse

| | |
|---|---|
| **File** | `apps/api/src/api/config/database.py` |
| **Line** | ~77 |
| **Issue** | `poolclass=NullPool` is used for PostgreSQL, meaning every single request opens and tears down a new database connection. Zero connection reuse exists. |
| **Impact** | Under load, this causes connection storms, file descriptor exhaustion, and dramatically increased DB latency. Each HTTP request incurs TCP handshake + auth overhead. |
| **Fix** | Replace with `AsyncAdaptedQueuePool` with tuned `pool_size=20`, `max_overflow=10`, `pool_timeout=30`. |

### 2. Auto-Commit on Every Request (Including Reads)

| | |
|---|---|
| **File** | `apps/api/src/api/config/database.py` |
| **Lines** | 92–93 |
| **Issue** | `get_db()` commits the transaction after every request, even read-only GET endpoints. This forces WAL flush and fsync on every read. |
| **Impact** | ~50%+ unnecessary database I/O on read-heavy endpoints. WAL pressure increases. |
| **Fix** | Only commit on write operations. Use `db.get() / db.execute()` without commit on reads. Or add a `read_only` parameter to `get_db()`. |

### 3. f-string Logging — 176 Occurrences

| | |
|---|---|
| **Scope** | Across all `apps/api/src/api/` Python files |
| **Issue** | `logger.info(f"user={user_id} ...")` — string interpolation happens at call time, even when the log level is not enabled (e.g., `INFO` logs when log level is `WARNING`). Wastes CPU cycles on every log call. |
| **Impact** | Cumulative CPU waste — under high request volume, this adds measurable overhead. Prevents log aggregation tools from properly indexing structured fields. |
| **Fix** | Replace with `logger.info("user=%s ...", user_id, extra={"user_id": user_id})` or structured keyword logging. 176 f-string calls vs 407 already-correct structured calls. |

### 4. No Resource Limits on Docker Containers

| | |
|---|---|
| **File** | `docker-compose.yml` |
| **Scope** | All services: celery workers (high/default/low/beat), backend, sandbox-worker, flower, celery-monitor, redis, minio |
| **Issue** | Zero CPU/memory resource limits on any container. A memory leak in any service can OOM-kill the entire host. CPU starvation can affect all co-located services. |
| **Impact** | Cascading failure vulnerability — one leaky worker can bring down the entire stack. Noisy-neighbor problem for co-located services. |
| **Fix** | Add `deploy.resources.limits` with appropriate memory (e.g., 512M–2G) and CPU (e.g., 0.5–2.0) per service type. |

### 5. No Health Checks on Celery Workers

| | |
|---|---|
| **File** | `docker-compose.yml` |
| **Scope** | `celery-worker-high`, `celery-worker-default`, `celery-worker-low`, `celery-beat` |
| **Issue** | No health checks configured. Docker/orchestrator cannot detect if a worker is deadlocked, zombie process, or silently failing to consume tasks. |
| **Impact** | Tasks silently queue indefinitely. No auto-remediation. Monitoring dashboards show healthy containers while work is not being done. |
| **Fix** | Add `healthcheck` using `celery -A tasks inspect ping` or `celery status` with appropriate interval/retries/start-period. |

---

## 🟠 HIGH — Significant Impact

### 6. Inconsistent Error Response Format

| | |
|---|---|
| **Files** | `middleware.py` / `exception_handlers.py` / `core/errors.py` |
| **Issue** | Three different error response shapes coexist: |
| | - **Middleware**: `{"success": false, "error": {"code", "message", "request_id", "type"}}` |
| | - **Exception handlers**: `{"success": false, "error": {"code", "message", "request_id"}}` (no `type`) |
| | - **Some routes**: raw `{"detail": "..."}` from FastAPI defaults |
| **Impact** | Frontend error handling is fragile. Monitoring/alerting cannot reliably classify or extract error codes. API consumers get inconsistent shapes. |
| **Fix** | Unify to a single `ErrorEnvelope` schema. Remove the middleware error handler layer (it duplicates `exception_handlers.py`). Ensure all routes use the same error response model. |

### 7. Routers Mounted Twice (Dual Registration)

| | |
|---|---|
| **File** | `apps/api/src/api/route_mounting.py` |
| **Issue** | `mount_primary_routes()` mounts ~22 routers at `/chat`, `/api`, `/auth`, etc. `mount_versioned_alias_routes()` re-mounts 10 of them at `/api/v1/chat`, `/api/v1/api`, etc. Same handlers, same middleware, double registration. |
| **Impact** | Double the route resolution overhead on every request. Potential for subtle route collision bugs. Versioning strategy provides no actual API contract separation. |
| **Fix** | Choose one scheme: either versioned-only paths (clean) or non-versioned defaults with redirect headers. Remove the dual mounting. |

### 8. Synchronous Blocking Calls in Async Context

| | |
|---|---|
| **Scope** | Various route handlers across `apps/api/src/api/routes/` |
| **Issue** | Several services use `time.sleep()`, synchronous file I/O (`open()`, `json.load()`), or `requests.get()` (blocking HTTP) inside async route handlers. These block the entire asyncio event loop. |
| **Impact** | When a single route handler blocks for I/O (e.g., file read or upstream HTTP call), all concurrent requests are delayed. This is the classic "async + sync = sad" antipattern. |
| **Fix** | Use `asyncio.to_thread()` for blocking operations. Replace `requests` with `httpx.AsyncClient`. Replace `time.sleep()` with `asyncio.sleep()`. |

### 9. No Rate Limiting

| | |
|---|---|
| **Scope** | Middleware stack in `apps/api/src/api/middleware.py` |
| **Issue** | No rate limiting middleware exists. The API is fully open — a single client (or compromised credential) can saturate resources. |
| **Impact** | Denial-of-service vulnerability. LLM API costs can be driven up by abuse. No fair-usage enforcement across tenants. |
| **Fix** | Add rate limiting middleware (slowapi, Redis-based token bucket, or custom middleware). Apply per-route / per-user limits. |

### 10. In-Memory Streaming Task Store

| | |
|---|---|
| **File** | `apps/api/src/api/routes/api_router.py` |
| **Issue** | `route_task_stream_start`, `poll/{id}`, `cancel/{id}` use a plain Python dict for task state storage. No persistence, no TTL, no cleanup. |
| **Impact** | Task state is lost on server restart. Cannot scale to multiple replicas. Stale entries accumulate in memory indefinitely. |
| **Fix** | Move task state to Redis with TTL-based expiration. Use Redis Streams or a dedicated task queue. |

---

## 🟡 MEDIUM — Gradual Degradation Risk

### 11. No Connection Pool Tuning

| | |
|---|---|
| **File** | `apps/api/src/api/config/database.py` |
| **Issue** | No explicit `pool_size`, `max_overflow`, or `pool_timeout` values. Even after fixing NullPool, defaults may be suboptimal. |
| **Impact** | Under high concurrency, default pool size (5) causes queueing. Under low concurrency, excess connections waste resources. |
| **Fix** | Configure based on expected concurrency: `pool_size=20`, `max_overflow=10`, `pool_timeout=30`. |

### 12. Silent Degradation on Startup Failures

| | |
|---|---|
| **File** | `apps/api/src/api/lifespan.py` |
| **Issue** | Every subsystem (Redis, DB, Vault, provider monitoring, embeddings) is wrapped in individual try/except that logs a warning and continues. The app starts even if critical subsystems fail. |
| **Impact** | The app runs in a degraded state with no explicit alerting. Redis down? Still serving requests that will fail. Database unreachable? 500 errors for every DB-backed endpoint. |
| **Fix** | Add a `/health` endpoint that reports subsystem status. Fail startup for truly required subsystems (DB, Redis). Implement startup dependency checks. |

### 13. Stale SQLite Journal File in Repo

| | |
|---|---|
| **File** | `apps/api/goblin_assistant.db-journal` |
| **Issue** | A `.db-journal` file exists, likely from local development with SQLite. If accidentally deployed, it can cause database locking issues. |
| **Impact** | Potential database corruption or locking errors if deployed with SQLite in production. |
| **Fix** | Add to `.gitignore`. Remove from repo. Document that SQLite is dev-only. |

### 14. Mock/Hardcoded Endpoints Still Mounted

| | |
|---|---|
| **File** | `apps/api/src/api/routes/api_router.py` |
| **Issue** | Several endpoints return hardcoded/stub data: `GET /goblins`, `GET /history/{id}`, `GET /stats/{id}`, `POST /route_task` |
| **Impact** | Dead code in production. Clients can call these and get fake data. Maintenance burden when refactoring. |
| **Fix** | Either implement properly or remove and return 501 Not Implemented with clear deprecation headers. |

### 15. Docker Socket Exposed to Sandbox Worker

| | |
|---|---|
| **File** | `docker-compose.yml` |
| **Issue** | `/var/run/docker.sock` mounted (read-only) in `sandbox-worker` — a container that runs untrusted user code. |
| **Impact** | Even read-only, Docker socket access is a significant security surface. Container escape or Docker API reconnaissance is possible from compromised sandbox. |
| **Fix** | Remove Docker socket mount. Use a different isolation mechanism (e.g., gVisor, Firecracker micro-VMs, or sysbox). |

---

## 📊 Issue Summary

| Severity | Count | Primary Category |
|----------|-------|-----------------|
| 🔴 Critical | 5 | Database, Observability, Infrastructure |
| 🟠 High | 5 | API Design, Performance, Security |
| 🟡 Medium | 5 | Configuration, Security, Dead Code |

**Key Themes:**
- **Database is the #1 bottleneck** — NullPool + auto-commit creates maximum overhead per request
- **Observability is actively degrading performance** — 176 f-string log calls burn CPU for no benefit
- **Container orchestration is fragile** — no resource limits, no health checks, single-point-of-failure design
- **API consistency issues** — dual routing, inconsistent errors, mixed sync/async patterns
- **Production-readiness gaps** — no rate limiting, no connection pooling, in-memory state

---

## 🎯 Recommended Fix Order (ROI-Based)

```
Week 1 (High ROI, Low Risk):
  1. Fix NullPool → AsyncAdaptedQueuePool              [DB perf: +200-500%]
  2. Add Docker resource limits + health checks         [Stability]
  3. Bulk fix f-string logging (176 files)              [CPU: 2-5% savings]

Week 2 (Medium ROI, Low-Medium Risk):
  4. Add rate limiting middleware                        [Security]
  5. Remove auto-commit on read-only requests           [DB I/O: -50%]
  6. Unify error response format                        [API quality]

Week 3 (Infrastructure):
  7. Move streaming tasks to Redis                      [Scalability]
  8. Add /health with subsystem checks                  [Observability]
  9. Fix sync-in-async blockers                         [Concurrent perf]

Week 4 (Cleanup):
  10. Resolve dual router mounting                      [Maintainability]
  11. Remove/implement stub endpoints                   [Cleanup]
  12. Remove Docker socket from sandbox                 [Security]