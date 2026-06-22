# Observability — Engine Pillar

## Purpose

The Observability pillar provides health status, performance metrics, cost tracking, and diagnostic information for the entire system. It enables operators to detect degradation, diagnose failures, track costs, and measure performance across all other pillars.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Observability Surface                      │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ Health Checks │  │    Metrics   │  │       Debug       │  │
│  │  /api/v1/    │  │  Prometheus  │  │  /api/v1/debug/* │  │
│  │  health/*    │  │  + Datadog   │  │  (ops-auth)       │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬──────────┘  │
└─────────┼─────────────────┼───────────────────┼──────────────┘
          │                 │                   │
          ▼                 ▼                   ▼
┌─────────────────────────────────────────────────────────────┐
│                    Instrumentation Layer                      │
│                                                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │ Provider    │ │ Health Core │ │ Cost        │           │
│  │ Monitor     │ │ (routing,   │ │ Tracking    │           │
│  │ (async      │ │  db, redis, │ │ Probes      │           │
│  │  monitoring │ │  api)       │ │             │           │
│  │  loop)      │ └─────────────┘ └─────────────┘           │
│  └──────┬──────┘                                           │
│         │                                                    │
│         ▼                                                    │
│  ┌────────────────────────────────────┐                     │
│  │         Collector Layer            │                     │
│  │  • Prometheus metrics endpoints    │                     │
│  │  • Datadog agent integration       │                     │
│  │  • structlog structured logging    │                     │
│  │  • Domain event emission           │                     │
│  └────────────────────────────────────┘                     │
└─────────────────────────────────────────────────────────────┘
          │                 │                   │
          ▼                 ▼                   ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────────────┐
│  Prometheus  │   │   Datadog   │   │   Log Aggregation   │
│  + Alert     │   │  Dashboards │   │   (stdout + file)   │
│  Manager     │   │  + SLOs     │   │                     │
└─────────────┘   └─────────────┘   └─────────────────────┘
```

---

## Core Components

### 1. Health Check Endpoints

The system exposes a hierarchical health check surface:

| Endpoint | Purpose | Caching |
|---|---|---|
| `GET /api/v1/health` | Summary health status of all components | Provider status cached (30s), others live |
| `GET /api/v1/health/all` | Detailed health of all components | Same as above |
| `GET /api/v1/health/ready` | Kubernetes-style readiness probe | Live |
| `GET /api/v1/health/live` | Kubernetes-style liveness probe | Live |
| `GET /api/v1/health/{component}` | Specific component health | Varies by component |

**Health response shape**:
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

**Component health checks** (`health_core.py`):

| Component | Check | Latency Target | Critical? |
|---|---|---|---|
| API | Basic endpoint response | < 100ms | Yes |
| Database | pgvector-capable Postgres query | < 50ms | Yes |
| Redis | PING command | < 10ms | Yes |
| Providers | Per-provider health via adapter | < 5s aggregate | No (degraded) |
| Routing | Department registry loaded | < 10ms | Yes |
| Sandbox | Redis + RQ available | < 10ms | No |
| Chroma | ChromaDB connectivity | < 1s | No |
| MCP | MCP server connectivity | < 1s | No |
| Raptor | Raptor process status | < 1s | No |
| Cost tracking | SQLite/Postgres probe | < 1s | No |

### 2. Provider Monitor (`monitoring.py`)

An async background loop that continuously checks provider health:

- **Interval**: Configurable (default 60s)
- **Checks**: Each provider is probed via its adapter's health check
- **State**: Results are cached and exposed through health endpoints
- **Actions**: Unhealthy providers are flagged; circuit breaker may open on repeated failure
- **Logging**: Each check result is logged with provider_id, latency, and status

```python
class ProviderMonitor:
    async def start(self):     # Start the monitoring loop
    async def stop(self):      # Stop the monitoring loop
    async def get_status(self): # Return current cached provider status
```

### 3. Metrics Collection

#### Prometheus Metrics

Exposed at `GET /api/v1/metrics` with the following metric categories:

**HTTP-level metrics** (via middleware):

| Metric | Type | Labels |
|---|---|---|
| `http_requests_total` | Counter | endpoint, method, status |
| `http_request_duration_seconds` | Histogram | endpoint, method |
| `http_requests_in_flight` | Gauge | endpoint |

**Provider-level metrics** (from dispatcher):

| Metric | Type | Labels |
|---|---|---|
| `provider_invocations_total` | Counter | provider_id, model, success |
| `provider_invocation_duration_seconds` | Histogram | provider_id, model |
| `provider_cost_usd_total` | Counter | provider_id, model |
| `provider_circuit_breaker_state` | Gauge | provider_id (0=closed, 1=open) |
| `provider_circuit_breaker_trips_total` | Counter | provider_id |

**Routing-level metrics**:

| Metric | Type | Labels |
|---|---|---|
| `routing_fallbacks_total` | Counter | department, reason |
| `routing_department_selections_total` | Counter | department |
| `routing_model_alias_resolutions_total` | Counter | alias |

**Sandbox-level metrics**:

| Metric | Type | Labels |
|---|---|---|
| `sandbox_jobs_submitted_total` | Counter | language |
| `sandbox_jobs_completed_total` | Counter | exit_code |
| `sandbox_jobs_failed_total` | Counter | failure_type |
| `sandbox_jobs_cancelled_total` | Counter | — |
| `sandbox_queue_depth` | Gauge | — |

**Memory-level metrics**:

| Metric | Type | Labels |
|---|---|---|
| `memory_facts_ingested_total` | Counter | category |
| `memory_context_assemblies_total` | Counter | degraded |
| `memory_retrieval_duration_seconds` | Histogram | source_type |

**Auth-level metrics**:

| Metric | Type | Labels |
|---|---|---|
| `auth_login_attempts_total` | Counter | method, success |
| `auth_registrations_total` | Counter | method |
| `auth_token_validations_total` | Counter | valid |
| `auth_csrf_tokens_issued_total` | Counter | — |
| `auth_rate_limits_hit_total` | Counter | endpoint |

#### Datadog Integration

Configured via `init_ddtrace()` in `app_factory.py`:
- **APM tracing**: Automatic trace collection for FastAPI requests
- **Custom metrics**: Provider, routing, and sandbox metrics forwarded via DogStatsD
- **Log correlation**: Trace IDs injected into log records

Configuration: `DD_SERVICE=goblin-assistant`, `DD_ENV={environment}`

### 4. Cost Tracking

Cost tracking probes check the ability to record and query per-provider, per-request costs:

- **SQLite probe**: Validates local cost tracking file is writable and queryable
- **Postgres probe**: Validates cost tracking table exists and is writable
- **Fallback**: If neither is available, cost tracking is reported as `unavailable`

Cost data structure:
```json
{
  "provider_id": "openai",
  "model": "gpt-4o",
  "input_tokens": 150,
  "output_tokens": 50,
  "input_cost_usd": 0.00075,
  "output_cost_usd": 0.0015,
  "total_cost_usd": 0.00225,
  "request_id": "req_abc123",
  "user_id": "user_42",
  "timestamp": "2026-06-20T13:00:00Z"
}
```

### 5. Debug Endpoints

Available under `GET /api/v1/debug/*` — require ops-level authentication:

| Endpoint | Purpose |
|---|---|
| `/api/v1/debug` | Full system debug snapshot |
| `/api/v1/debug/providers` | Provider inventory with config (secrets redacted) |
| `/api/v1/debug/routing` | Routing diagnostics, alias maps, circuit states |
| `/api/v1/debug/migration-metrics` | API migration/compatibility counters |

### 6. Structured Logging

All services use `structlog` for structured JSON logging:

```json
{
  "event": "routing.department_selected",
  "logger": "api.routing_router",
  "level": "info",
  "timestamp": "2026-06-20T13:00:00Z",
  "department": "coding",
  "resolved_provider": "anthropic",
  "resolved_model": "claude-sonnet-4-20250514",
  "trace_id": "trace_xyz",
  "user_id": "user_42",
  "request_id": "req_abc123"
}
```

Key log enrichment:
- `trace_id`: Correlated across services (from Datadog APM)
- `user_id`: Authenticated user (when available)
- `request_id`: Per-request correlation ID
- Secrets are redacted from logs via `sanitize_error_message()`

---

## Alert Rules

| Alert Name | Condition | For | Severity | Action |
|---|---|---|---|---|
| `HighErrorRate` | `http_requests_total{status=~"5.."} / http_requests_total > 0.05` | 5m | critical | Pager |
| `HighLatency` | `http_request_duration_seconds{p99} > 5.0` | 5m | critical | Pager |
| `ProviderDegraded` | `provider_circuit_breaker_state == 1` | 2m | warning | Slack |
| `SandboxQueueBacklog` | `sandbox_queue_depth > 20` | 1m | warning | Slack |
| `CircuitBreakerOpen` | `provider_circuit_breaker_state == 1` | 5m | warning | Slack |
| `BudgetExceeded` | `provider_cost_usd_total{provider_id} hourly rate > 90% of cap` | 1m | warning | Slack |
| `AuthErrorRate` | `auth_login_attempts_total{success=false} rate > 10/min` | 1m | warning | Slack |
| `MemoryRetrievalSlow` | `memory_retrieval_duration_seconds{p99} > 2.0` | 5m | warning | Slack |

---

## Ops Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/v1/ops/snapshot` | Full system state snapshot (providers, routing, memory, sandbox) |
| `GET /api/v1/ops/providers-status` | Provider health summary (ops view) |
| `GET /api/v1/admin/providers/state` | Provider state snapshot (ops-only, hidden from OpenAPI) |

---

## Key Configuration

```python
# From environment
ENVIRONMENT = "development"  # development, staging, production
DD_SERVICE = "goblin-assistant"
DD_ENV = ENVIRONMENT
PROMETHEUS_MULTIPROC_DIR = "/tmp/prometheus-metrics"
MONITORING_INTERVAL_SECONDS = 60  # Provider monitor loop interval
HEALTH_CACHE_TTL_SECONDS = 30     # Provider status cache TTL
COST_TRACKING_ENABLED = True      # Enable/disable cost tracking
COST_TRACKING_DSN = "sqlite:///data/costs.db"  # SQLite or Postgres DSN
```

---

## SLO Targets

| SLO | Target | Measurement | Window |
|---|---|---|---|
| API availability | 99.9% | Health endpoint success | 30d |
| Routing decision latency | p99 < 200ms | Provider dispatch time | 7d |
| Provider fallback success | > 99% | Fallback → successful response | 7d |
| Context assembly latency | p99 < 500ms | Full assembly time | 7d |
| Sandbox job completion | > 95% | Submitted → completed (non-timeout) | 7d |
| Auth login success | > 98% | Login attempts → success | 7d |
| Cost tracking accuracy | > 99.9% | Recorded cost vs actual spend | 30d |

---

## Failure Mode Matrix

| Failure | Detection | Impact | Recovery |
|---|---|---|---|
| Provider monitoring loop crash | Missing metrics, stale health | Outdated provider status | Restart loop (auto on next check interval) |
| Prometheus endpoint unavailable | 503 from `/metrics` | No metric collection | Check process, restart collector |
| Datadog agent disconnect | Missing traces, no custom metrics | No APM data | Restart Datadog agent, check API key |
| Cost tracking DB unavailable | Health check failure | Cost not recorded | Fail open (no-cost mode), alert operator |
| Health endpoint slow | p99 > 1s | Degraded health checks | Investigate component with highest latency |
| Log volume spike | Disk pressure, log rate limits | Logs may be dropped | Adjust log level, increase disk, rotate aggressively |

---

## Testing Guidance

### Unit Tests
- `tests/contract/test_observability_contract.py`: Assert health response shape
- `apps/api/src/api/tests/test_health_endpoints.py`: Health endpoint behavior
- `apps/api/src/api/tests/test_cost_tracking_probe.py`: Cost tracking probe behavior

### Integration Tests
- `tests/integration/engine/test_observability_full_health.py`: All components report correct status
- `tests/integration/engine/test_observability_metrics.py`: Metrics endpoint returns valid Prometheus format
- `tests/integration/engine/test_observability_cost_tracking.py`: Submit request, verify cost recorded

### Performance Tests
- `tests/performance/test_observability_overhead.py`: Measure health endpoint overhead (target < 10ms additional latency)

---

## Related Documents

- `ENGINE_CONTRACTS.md` — Canonical interface contract for this pillar
- `prometheus_rules.yml` — Alert rule definitions
- `static-analysis.datadog.yml` — Datadog configuration
- `datadog/DATADOG_SLOS.md` — SLO definitions and dashboard references
- `apps/api/src/api/health.py` — Health router
- `apps/api/src/api/health_core.py` — Core health check functions
- `apps/api/src/api/monitoring.py` — Provider monitoring loop
- `apps/api/src/api/ops_router.py` — Ops endpoints
- `apps/api/src/api/observability/` — Observability sub-package (debug, metrics)