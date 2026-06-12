# Service Level Objectives

> Last updated: 2026-06-06
> Owner: Platform / On-call rotation

---

## SLO Inventory

| SLO | Target | Window | Error Budget (min/month) | Alert |
|-----|--------|--------|--------------------------|-------|
| API Availability | 99.9% | 7-day rolling | 43.8 | `APIAvailabilityLow` |
| Chat P95 Latency | < 2 s | 7-day rolling | N/A (latency) | `ChatLatencyHigh` |
| Auth Success Rate | 99.9% | 7-day rolling | 43.8 | `AuthSuccessRateLow` |
| LLM Provider Availability | 99.5% | 7-day rolling | 219 | `LLMProviderAvailabilityLow` |
| Sandbox Availability | 95% | 7-day rolling | 2,190 | `SandboxAvailabilityLow` |
| Sandbox P95 Job Duration | < 120 s | 7-day rolling | N/A (latency) | `SandboxLatencyHigh` |

---

## Error Budget Math

```
monthly_minutes  = 30 × 24 × 60  = 43,800
budget_min       = (1 − target) × 43,800
burn_rate        = actual_error_rate / (1 − target)
```

A burn rate of **1.0** exhausts the monthly budget in exactly 30 days.
A burn rate of **14.4** exhausts it in 50 hours (fast-burn alert threshold).

---

## SLO Details

### API Availability — 99.9%

**Definition:** Fraction of HTTP requests that do not return a 5xx response.

```promql
-- SLI (7-day success rate)
1 - (
  rate(http_requests_total{status=~"5.."}[7d])
  /
  rate(http_requests_total[7d])
)
```

