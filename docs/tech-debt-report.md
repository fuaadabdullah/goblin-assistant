# Technical Debt Report: Goblin Assistant

**Generated:** 2026-07-17
**Scope:** Full repository analysis

---

## Executive Summary

This report identifies **6 major categories** of technical debt:
- **Architecture Boundary Violations** (25 issues - HIGH PRIORITY)
- **Capability Boundary Violations** (39 issues - HIGH PRIORITY)
- **Architecture & Code Organization** (5 issues)
- **Security Vulnerabilities** (10 issues)
- **Testing Debt** (3 issues)
- **Operational & Build Debt** (4 issues)

Total estimated remediation effort: **3-4 sprints** for P0-P2 issues.

---

## 1. Architecture Boundary Violations (CRITICAL)

Running `make check-api-boundaries` reveals **25 active violations** that breach the established architecture rules.

### 1.1 Route Direct Storage Imports (21 violations)

Routes/modules directly importing storage modules (violates `route_no_direct_storage` rule):

| File | Violations |
|------|------------|
| `apps/api/src/api/api_router.py` | `api.storage`, `api.storage.tasks` |
| `apps/api/src/api/observability/debug_system_router.py` | `api.storage.usage_events` |
| `apps/api/src/api/routes/account_router.py` | `api.storage.saas_service` |
| `apps/api/src/api/routes/agent.py` | `api.storage.tasks` |
| `apps/api/src/api/routes/api_keys_router.py` | `api.storage.api_keys` |
| `apps/api/src/api/routes/feature_flags_router.py` | `api.storage.database`, `api.storage.saas_service` |
| `apps/api/src/api/routes/notifications_router.py` | `api.storage.database`, `api.storage.saas_service` |
| `apps/api/src/api/routes/orchestration_router.py` | `api.storage.tasks` |
| `apps/api/src/api/routes/privacy.py` | `api.storage.database`, `api.storage.models`, `api.storage.saas_service` |
| `apps/api/src/api/routes/search_router.py` | `api.storage.database` |
| `apps/api/src/api/routes/settings_router.py` | `api.storage.database`, `api.storage.saas_service` |
| `apps/api/src/api/routes/support_router.py` | `api.storage.database`, `api.storage.saas_service`, `api.storage.user_service` |
| `apps/api/src/api/routing/feedback_router.py` | `api.storage.database` |

### 1.2 Service Route Dependencies (4 violations)

Services importing route modules (violates `service_no_route_dependency` rule):

| File | Route Imports |
|------|---------------|
| `apps/api/src/api/services/learning_applicator.py` | `api.routing.ml_router`, `api.routing.feature_router` |
| `apps/api/src/api/services/smart_router.py` | `api.routing.ml_router`, `api.routing.feature_router` |

**Impact:** These directly violate the pure-by-default policy documented in `PURE_FUNCTIONS_AND_NAMING_POLICY.md`. Routes should use service abstractions, not concrete storage implementations.

---

## 2. Capability Boundary Violations (CRITICAL)

Running `make check-capability-boundaries` reveals **39 active violations** that breach capability ownership rules.

### 2.1 Provider Leakage (11 violations)

Concrete provider imports in non-owner modules:

| File | Violations |
|------|------------|
| `apps/api/src/api/providers/google_cloud_provider.py:22` | `api.providers.openai_compatible` |
| `apps/api/src/api/providers/google_cloud_selfhosted_provider.py:30-32` | `api.providers.llamacpp_provider`, `api.providers.ollama_provider`, `api.providers.vertex_provider` |
| `apps/api/src/api/providers/provider_registry.py:11-24` | Multiple concrete provider imports (`aliyun`, `anthropic`, `azure`, `mock`, `ollama`, `openai_compatible`, `openai`, `siliconeflow`) |

### 2.2 Capability Allowed Dependency Violations (27 violations)

