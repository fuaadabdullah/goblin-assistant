# Tech Debt Reduction Plan

> Generated: 2026-06-05
> Based on comprehensive codebase analysis across architecture, code quality, and infrastructure dimensions.

---

## Priority Matrix

| Priority | Area | Effort | Impact |
|----------|------|--------|--------|
| P0 | Security & secrets | Low | Critical |
| P0 | Type safety (any) | Medium | High |
| P1 | API contract consistency | Medium | High |
| P1 | Next.js Pages → App Router | Large | High |
| P2 | Dead/commented code cleanup | Low | Medium |
| P2 | CI/CD pipeline re-enablement | Medium | High |
| P2 | Duplicate API routes (dual-mount) | Small | Medium |
| P2 | Dependency consolidation | Medium | Medium |
| P3 | Config file deduplication | Small | Low |
| P3 | Doc/architecture alignment | Medium | Medium |
| P3 | Test coverage gaps | Large | High |

---

## 1. ARCHITECTURE & API CONTRACTS

### 1.1 Duplicate API Route Mounting (HIGH)
**Files:** `apps/api/src/api/route_mounting.py` (lines 75–134)
**Issue:** Both unversioned (`/api`) and versioned (`/api/v1`) prefixes are mounted for all 20 routers, creating two parallel route sets. This doubles maintenance surface and allows drift between the two sets.
**Action:** Pick one prefix (recommended: `/api/v1`). Remove the unversioned mount or make it a 301 redirect.
**Effort:** Small (1–2 hours)

### 1.2 Frontend Hardcodes `/api/v1` Paths (MEDIUM)
**Files:**
- `apps/web/src/features/chat/api/index.ts:265` — hardcoded `/api/v1/chat/stream`
- `apps/web/src/lib/__tests__/api.test.ts` — multiple v1 paths
- `apps/web/src/__tests__/pages/api/models.test.ts` — fallback tests
**Issue:** Paths are hardcoded strings rather than using a shared contract constant.
**Action:** Extract all API path constants into `packages/shared/src/api/paths.ts` and import across frontend.
**Effort:** Medium (2–3 hours)

### 1.3 Frontend Proxy Routes Duplicate Backend Logic (MEDIUM)
**Files:** `apps/web/pages/api/` — 13 Next.js API proxy routes
**Issue:** Each proxy route manually forwards requests. Any backend route change requires updating the proxy.
**Action:** Consolidate into a single catch-all proxy route at `pages/api/[...path].ts`. Review each existing proxy for unique middleware concerns, then consolidate.
**Effort:** Medium (3–4 hours)

### 1.4 Arch Doc Claims `/v1` Not Mounted — Stale (LOW)
**File:** `docs/architecture/ARCHITECTURE_OVERVIEW.md` (lines 83–92)
**Action:** Update doc to reflect current state (v1 IS mounted). Consider auto-generating route docs from FastAPI OpenAPI schema.
**Effort:** Small (30 min)

---

## 2. TYPE SAFETY & CODE QUALITY

### 2.1 Excessive `as any` Casts (HIGH)
**Finding:** 30+ `as any` casts across the frontend codebase. Worst offenders:

| File | Count | Severity |
|------|-------|----------|
| `apps/web/src/components/ui/Select.tsx` | 12 | HIGH — entire Radix primitive layer untyped |
| `apps/web/src/components/auth/PasskeyPanel.tsx` | 6 | HIGH — WebAuthn API uses `any` for credential types |
| `apps/web/src/utils/monitoring.ts` | 3 | MEDIUM — Sentry SDK shim |
| `apps/web/src/utils/api-notifications.ts` | 2 | LOW |
| `apps/web/src/lib/api/shared.ts` | 2 | LOW |
| `apps/web/src/lib/api/chat.ts` | 1 | LOW |

**Action:**
- **Select.tsx:** Upgrade `@radix-ui/react-select` (newer versions export proper types). Replace `any` aliases with `typeof SelectPrimitive.Trigger`, etc.
- **PasskeyPanel.tsx:** Create `packages/types/src/webauthn.ts` with proper `PublicKeyCredential` wrapper types. Leverage TypeScript 5.5+ lib for WebAuthn types.
- **monitoring.ts:** Type the `Sentry as any` shim using `@sentry/types` package.
**Effort:** Medium (4–6 hours)

