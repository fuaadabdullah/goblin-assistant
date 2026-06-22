# Engine Contracts — Canonical Interface Specification

This document defines the formal contract for each of the six engine pillars: Routing, Memory, Tool Execution, Sandbox, Auth, and Observability. Every implementation, test, and consumer of an engine pillar must respect these contracts.

## Principles

1. **Contract stability** — Public interfaces documented here are versioned. Breaking changes require a new contract version and a migration path.
2. **Composability** — Every pillar publishes typed events that other pillars can subscribe to without direct coupling.
3. **Observability by default** — Every pillar emits lifecycle metrics, logs, and tracing spans.
4. **Failure isolation** — A failure in one pillar must not cascade into unrelated pillars.

---

## 1. Routing Contract

### Purpose

Classify an incoming request into a brain department and dispatch it through the department's configured provider chain with fallback, cost-awareness, and circuit-breaker isolation.

### Entry Point

```
POST /api/v1/routing/route
```

### Input

```json
{
  "department": "coding",
  "payload": {
    "messages": [{"role": "user", "content": "..."}],
    "tools": [...]
  },
  "stream": false
}
```

- `department`: one of `general`, `reasoning`, `coding`, `creative`, `recall`, `tool_use`, `research`
- `payload.messages`: standard chat messages array
- `payload.tools`: tool schemas (optional, only included if the department supports tools)
- `stream`: boolean, requests SSE streaming response

### Output (non-streaming)

```json
{
  "content": "assistant response text",
  "provider_id": "openai",
  "model": "gpt-4o",
  "usage": {
    "input_tokens": 120,
    "output_tokens": 45
  },
  "department": "coding",
  "department_reason": "classified as coding"
}
```

### Output (streaming `text/event-stream`)

```
event: token
data: {"token": "Hello"}

event: token
data: {"token": " world"}

event: done
data: {"provider_id": "openai", "model": "gpt-4o", "usage": {"input_tokens": 120, "output_tokens": 45}}
```

### Guarantees

| Property | Guarantee |
|---|---|
| Fallback | If the primary provider fails (auth, rate-limit, timeout, server error), the router falls through to the next provider in the chain. |
| Circuit breaking | A provider that exceeds the failure threshold is bypassed for a cooldown period. Canary requests periodically test recovery. |
| Budget control | If the hourly spend cap is exceeded, providers are re-ranked by cost. |
| Warmup | Self-hosted providers are prewarmed before being eligible for routing. |
| Privacy | Provider names are not included in error messages returned to the user. |

### Events Emitted

- `routing.department_selected` — department_id, reason, resolved_provider, model
- `routing.provider_invoked` — provider_id, model, latency_ms, success, error_category
- `routing.fallback_triggered` — previous_provider, reason, fallback_provider
- `routing.circuit_opened` — provider_id, failure_count, cooldown_seconds
- `routing.budget_rerank` — previous_order, re-ranked_order, current_spend

### Error Contract

| HTTP Status | Condition |
|---|---|
| 200 | Successful response (or 200 with SSE for streaming) |
| 404 | Department not found |
| 500 | All providers in chain exhausted |

---

## 2. Memory Contract

### Purpose

Assemble relevant context from system instructions, long-term memory, working memory, semantic retrieval, and ephemeral conversation state into a prompt layer, respecting per-layer token budgets.

### Entry Point

```
POST /api/v1/semantic-chat/conversations/{conversation_id}/context?query=...&k=5
```

### Input

```json
{
  "query": "What were we discussing about the deployment?",
  "k": 5,
  "max_age_hours": 168
}
```

### Output (context bundle)

```json
{
  "summaries": [{"content": "...", "tokens": 200, "source": "conversation_abc"}],
  "messages": [{"role": "assistant", "content": "...", "tokens": 150}],
  "ephemeral_messages": [],
  "tasks": [],
  "memory_facts": [{"content": "...", "category": "preference", "confidence": 0.9}],
  "total_tokens": 350,
  "retrieved_at": "2026-06-20T13:00:00Z"
}
```

### Context Assembly Layer Contract

The orchestrator assembles context in this exact order:

1. **System layer** — always included, not token-budgeted
2. **Long-term memory** — from `memory_core_service` (pgvector-backed)
3. **Working memory** — from active conversation state (if `conversation_id` provided)
4. **Semantic retrieval** — from pgvector similarity search across all source types
5. **Ephemeral memory** — from recent conversation history (if history provided)

Each layer after `system` is token-budgeted. If a layer exceeds its budget, it is truncated with a `truncation_warning` entry. If a layer returns `None`, it is skipped gracefully.

### Memory Fact Lifecycle