| Module | Owning Capability | Forbidden Imports |
|--------|-------------------|-----------------|
| `apps/api/src/api/assistant_tools/executor.py` | sandbox | `api.capabilities.permissions`, `api.capabilities.registry` |
| `apps/api/src/api/chat_router/contextual.py` | chat | `api.departments` |
| `apps/api/src/api/chat_router/messages/router.py` | chat | `api.departments` |
| `apps/api/src/api/chat_router/service_accessors.py` | chat | `api.pipeline.pipeline`, `api.pipeline.tool_selection` |
| `apps/api/src/api/providers/dispatcher_pkg/execution.py` | providers | `api.ops.integrations.jira` |
| `apps/api/src/api/providers/router_service.py` | providers | `api.storage.usage_events`, `api.services.task_routing_audit` |
| `apps/api/src/api/routing/feature_router.py` | orchestration | `api.providers.supabase_events` |
| `apps/api/src/api/routing/learned_department_router.py` | orchestration | `api.providers.supabase_events` |
| `apps/api/src/api/routing/ml_router.py` | orchestration | `api.providers.supabase_events` |
| `apps/api/src/api/routing/router_supabase.py` | orchestration | `api.providers.supabase_events` |
| `apps/api/src/api/routing/selection.py` | orchestration | `api.providers.pricing` |
| `apps/api/src/api/sandbox_api.py` | sandbox | `api.sandbox_config`, `api.sandbox_job_helpers`, `api.sandbox_models` |
| `apps/api/src/api/services/provider_health.py` | providers | `api.ops.integrations.jira` |
| `apps/api/src/api/routing/feedback_router.py` | orchestration | `api.storage.database`, `api.providers.supabase_events` |

### 2.3 Orchestration Forbidden Import (1 violation)

| File | Line | Import | Rule |
|------|------|--------|------|
| `apps/api/src/api/routing/feedback_router.py` | 201 | `api.storage.database` | orchestration_forbidden_import_prefixes |

**Impact:** These violations indicate that the capability ownership boundaries defined in `architecture-capabilities.json` are not being enforced, creating tight coupling between unrelated subsystems.

---

## 3. Architecture & Code Organization Debt

### 3.1 Large Files / Single Responsibility Violations

| File | Lines | Assessment | Recommendation |
|------|-------|------------|----------------|
| `packages/sdk/src/generated/openapi.ts` | 11,655 (was 13,125) | Auto-generated artifact - high complexity | Would require changing the SDK codegen pipeline, not the generated output — needs its own scoped investigation, not attempted here |
| `apps/api/src/api/routing/router.py` | 48 (was 778) | RESOLVED | Now a re-export façade over `registry_store.py`, `policy_engine.py`, `router_registry.py`, `selection.py` |
| `apps/api/src/api/health.py` | 277 (was 777) | RESOLVED | Split into `health_core.py`, `health_checks.py`, `ops_health.py` |
| `apps/api/src/api/observability/debug_router.py` | 744 | ACCEPTABLE | Single `/debug` prefix with cohesive endpoints - monitor only |
| `apps/api/src/api/providers/quota_service.py` | 788 | ACCEPTABLE | Cohesive Redis-backed quota logic - acceptable |

### 3.2 Circular Dependencies (STALE — see below)

From `apps/api/architecture-boundaries.toml`, the following cycles are explicitly ignored:

```toml
[ignore_cycles]
# Secrets subsystem
api.integrations.secrets.auth -> api.integrations.secrets.vault_adapter -> api.integrations.secrets.auth

# Provider monitoring
api.providers.dispatcher -> api.services.provider_health -> api.providers.dispatcher

# Provider → Routing cycle
api.providers.dispatcher -> api.services.provider_health -> api.routing.router -> api.providers.dispatcher

# Memory service cycles
api.services.memory_promotion_service -> api.services.observability_service -> api.services.retrieval_service -> api.services.tool_result_memory_service -> api.services.memory_promotion_service
api.services.memory_promotion_service -> api.services.retrieval_service -> api.services.tool_result_memory_service -> api.services.memory_promotion_service
api.services.retrieval_service -> api.services.tool_result_memory_service -> api.services.retrieval_service

# Storage models
api.storage.models -> api.storage.vector_models -> api.storage.models
```

**`make check-api-cycles` is not wired into any CI pipeline** (not in
`.github/workflows/ci.yml` or `.circleci/config.yml` — it only exists as a
manual `make` target), so this list has drifted from reality undetected.
Running it against the current tree surfaces **9 different, undocumented
cycles** — none of which match the 7 above:

```text
api.observability.alert_handlers -> api.observability.alerting_system -> api.observability.alert_handlers
api.providers.dispatcher -> api.providers.dispatcher_pkg.debug -> api.routing.router -> api.routing.selection -> api.providers.dispatcher
api.providers.dispatcher -> api.providers.model_registry -> api.providers.dispatcher
api.routing.feature_extractor -> api.services.provider_health -> api.routing.router -> api.routing.router_registry -> api.routing.ml_router -> api.routing.feature_router -> api.routing.feature_extractor
api.routing.feature_router -> api.routing.ml_router -> api.routing.feature_router
api.routing.feature_router -> api.routing.router_registry -> api.routing.ml_router -> api.routing.feature_router
api.routing.ml_router -> api.routing.router_strategies -> api.routing.policy_engine -> api.routing.router_registry -> api.routing.ml_router
api.routing.prompt_classifier -> api.services.smart_router -> api.routing.prompt_classifier
api.services.embedding_service -> api.services.embedding_worker -> api.services.embedding_service
```