### 2.2 Missing Error Typing in Error Boundaries (MEDIUM)
**File:** `apps/web/src/utils/monitoring.ts` — catches `unknown` errors but casts to `any`
**File:** `apps/web/src/components/auth/PasskeyPanel.tsx` — catch blocks typed as `e: any`
**Action:** Use `unknown` + type narrowing pattern consistently. Create shared error normalization utility.
**Effort:** Small (1–2 hours)

### 2.3 Weakly Typed Configuration & Constants (MEDIUM)
**Files:** Various files with inline string literals for model names, provider IDs, route paths
**Issue:** No shared enum/constant file for provider IDs, model names, route prefixes — leading to typo-prone stringly-typed code.
**Action:** Create `packages/shared/src/constants/providers.ts`, `packages/shared/src/constants/models.ts`, and `packages/shared/src/constants/routes.ts`. Migrate all hardcoded strings.
**Effort:** Medium (3–4 hours)

---

## 3. NEXT.JS PAGES ROUTER → APP ROUTER MIGRATION (HIGH)

### 3.1 Current State
**Files to migrate:** 17 page files in `apps/web/src/pages/`
- `pages/index.tsx` — Landing page (layout + hero)
- `pages/chat/` — 10 route files (conversation listing, individual chat, streaming)
- `pages/auth/` — 2 files (sign-in, sign-up)
- `pages/api/` — 13 proxy routes

### 3.2 Migration Steps
1. Create `src/app/layout.tsx` with root layout
2. Migrate `pages/index.tsx` → `app/page.tsx` (simplest — pure presentational)
3. Migrate chat routes using App Router's `loading.tsx` and `error.tsx` conventions
4. Consolidate `pages/api/` → single `app/api/[...path]/route.ts`
5. Remove `middleware.ts` in favor of App Router middleware at `src/middleware.ts`

**Effort:** Large (2–4 weeks incremental). High value for long-term maintainability (streaming SSR, React Server Components, simpler data fetching).
**Recommendation:** Do incrementally. Start with landing page and API proxy consolidation.

---

## 4. CI/CD & AUTOMATION

### 4.1 CI Pipeline Largely Commented Out (CRITICAL)
**File:** `.github/workflows/ci.yml` (lines 9–14 and throughout)
**Issue:** The entire CI pipeline appears to be disabled/overwritten with placeholder steps. Tests, lint, type-check, build, and deploy steps are either commented out or stripped down to `echo` commands.
**Action:** Restore CI pipeline. Implement at minimum: lint → type-check → unit tests → build. Add integration tests as separate workflow.
**Effort:** Medium (4–6 hours)

### 4.2 No Pre-commit Hooks Configured (MEDIUM)
**File:** `.husky/` — checked for existence, appears minimal or missing
**Issue:** No husky hooks enforce lint/type-check before commits, allowing debt to accumulate.
**Action:** Configure husky with pre-commit hooks: `lint-staged` for TS/TSX, `prettier --check`, and type-check for changed files.
**Effort:** Small (1 hour)

### 4.3 Manual Heavyweight Scripts (MEDIUM)
**Issues:**
- `scripts/cleanup_backend.py` exists but is manual — should be automated in CI or cron
- `scripts/run-full-deployment-setup.sh` (197 lines) — manual orchestration that should be in CI/CD or a Makefile target
- `scripts/check-e2e-budget.sh` — should auto-fail CI if e2e budget exceeded
- `scripts/run-test-bucket.py` — test parallelism script that should be a Makefile target
**Action:** Move orchestration logic from shell scripts into Makefile or CI pipeline. Delete scripts that have been superseded.
**Effort:** Medium (3–4 hours)

### 4.4 Multiple Dependabot Branches (LOW)Duplicate Dependency Management (MEDIUM)
**Issue:**
- `apps/web/package.json` AND `apps/web/package-lock.json` (npm lock) coexist with root `pnpm-lock.yaml` — lock file drift risk
- Root `pnpm-workspace.yaml` defines 5 workspaces but `apps/web/package-lock.json` suggests npm was used at some point
**Action:** Delete `apps/web/package-lock.json`. Ensure all installs go through `pnpm install` at root. Add `.npmrc` with `save-exact=true` for consistency.
**Effort:** Small (30 min)

### 5.2 API vs Web Dependency Version Drift (LOW)
**Issue:** Python backend and TypeScript frontend evolve independently. No shared version manifest for compatible API/client releases.
**Action:** Introduce a version manifest at root (`VERSION`) and wire into both API (`get_version()` route) and web build (`NEXT_PUBLIC_APP_VERSION`). Use in health check responses.
**Effort:** Small (1–2 hours)