| Operation | Endpoint | Contract |
|---|---|---|
| Ingest | `POST /api/v1/semantic-chat/users/{user_id}/memory` | Stores fact with content, category, confidence, source_kind, source_id |
| Search | `GET /api/v1/semantic-chat/users/{user_id}/memory/search?query=...` | Returns top-k facts by semantic similarity, optionally filtered by category |
| Promote | Internal (from tool execution) | Tool results meeting the promotion threshold become memory facts |

### Guarantees

| Property | Guarantee |
|---|---|
| Degradation | If semantic retrieval fails, the orchestrator returns minimal context (system only) with `degraded_mode: true` and a reason string. |
| Token safety | No layer exceeds its configured token budget. Hard-stopped layers emit truncation warnings. |
| Freshness | Memory facts older than `MEMORY_RETENTION_DAYS` (default 30) are eligible for eviction. |

### Events Emitted

- `memory.fact_ingested` — fact_id, category, confidence, tokens
- `memory.context_assembled` — layers_included, total_tokens, degraded, truncation_warnings
- `memory.fact_promoted` — tool_result_id, fact_id, category

---

## 3. Tool Execution Contract

### Purpose

Execute assistant tools (skills, functions, data operations) with structured input/output, memory promotion, and safety controls.

### Entry Point

Internal — invoked by the chat message pipeline after provider response.

### Input

```json
{
  "tool_calls": [
    {
      "id": "call_abc123",
      "type": "function",
      "function": {
        "name": "web_search",
        "arguments": {"query": "latest AI research 2026"}
      }
    }
  ],
  "user_id": "user_42",
  "conversation_id": "conv_99"
}
```

### Output

```json
{
  "tool_results": [
    {
      "tool_call_id": "call_abc123",
      "output": {"results": [...], "source_count": 5},
      "error": null
    }
  ],
  "memory_promoted": true,
  "visualization_extracted": false
}
```

### Supported Skills

| Skill | Tool Name | Input | Output | Status |
|---|---|---|---|---|
| Web search | `web_search` | query, max_results, domain_filters | results[], source_count | Present |
| Academic search | `academic_search` | query, max_results | papers[], source_count | Present |
| Research PDF extract | `research_pdf_extract` | path, sections | extracted_text, metadata, references | Present |
| Citation graph | `citation_graph` | paper_id, direction | references[], citations[] | Present |
| Source verification | `verify_sources` | sources[] | verification[], overall_confidence | Present |

### Guarantees

| Property | Guarantee |
|---|---|
| Memory promotion | Tool results that meet the `MEMORY_PROMOTION_THRESHOLD` (default 0.7) are automatically ingested as memory facts. |
| Error isolation | A tool failure does not block other tools in the same call batch. |
| Input sanitization | All tool arguments are sanitized before execution. |
| Timeout | Each tool call has a configurable timeout (default 30s). |

### Events Emitted

- `tool.execution_started` — tool_name, tool_call_id, input_size_bytes
- `tool.execution_completed` — tool_name, tool_call_id, latency_ms, output_size_bytes
- `tool.execution_failed` — tool_name, tool_call_id, error_category, error_message
- `tool.memory_promoted` — tool_call_id, memory_fact_id, confidence

---

## 4. Sandbox Contract

### Purpose

Execute untrusted code in an isolated Docker container with resource limits, artifact management, and security hardening.

### Entry Points

| Operation | Endpoint | Method |
|---|---|---|
| Submit job | `/api/v1/sandbox/run` | POST |
| Get job status | `/api/v1/sandbox/jobs/{job_id}` | GET |
| Get job logs | `/api/v1/sandbox/jobs/{job_id}/logs` | GET |
| List artifacts | `/api/v1/sandbox/jobs/{job_id}/artifacts` | GET |
| Download artifact | `/api/v1/sandbox/jobs/{job_id}/artifacts/{filename}` | GET |
| Cancel job | `/api/v1/sandbox/jobs/{job_id}/cancel` | POST |

### Input (submit)

```json
{
  "language": "python",
  "code": "print('hello')",
  "timeout_seconds": 30,
  "memory_limit_mb": 256
}
```

- `language`: one of `python`, `javascript`, `typescript`, `go`, `ruby`, `rust` (bash is not supported)
- `code`: the source code to execute
- `timeout_seconds`: hard timeout (default 30, max 120)
- `memory_limit_mb`: memory limit (default 256, max 1024)

### Output (submit)

```json
{
  "job_id": "sandbox-job-abc123",
  "status": "queued",
  "language": "python",
  "created_at": "2026-06-20T13:00:00Z"
}
```

### Job Status States