These predate this remediation pass (confirmed unchanged against the
pre-session commit) and mostly cluster around the `routing/router.py` split
into `policy_engine.py`/`router_registry.py`/`selection.py`/etc. — the
extraction likely introduced cross-module back-references among the split
pieces. **Not fixed here**: breaking these safely requires case-by-case
analysis of import order and likely dependency-inversion/lazy-import work in
live routing/provider-dispatch code, which is real behavioral risk to take on
without dedicated review per cycle. Wiring `check-api-cycles` into CI is a
prerequisite for catching further drift, but doing so today would fail the
build on 9 pre-existing violations — do that only alongside a resolution
plan, not before one.

**Impact:** These create maintenance complexity and hinder module hot-swapping capability.

### 3.3 Frontend Proxy Separation — RESOLVED

`apps/web/src/server/backendProxyRoute.ts` (238 lines, was mixing route
resolution, HTTP forwarding, and helper functions) is now a thin
composition layer over `proxy/routeResolver.ts` (route resolution) and
`proxy/httpForwarder.ts` (HTTP forwarding).

---

## 4. Security Vulnerabilities

### 4.1 Node.js Dependencies — RESOLVED

`pnpm audit` (all severity levels) now reports **no known vulnerabilities**.
Verified each of the 9 originally-flagged advisories individually against
the lockfile:

| Package | Severity | CVE/Source | Resolved To |
|---------|----------|------------|---------------|
| `next` | High | GHSA-9g9p-9gw9-jx7f (DoS Image Optimizer) | 16.2.6 (required ≥15.5.10) |
| `next` | High | GHSA-h25m-26qc-wcjf (HTTP deserialization DoS) | 16.2.6 (required ≥15.5.10) |
| `minimatch` | High | GHSA-3ppc-4f35-3m26, GHSA-7r86-cg39-jmmj, GHSA-23c5-xmqv-rm74 (multiple ReDoS) | 10.2.5 |
| `dompurify` | Moderate | GHSA-v2wj-7wpq-c8vv (XSS) | pnpm override pinned to ^3.3.2 (required ≥3.3.1); no longer resolved as an active transitive dependency |
| `ajv` | Moderate | GHSA-2g4f-4pwh-qvx6 (ReDoS) | 6.15.0 (required ≥6.14.0) |
| `@tootallnate/once` | Low | GHSA-vpq2-c234-7xj6 (control flow) | pnpm override pinned to ^3.0.1; no longer resolved as an active transitive dependency |
| `diff` | Low | GHSA-73rr-hh4g-fpgx (DoS) | 8.0.3 (required ≥4.0.4) |

### 4.2 Python Dependencies — RESOLVED

| Package | Severity | CVE | Status |
|---------|----------|-----|--------|
| `ecdsa` | Moderate | CVE-2024-23342 | **Removed entirely** — was a transitive dependency of `python-jose`, which this remediation pass replaced with `pyjwt` (`apps/api/requirements.txt`). `ecdsa` is absent from `uv.lock` and not installed in the venv. |

---

## 5. Testing Debt

### 5.1 Large Test Files — RESOLVED

All test files originally exceeding 700+ lines have been split into
per-concern packages (one file per test class/area, shared fixtures in
`conftest.py`/`helpers.py`):

| Original Test File | Lines | Split Into |
|-----------|-------|-------|
| `test_context_assembly_coverage.py` | 1,159 | `context_assembly_coverage/` |
| `test_provider_dispatcher_authority.py` | 1,208 | `provider_dispatcher_authority/` |
| `test_chat_router_core.py` | 1,117 | `chat_router_core/` |
| `test_provider_dispatcher_routing.py` | 1,111 | `provider_dispatcher_routing/` |
| `test_sse_errors.py` | 793 | `sse_errors/` |
| `test_sandbox_api_runtime.py` | 708 | `sandbox_api_runtime/` |
| `test_auth_additional_coverage.py` | 699 | `auth_additional_coverage/` |

### 5.2 Already Addressed (Positive Note)

The `REFACTOR_SUMMARY.md` documents successful elimination of **20 loose status code assertions** across 6 test files, replacing them with exact expectations and response body validation.

### 5.3 Dead Code — RESOLVED (with known residual)