### 5.3 Security Vulnerabilities (MEDIUM)
**File:** `reports/security-audit.json`, `reports/pip-audit-latest.json`, `reports/security-audit.html`
**Issue:** Security audit reports exist suggesting past scans, but no automated tool to prevent regressions.
**Action:** Add `npm audit` / `pnpm audit` and `pip-audit` to CI pipeline with fail threshold (e.g., fail on critical/high). Schedule weekly automated scans.
**Effort:** Small (2–3 hours)

### 5.4 Potential Unused/Stale Dependencies (MEDIUM)
**Issue:** Requirements file at 85 lines — likely some are transitive or unused. No tool like `pipdeptree` or `depcheck` has been run.
**Action:** Run `pipdeptree --warn fail` to audit unused transitive deps. Run `npx depcheck` on web workspace. Remove unused deps.
**Effort:** Small (1–2 hours)
**Observation:** 6+ open dependabot branches covering GitHub Actions, npm, pip, terraform — many unmerged for some time.
**Action:** Audit, merge, or close stale dependabot PRs. Consider weekly automated merge schedule for patch/minor deps.
**Effort:** Small (1–2 hours)

---

## 5. DEPENDENCIES & PACKAGE MANAGEMENT

### 5.1 

---

## 6. INFRASTRUCTURE & CONFIGURATION

### 6.1 Docker Compose Configuration Fragmentation (MEDIUM)
**Files:**
- `docker-compose.yml` (main)
- `docker-compose.goblinos-override.yml`
- `docker-compose.redis.yml`
- `infra/docker-compose.yml` (separate directory)
**Issue:** 4 compose files across 2 directories creates confusion about which is the "source of truth." Override patterns and env var defaults may drift.
**Action:** Consolidate into single `docker-compose.yml` with profiles (`--profile redis`, `--profile goblinos`). Remove `infra/docker-compose.yml` or make it reference the root file.
**Effort:** Medium (3–4 hours)

### 6.2 Deployment Config Fragmentation (MEDIUM)
**Files:** `render.yaml` (Render), `fly.toml` (Fly.io), multiple deployment scripts
**Issue:** At least 2 deployment platforms configured. Increases cognitive load and risk of config drift.
**Action:** Pick one primary platform. Document the decision in ADR. Remove/archive config for the unused platform.
**Effort:** Medium depends on org decision

### 6.3 Dockerfile Quality (LOW)
**File:** `Dockerfile`, `Dockerfile.sandbox`
**Issue:** Multi-stage builds may be missing layer caching optimization. Sandbox Dockerfile is separate — consider merging.
**Action:** Audit for layer ordering (copy package files before source code for cache efficiency). Consider a single Dockerfile with targets.
**Effort:** Small (1–2 hours)

### 6.4 Duplicate Redis Config (LOW)
**File:** `redis.conf` at root + inline Redis config in compose files
**Action:** Consolidate into a single `redis.conf` used across all environments.
**Effort:** Small (30 min)

---

## 7. TESTING & QUALITY GATES

### 7.1 Test Coverage Gaps (HIGH)
**Issue:** Test directory structure exists but coverage metrics are absent or unknown. Test buckets are split (contract, e2e, integration, performance) but many may be empty/skeleton.
**Action:** 
1. Run `pytest --cov=apps/api --cov-report=term-missing` on backend to establish baseline
2. Run `npx jest --coverage` on frontend
3. Set coverage thresholds in CI (e.g., 70% line, 60% branch)
4. Identify uncovered modules and prioritize by risk
**Effort:** Large (20–40 hours to bring to target)

### 7.2 Test Infrastructure Fragility (MEDIUM)
**File:** `Makefile` defines test commands across 8+ targets (`test-web`, `test-api`, `test-e2e`, `test-integration`, `test-contract`, `test-performance`, `test-e2e-custom`)
**Issue:** The number of test targets suggests test isolation issues — needing different configs for different test types.
**Action:** Consolidate to 3 targets (`test-unit`, `test-integration`, `test-e2e`). Ensure all unit tests run with a single command.
**Effort:** Medium (3–5 hours)

### 7.3 No Contract Tests Enforced (MEDIUM)
**Issue:** `packages/shared/` defines shared types but no automated contract tests verify frontend/backend alignment.
**Action:** Add a CI step that generates OpenAPI schema from backend and validates frontend API client types against it (e.g., `openapi-typescript` for codegen).
**Effort:** Medium (4–6 hours)