```
queued → running → completed (exit_code=0)
queued → running → completed (exit_code≠0)
queued → running → failed (timeout, container error)
queued → cancelled (user cancelled before execution)
```

### Job Status Response

```json
{
  "job_id": "sandbox-job-abc123",
  "status": "completed",
  "exit_code": 0,
  "created_at": "2026-06-20T13:00:00Z",
  "completed_at": "2026-06-20T13:00:05Z",
  "execution_time_seconds": 4.2
}
```

### Security Hardening

| Control | Implementation |
|---|---|
| Container isolation | Docker with `--rm`, `--network none`, `--cap-drop ALL`, `--security-opt no-new-privileges` |
| Filesystem | Root FS read-only, `/tmp` as tmpfs (64 MB), `/work` as job directory bind mount |
| Seccomp | Optional seccomp profile at `/etc/sandbox/seccomp.json` |
| AppArmor | Optional AppArmor profile `sandbox-runner` |
| Inner timeout | `sandbox_entrypoint.sh` enforces `INNER_TIMEOUT` (default 20s) before kill |
| Artifact TTL | S3 artifacts expire after 7 days |
| API key auth | Endpoints require `X-API-Key` header |

### Events Emitted

- `sandbox.job_submitted` — job_id, language
- `sandbox.job_started` — job_id
- `sandbox.job_completed` — job_id, exit_code, execution_time
- `sandbox.job_failed` — job_id, failure_type, execution_time
- `sandbox.job_cancelled` — job_id
- `sandbox.container_killed` — reason

---

## 5. Auth Contract

### Purpose

Authenticate and authorize users, issue and validate session tokens, manage passkeys, and protect against CSRF.

### Entry Points

| Operation | Endpoint | Method |
|---|---|---|
| Register | `/api/v1/auth/register` | POST |
| Login | `/api/v1/auth/login` | POST |
| Logout | `/api/v1/auth/logout` | POST |
| Validate token | `/api/v1/auth/validate` | GET |
| Google OAuth URL | `/api/v1/auth/google/url` | GET |
| Google OAuth callback | `/api/v1/auth/google/callback` | GET |
| Passkey challenge | `/api/v1/auth/passkey/challenge` | POST |
| Passkey register | `/api/v1/auth/passkey/register` | POST |
| Passkey auth | `/api/v1/auth/passkey/auth` | POST |
| CSRF token | `/api/v1/auth/csrf/token` | GET |

### Auth Flow

1. User registers or logs in via email/password, Google OAuth, or passkey.
2. Server returns a JWT token and sets an HTTP-only cookie.
3. All subsequent requests include the token in the `Authorization` header or cookie.
4. The middleware validates the token on every request (excluding public paths).
5. On logout, the token is invalidated server-side.

### Token Specification

| Field | Description |
|---|---|
| `sub` | user ID |
| `email` | user email |
| `exp` | expiration timestamp (default 24h from issuance) |
| `iat` | issued at timestamp |
| `type` | `"access"` |

### Security Controls

| Control | Implementation |
|---|---|
| Password hashing | bcrypt (via passlib) |
| CSRF | One-time CSRF tokens for state-changing operations. In-memory fallback when Redis unavailable. |
| Rate limiting | 10 attempts/min per IP for login, 10 attempts/min per IP for registration |
| CORS | Allowed origins configurable per environment. Production restricts to deploy domain. |
| Security headers | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Strict-Transport-Security`, `Content-Security-Policy` |

### Events Emitted

- `auth.user_registered` — user_id, method (email/google/passkey)
- `auth.user_logged_in` — user_id, method
- `auth.user_logged_out` — user_id
- `auth.token_validated` — user_id, valid, reason (if invalid)
- `auth.csrf_issued` — user_id, expiry
- `auth.rate_limit_hit` — identifier, endpoint, window

### Error Contract

| HTTP Status | Error Code | Condition |
|---|---|---|
| 401 | `INVALID_CREDENTIALS` | Wrong email or password |
| 401 | `TOKEN_EXPIRED` | JWT has expired |
| 401 | `INVALID_TOKEN` | JWT malformed or invalid signature |
| 401 | `INVALID_CSRF` | CSRF token missing, expired, or invalid |
| 409 | `EMAIL_EXISTS` | Registration with existing email |
| 429 | `RATE_LIMITED` | Too many requests |

---

## 6. Observability Contract

### Purpose

Expose health status, performance metrics, cost tracking, and diagnostic information for the entire system.

### Entry Points

| Operation | Endpoint | Method |
|---|---|---|
| Health summary | `/api/v1/health` | GET |
| Health all | `/api/v1/health/all` | GET |
| Readiness | `/api/v1/health/ready` | GET |
| Liveness | `/api/v1/health/live` | GET |
| Component health | `/api/v1/health/{component}` | GET |
| Ops snapshot | `/api/v1/ops/snapshot` | GET |
| Debug info | `/api/v1/debug` | GET (ops-auth) |
| Provider debug | `/api/v1/debug/providers` | GET (ops-auth) |
| Metrics | `/api/v1/metrics` | GET |
| Cost tracking | `/api/v1/health/cost-tracking` | GET |

### Health Response Shape

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "components": {
    "api": {"status": "healthy", "latency_ms": 5},
    "database": {"status": "healthy", "latency_ms": 3},
    "redis": {"status": "healthy", "latency_ms": 1},
    "providers": {
      "status": "degraded",
      "details": {
        "configured": 10,
        "healthy": 8,
        "unhealthy": ["provider_x"]
      }
    },
    "routing": {"status": "healthy", "departments": 7},
    "sandbox": {"status": "healthy", "queued_jobs": 0}
  },
  "timestamp": "2026-06-20T13:00:00Z"
}
```