**Error budget:** 43.8 min/month  
**Alert:** `APIAvailabilityLow` (critical) fires when 7-day success rate drops below 99.9%  
**Runbook:** [#api-availability](#api-availability-runbook)

---

### Chat P95 Latency — < 2 s

**Definition:** 95th-percentile end-to-end chat completion latency measured at the backend.

```promql
-- SLI (7-day P95)
histogram_quantile(
  0.95,
  rate(goblin_chat_duration_seconds_bucket[7d])
)
```

**Alert:** `ChatLatencyHigh` (warning) fires when 7-day P95 exceeds 2 s  
**Runbook:** [#chat-latency](#chat-latency-runbook)

---

### Auth Success Rate — 99.9%

**Definition:** Fraction of authentication attempts (login + token refresh) that succeed.

```promql
-- SLI (7-day success rate)
rate(auth_success_total[7d])
/
rate(auth_attempts_total[7d])
```

**Error budget:** 43.8 min/month  
**Alert:** `AuthSuccessRateLow` (critical) fires when 7-day success rate drops below 99.9%  
**Runbook:** [#auth-success-rate](#auth-success-rate-runbook)

---

### LLM Provider Availability — 99.5%

**Definition:** Fraction of LLM provider requests that return a successful (non-error) response across all configured providers, weighted equally.

```promql
-- SLI (7-day success rate, aggregated across providers)
rate(goblin_provider_requests_total{result="success"}[7d])
/
rate(goblin_provider_requests_total[7d])
```

**Error budget:** 219 min/month  
**Alert:** `LLMProviderAvailabilityLow` (warning) fires when 7-day aggregate success rate drops below 99.5%  
**Runbook:** [#llm-provider-availability](#llm-provider-availability-runbook)

---

### Sandbox Availability — 95%

**Definition:** Fraction of sandbox jobs that complete successfully (not failed or timed out).

```promql
-- SLI (7-day success rate)
1 - (
  rate(sandbox_job_failures_total[7d])
  /
  rate(sandbox_jobs_submitted_total[7d])
)
```

**Error budget:** 2,190 min/month  
**Alert:** `SandboxAvailabilityLow` (critical) fires after 1 h sustained breach  
**Runbook:** [#sandbox-availability](#sandbox-availability-runbook)

---

### Sandbox P95 Job Duration — < 120 s

**Definition:** 95th-percentile wall-clock time from job submission to completion.

```promql
-- SLI (7-day P95)
histogram_quantile(
  0.95,
  rate(sandbox_job_duration_seconds_bucket[7d])
)
```

**Alert:** `SandboxLatencyHigh` (warning) fires after 1 h sustained breach  
**Runbook:** [#sandbox-latency](#sandbox-latency-runbook)

---

## Burn Rate Alert Thresholds

Multi-window, multi-burn-rate alerting catches both fast exhaustion (short spike) and slow leaks.

| Severity | Burn Rate | Detection Window | Budget Consumed | Alert Action |
|----------|-----------|-----------------|-----------------|--------------|
| Critical (page) | 14.4× | 1 h | 2% in 1 h | Page on-call immediately |
| Critical (page) | 6× | 6 h | 5% in 6 h | Page on-call immediately |
| Warning (ticket) | 3× | 1 day | 10% in 1 day | Create incident ticket |
| Warning (ticket) | 1× | 3 days | 10% in 3 days | Review in weekly sync |

The Prometheus rules in `prometheus_rules.yml` currently implement single-window SLO breach alerts (simpler). Upgrade to multi-burn-rate alerts when Prometheus recording rules are wired up for all SLIs.

---

## Review Cadence

| Cadence | Activity |
|---------|----------|
| Weekly | Review remaining error budget per SLO; escalate if > 50% consumed |
| Monthly | Full SLO review: adjust targets if consistently over/under; update this doc |
| Quarterly | Audit alert thresholds against real traffic patterns; tune burn rates |

---

## Runbooks

### API Availability Runbook

1. Check `/health` and `/health/all` endpoints for subsystem failures
2. Review recent deploys (`git log --oneline -20`) for correlation
3. Check Render dashboard for backend restarts or OOM kills
4. Check Supabase status page for database connectivity issues
5. If 5xx rate is provider-related (timeouts), shift traffic via `topProvidersFor` config
6. Rollback last deploy if no other cause found

### Chat Latency Runbook

1. Check `histogram_quantile(0.95, rate(goblin_chat_duration_seconds_bucket[5m]))` for real-time P95
2. Identify slow providers: `/api/v1/health/routing` shows per-provider latency history
3. Check Redis health (`/health` → redis subsystem) — high latency often from cache misses
4. Review active model — some models (GPT-4, Claude Opus) have inherently higher latency
5. If provider-specific: temporarily disable the slow provider via admin panel

### Auth Success Rate Runbook

1. Check `/health` for database connectivity — auth failures often DB-related
2. Review Supabase Auth logs for error patterns
3. Check rate limiter (`/api/v1/core/rate-limit`) — excessive 429s inflate failure count
4. Verify CSRF token configuration hasn't changed after a deploy
5. Check for expired or rotated JWT secrets in environment config

### LLM Provider Availability Runbook

1. Check `/api/v1/providers/status` for per-provider health scores and circuit breaker state
2. Identify which providers are failing — check upstream status pages (OpenAI, Anthropic, Groq)
3. If one provider is down, the router automatically deprioritizes it — verify via `topProvidersFor`
4. For persistent failures: disable the provider in `config/providers.toml`, regenerate JSON (`make generate-providers-json`), redeploy
5. Check API key validity — expired keys surface as 401s counted as failures

### Sandbox Availability Runbook

1. Check Docker daemon health on sandbox host
2. Review `sandbox_job_failures_total` by failure reason label
3. Check disk space — full disk causes both job failures and cleanup failures
4. Review `SandboxJobsStuck` alert — stuck jobs block queue processing
5. Restart sandbox worker if queue is backed up with no progress

### Sandbox Latency Runbook

1. Check `SandboxQueueDepthHigh` — high queue depth causes queuing latency
2. Profile container startup time — slow image pulls inflate P95
3. Check `SandboxContainerKillsHigh` — kills indicate resource contention
4. Review job types in queue — expensive jobs (ML workloads) raise P95 for all jobs
5. Scale sandbox workers horizontally if traffic has genuinely grown