---

## 8. CODE CLEANUP

### 8.1 Commented-Out Code Blocks (LOW)
**Finding:** Several files contain large commented-out sections. While not harmful, they reduce readability.
**Action:** Remove commented-out code. Trust git history for retrieval.
**Effort:** Small (1–2 hours across whole repo)

### 8.2 Large File Refactoring (MEDIUM)
**File:** `reports/largest_files_by_loc.txt` — identify top 5 largest files
**Action:** For each top file, assess if it violates single-responsibility principle. Extract cohesive sub-modules.
**Effort:** Varies by file (2–6 hours each)

### 8.3 Dead Code Identification (MEDIUM)
**Action:** Run `vulture` on Python backend and `ts-prune` on TypeScript frontend to find dead exports/functions.
**Effort:** Small (1–2 hours) for initial pass

---

## 9. DOCUMENTATION & KNOWLEDGE

### 9.1 Stale ADR Documents (MEDIUM)
**Files:** `docs/adr/` and `docs/decisions/`
**Issue:** Architecture decisions made early may no longer be accurate.
**Action:** Audit all ADRs for status (`proposed`, `accepted`, `deprecated`, `superseded`). Mark status explicitly in each document. Update or deprecate.
**Effort:** Medium (3–5 hours)

### 9.2 Missing README Files (LOW)
**Issue:** Subdirectory READMEs may be missing or outdated.
**Action:** Ensure each top-level directory (`apps/*`, `packages/*`, `scripts/`, `tests/`, `tooling/`) has a minimal README explaining purpose and how to run/use contents.
**Effort:** Small (2–3 hours)

### 9.3 No Onboarding/Contribution Guide (LOW)
**Action:** Create `CONTRIBUTING.md` with setup steps, coding standards, PR process, and test expectations.
**Effort:** Medium (3–4 hours)

---

## 10. MONITORING & OBSERVABILITY

### 10.1 No Error Budget (MEDIUM)
**Issue:** `prometheus_rules.yml` exists but no SLO/SLI error budgets defined.
**Action:** Define service-level objectives in `docs/operations/SLO.md`. Wire error budgets into CI to block deploys if budget exhausted.
**Effort:** Medium (3–5 hours)

### 10.2 Alert Thresholds Not Documented (LOW)
**File:** `prometheus_rules.yml`
**Action:** Add alert severity, response time expectations, and runbook links as annotations.
**Effort:** Small (1 hour)

---

## Quick Wins (Can Be Done in < 2 Hours Each)

| # | Task | Effort | Impact |
|---|------|--------|--------|
| 1 | Delete `apps/web/package-lock.json` | 5 min | Prevents lock file drift |
| 2 | Run `ts-prune` / `vulture` for dead code | 30 min | Identifies cleanup targets |
| 3 | Update ARCHITECTURE_OVERVIEW.md v1 doc claim | 30 min | Reduces onboarding confusion |
| 4 | Remove commented-out code blocks | 1 hour | Improves readability |
| 5 | Add `.husky/pre-commit` with lint-staged | 1 hour | Prevents debt accumulation |
| 6 | Run `depcheck` on web, `pipdeptree` on API | 1 hour | Identifies unused deps |
| 7 | Add `pnpm audit` / `pip-audit` to CI | 1–2 hours | Automated vulnerability checks |
| 8 | Extract API path constants to shared package | 2 hours | Reduces hardcoded paths |

---

## Recommended Sprint Plan

### Sprint 1: Quick Wins & Safety Net
- Quick wins #1–8 from above
- Restore minimal CI pipeline (lint + type-check + test)
- Configure husky pre-commit hooks

### Sprint 2: Type Safety & API Contracts
- Fix `as any` in Select.tsx and PasskeyPanel.tsx
- Extract shared constants (paths, providers, models) to `packages/shared`
- Consolidate API proxy routes into catch-all

### Sprint 3: Infrastructure Consolidation
- Consolidate Docker compose files
- Choose/remove secondary deployment platform
- Audit and consolidate Redis config

### Sprint 4: Test Infrastructure
- Establish coverage baselines
- Set CI coverage thresholds
- Implement contract tests with OpenAPI validation

### Sprint 5+: Pages Router Migration
- Incrementally migrate pages to App Router
- Start with landing page, then auth, then chat
- Consolidate middleware