### Metrics Exposed

| Metric | Type | Description |
|---|---|---|
| `requests_total` | Counter | Total API requests by endpoint, method, status |
| `request_duration_seconds` | Histogram | Request latency by endpoint |
| `provider_invocation_total` | Counter | Provider calls by provider_id, model, success/failure |
| `provider_latency_seconds` | Histogram | Provider response latency by provider_id |
| `provider_cost_total` | Counter | Accumulated cost by provider_id (USD) |
| `routing_fallbacks_total` | Counter | Fallback events by department and reason |
| `circuit_breaker_state` | Gauge | 0=closed, 1=open by provider_id |
| `sandbox_jobs_total` | Counter | Jobs by status (queued, running, completed, failed) |
| `sandbox_queue_depth` | Gauge | Current number of queued jobs |
| `memory_facts_total` | Counter | Memory facts ingested by category |
| `memory_retrieval_latency_seconds` | Histogram | Context assembly retrieval latency |
| `auth_login_attempts_total` | Counter | Login attempts by method, success/failure |

### Alert Rules

| Alert | Condition | Severity |
|---|---|---|
| `HighErrorRate` | Error rate > 5% over 5m | critical |
| `ProviderDegraded` | Any provider unavailable > 2m | warning |
| `SandboxQueueBacklog` | Queue depth > 20 for > 1m | warning |
| `HighLatency` | p99 latency > 5s for > 5m | critical |
| `CircuitBreakerOpen` | Circuit open for any provider > 5m | warning |
| `BudgetExceeded` | Hourly spend > 90% of cap | warning |

### Events Emitted

- `observability.health_check_completed` — status, component_count, healthy_count
- `observability.metrics_collected` — metric_count, sink (prometheus/datadog)
- `observability.cost_snapshot` — period, total_spend, provider_breakdown

---

## Cross-Pillar Event Bus

Pillars communicate through typed domain events. Each event has:

```json
{
  "event_type": "routing.department_selected",
  "event_version": "1.0",
  "id": "evt_abc123",
  "timestamp": "2026-06-20T13:00:00Z",
  "source": "routing_router",
  "payload": { "...": "..." },
  "metadata": {
    "trace_id": "trace_xyz",
    "user_id": "user_42"
  }
}
```

### Event Taxonomy

| Domain | Events |
|---|---|
| `routing.*` | department_selected, provider_invoked, fallback_triggered, circuit_opened, budget_rerank |
| `memory.*` | fact_ingested, context_assembled, fact_promoted |
| `tool.*` | execution_started, execution_completed, execution_failed, memory_promoted |
| `sandbox.*` | job_submitted, job_started, job_completed, job_failed, job_cancelled, container_killed |
| `auth.*` | user_registered, user_logged_in, user_logged_out, token_validated, csrf_issued, rate_limit_hit |
| `observability.*` | health_check_completed, metrics_collected, cost_snapshot |

---

## Versioning and Migration

This document is versioned using Git tags. Breaking changes to a pillar contract require:

1. A new version of the pillar interface (e.g., `RoutingContract v2.0`)
2. A migration guide in `docs/operations/CONTRACT_MIGRATION_GUIDE.md`
3. A deprecation window where both v1 and v2 are served simultaneously (minimum one release cycle)
4. Removal of the deprecated contract after two release cycles

---

## Verification

Every contract in this document must be verified by:

1. **Contract tests** in `tests/contract/` that assert the input/output shape
2. **Integration tests** in `tests/integration/engine/` that exercise the full lifecycle
3. **Performance benchmarks** in `tests/performance/engine_benchmarks.py` for latency and throughput