`make check-dead-code` (vulture + knip) went from 46 Python findings + 5 unused
files + 3 unused dependencies down to 4 known false positives:

- Investigated every finding individually rather than blindly deleting: most
  were `__exit__`-style dunder parameters, side-effect-only pytest fixtures,
  and mock-signature-matching parameters — all legitimate, added to
  `ignore_names` in `apps/api/pyproject.toml`.
- Two genuinely dead function parameters removed:
  `setup_vault_approle_renewal`/`setup_vault_token_renewal` in
  `integrations/secrets/auth.py` took an unused `vault_client` (the functions
  have zero callers anywhere in the codebase); `delete_user_data` in
  `routes/privacy.py` took an unused `BackgroundTasks` FastAPI dependency.
  Two genuinely dead test parameters removed: `metrics_svc` fixture (created
  a `RetrievalMetricsService` never wired to anything) and `scores_override`
  (never passed by any caller, never read in the body).
  One vestigial always-same-branch ternary simplified in
  `test_failover.py` (`None if False else X` → `X`).
- `results_count` (`retrieval_tracer.RetrievalTracer.end_trace`) and
  `use_cache` (mirrors `load_provider_config`'s real signature) are called
  with these exact keyword arguments by live production code — added to a
  new `apps/api/vulture_whitelist.py` (vulture's own documented
  false-positive mechanism) rather than touched.
- Frontend (`knip`): deleted 5 confirmed-orphaned files (`features/analyst/*`
  — a whole unreferenced feature, `services/runtime-streaming.ts` — a dead
  re-export shim, `theme/theme.d.ts` — stale ambient types superseded by the
  real `theme.ts` implementation) and removed the genuinely-unused
  `framer-motion` dependency. `@goblin/shared`/`@goblin/ui` were also
  flagged but are demonstrably used in real (non-test) source — a knip
  monorepo-resolution false positive, added to `knip.json`'s
  `ignoreDependencies` instead of removed.

**Residual (not fixed):** 4 vulture findings — `unreachable code after
return/raise` and `unsatisfiable if/ternary condition` — in test provider
stubs (`provider_dispatcher_routing/conftest.py`,
`test_candidate_ordering.py`, `test_jira_provider_ops.py`,
`test_stream_router.py`). All 4 are the same intentional idiom: a
`return`/`raise` followed by an unreachable `yield` to make a stub method an
async generator without ever actually yielding. Vulture has no whitelist
mechanism for these two finding categories (only named-variable findings can
be whitelisted), and rewriting the idiom to dodge the heuristic would add
fake complexity purely to satisfy the linter. `make check-dead-code` will
therefore keep exiting non-zero on these 4 until vulture adds a suppression
mechanism for control-flow findings, or the idiom is replaced repo-wide with
something else.

---

## 6. Operational & Build Debt

### 6.1 Docker Security Issues

From `docker-compose.yml`:

| Line | Issue | Risk | Recommendation |
|------|-------|------|----------------|
| 124 | Direct `/var/run/docker.sock:ro` mount removed from sandbox-worker; access now goes through `docker-socket-proxy` | Residual Docker API exposure is bounded to the proxy service | Continue evaluating rootless Docker/gVisor/Firecracker before production sandbox expansion |
| Dockerfile | `COPY . /app` replaced with selective runtime copies | Lower information leakage risk | Keep `.dockerignore` and `check-operational-policy` current |
| Dockerfile | Runtime now uses non-root `appuser` | Lower container escape blast radius | Preserve explicit `USER` directive |
| Compose | Runtime services now use read-only roots plus selective writable mounts/tmpfs | Lower tampering risk | Add new writable mounts only for owned runtime data |

### 6.2 CI/CD Split Complexity

- GitHub Actions: repository guardrails and contract checks
- CircleCI: heavier lint/test/build/deploy work
- Dependabot is configured in `.github/dependabot.yml` for pip, npm, Terraform, and GitHub Actions

**Impact:** Potential for drift between guardrails and enforcement is now
covered by `make check-operational-policy`, which is included in
`make lint-policy`.

### 6.3 Build Process

`render.yaml` is the canonical backend deployment blueprint. `fly.toml` remains
checked in as an explicitly archived reference, and Docker Compose remains the
local orchestration surface.

---

## 7. Detailed Remediation Plan

### Priority 0 (Critical - Immediate Action)

1. **Security Upgrades**
   - [x] Verify `pnpm audit` shows clean results
   - [x] Consider alternative to `ecdsa` or accept risk documentation
   - [x] Restrict Docker socket access in sandbox worker

2. **Architecture Boundary Violations**
   - [x] Create service abstractions for storage modules (database, tasks, saas_service, etc.)
   - [x] Refactor routes to use service layer instead of direct storage imports
   - [x] Extract route functions from services (learning_applicator, smart_router)

3. **Capability Boundary Violations**
   - [ ] Fix provider leakage in `provider_registry.py` - use dispatcher pattern
   - [ ] Update capability ownership in `architecture-capabilities.json` or refactor imports
   - [ ] Add missing allowed dependency prefixes for `supabase_events`, `pricing`

### Priority 1 (High - Next Sprint)

4. **Architecture Refactoring**
   - [x] Extract `RoutingRegistryStore` from `routing/router.py`
   - [ ] Plan circular dependency resolution (start with secrets subsystem)
   - [x] Split frontend proxy into resolver/forwarder modules

5. **Test Organization**
   - [x] Split `test_context_assembly*.py` into domain-focused modules
   - [x] Create shared test fixtures for common setups
   - [x] Move large test files to `tests/` subdirectories by domain

### Priority 2 (Medium - Following Sprint)

6. **Docker Hardening**
   - [x] Multi-stage build with `.dockerignore` optimization
   - [x] Add non-root user (UID 1000)
   - [x] Read-only root filesystem with selective write mounts

7. **Documentation**
   - [x] Run `make generate-docs-coverage` and address gaps (report is a
     config summary, not a real-vs-declared diff — already fresh, no gaps;
     real inventory validation is `make check-docs-inventory`, passing)
   - [x] Update stale ADRs in `docs/decisions/` — marked
     `TECH_DEBT_REDUCTION_PLAN.md` (dated 2026-06-05, predates this report)
     as superseded after verifying most of its findings are resolved or
     were mischaracterized (e.g. the "docker-compose fragmentation" it
     flagged turned out to be two legitimately separate-purpose files, not
     duplication). Added a note to ADR-0004 (sandbox architecture)
     documenting the docker-socket-proxy hardening from this pass. Spot-
     checked router-decomposition and dispatcher-decomposition ADRs against
     current code — both still accurate. `TS_STRICT_VIOLATIONS.md` was
     already correctly marked resolved.
   - [x] Add operational runbooks in `docs/operations/` — added
     `PROVIDER_DISPATCH_INCIDENT_RESPONSE.md` (circuit breaker states,
     routing decisions, provider-leakage import errors) and
     `DEPLOYMENT_ROLLBACK.md` (Render/Vercel rollback, migration edge
     case); updated the existing `SANDBOX_README.md` troubleshooting
     section, which predated the docker-socket-proxy hardening from this
     pass and still told operators to check `/var/run/docker.sock`
     directly.

### Priority 3 (Low - Backlog)

8. **Code Quality**
   - [x] Run `make check-dead-code` and remove dead code (see 5.3)
   - [x] Audit OpenAPI spec size — confirmed 11,655 lines (was 13,125),
     auto-generated from the backend's OpenAPI schema. "Splitting by
     domain" would mean changing the SDK codegen pipeline itself, not the
     generated output — not attempted here; would need its own scoped
     investigation into the generator and all its consumers.
   - [x] Consolidate theme CSS files — turned out to be a non-issue:
     `dark-theme.css` doesn't exist anywhere in the repo, and
     `apps/web/src/index.css` (global styles, imported by `app/layout.tsx`)
     already cleanly `@import`s `apps/web/src/theme/index.css` (design
     tokens) — a normal two-layer stylesheet structure, not duplication.

---

## 8. Verification Commands

Run these to validate current state:

```bash
# Security
pnpm audit --audit-level moderate
make check-unused-deps

# Architecture
make check-api-boundaries
make check-api-cycles
make check-capability-boundaries

# Testing
make check-dead-code
make test-api-coverage
make test-web-coverage

# Contracts
make contract-checks
make sdk-check
```

---

## Appendix: Files Analyzed

- `package.json` (root and apps/web)
- `Makefile`
- `apps/api/pyproject.toml`
- `apps/api/requirements.txt`
- `apps/api/architecture-boundaries.toml`
- `apps/api/architecture-capabilities.json`
- `reports/largest_files_by_loc.txt`
- `reports/security-audit-latest.json`
- `reports/pip-audit-latest.json`
- `REFACTOR_SUMMARY.md`
- `docker-compose.yml`
- `Dockerfile`
- `.github/workflows/ci.yml`
- `docs/architecture/*.md`
- `scripts/policy_guard.py`
- `apps/web/src/server/backendProxyRoute.ts`
