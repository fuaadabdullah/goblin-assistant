# Merge Order — Integration Governor (2026-08-03, revised)

> **Temporary document.** Delete after all PRs below have landed on `main`.
>
> Status key: ✅ done · ⏳ waiting on CI · 🔧 needs work · 🗒️ queued
>
> **Revision note (2026-08-03 evening):** Reconciled against `gh pr list` live
> state. PR #52 merged. Local CI audit found and fixed lint-gate failures
> (stale build artifacts in ESLint scope, 24 ruff errors, ASYNC240, orphaned
> docs/gap-analysis.md). All architecture gates (boundaries, cycles,
> capabilities) pass on current HEAD.

---

## Wave 1 — `main` targets (no dependencies)

### PR #56 — `ci: guard Supabase keep-alive + repair CI gates` ⏳
- **Branch:** `fix/supabase-keepalive-secret-guard` → `main`
- **Size:** +340/-127 (CI/tooling only)
- **Mergeable:** ✅ MERGEABLE (confirmed via GitHub API)
- **Merge when:** `policy`, `lint`, `format-check`, `merge-gates` all pass.

### PR #49 — `feat(infra): production hardening` ⏳
- **Branch:** `fix/premarket-brief-path` → `main`
- **Size:** +6405/-1005 across 45 commits
- **Mergeable:** ✅ MERGEABLE (confirmed via GitHub API)
- **Merge when:** `policy` and `ci/circleci: policy` both pass.
- **Blocks:** PR #50 base must be updated to `main` post-merge.

---

## Wave 2 — depends on Wave 1

### PR #50 — `feat(db): Backend Performance & Database` 🔧
- **Branch:** `feature/routing-refactor` → `fix/premarket-brief-path` (needs retarget to `main` after #49 merges)
- **Size:** +27651/-20465 — **exceeds 800-line limit significantly**
- **Mergeable:** ❌ CONFLICTING
- **Action required after #49 merges:**
  1. Rebase onto `main`
  2. Split into (a) routing/DB schema changes and (b) performance/pool tuning
  3. Open two focused PRs, each ≤800 meaningful lines

---

## Wave 3 — `reorg/monorepo-visibility` integration branch

> These three PRs all target `reorg/monorepo-visibility`. They merge into
> the integration branch first, then the integration branch lands on `main`
> via PR #55 (Wave 4).

### PR #54 — `ci: preview quality gates` ⏳
- **Branch:** `ci/preview-quality-gates` → `reorg/monorepo-visibility`
- **Mergeable:** ✅ MERGEABLE
- **Merge first** (CI-only, no product risk)

### PR #53 — `feat(settings): Frontend Renaissance — settings overhaul` ⏳
- **Branch:** `feature/settings-overhaul` → `reorg/monorepo-visibility`
- **Mergeable:** ✅ MERGEABLE
- **Merge second** (UI only)

### PR #51 — `feat(chat): Frontend Renaissance — conversation UI` ⏳
- **Branch:** `feature/chat-redesign-v2` → `reorg/monorepo-visibility`
- **Mergeable:** ✅ MERGEABLE
- **Merge third** (UI + chat logic)

---

## Wave 4 — land `reorg/monorepo-visibility` on `main`

### PR #55 — `feat(web): complete App Router migration + monorepo reorg` 🔧
- **Branch:** `reorg/monorepo-visibility` → `main`
- **Mergeable:** ❌ CONFLICTING
- **Prerequisite:** Wave 3 must be fully merged first
- **Action required:** Rebase onto `main` after Wave 3 completes, resolve
  conflicts, then merge. If still too large for review, split into:
  - #55-A: App Router migration (delete `src/pages/`, `next/router` → `next/navigation`)
  - #55-B: Monorepo reorg (packages, CI/CD, docs, infra scripts)

---

## Backlog — Dependabot PRs (non-blocking)

| PR | Title | Status |
|----|-------|--------|
| #47 | build(deps): bump prod-dependencies group (15 updates) | MERGEABLE |
| #46 | build(deps-dev): bump dev-dependencies group (32 updates) | MERGEABLE |
| #45 | build(deps-dev): bump dev-dependencies in apps/web (30 updates) | MERGEABLE |
| #44 | build(deps): bump prod-dependencies in apps/web (15 updates) | MERGEABLE |
| #43 | build(deps): bump actions/setup-node 4→7 | MERGEABLE |
| #41 | build(deps): bump pip prod-dependencies (64 updates) | MERGEABLE |
| #12 | build(deps): bump hashicorp/setup-terraform 3→4 | MERGEABLE |
| #10 | build(deps): bump docker/metadata-action 5→6 | MERGEABLE |
| #9 | build(deps): bump github/codeql-action 3→4 | MERGEABLE |
| #8 | chore(deps): bump pnpm/action-setup 2→6 | MERGEABLE |

> Merge dependabot PRs after Wave 1 lands to avoid churn. They are all
> MERGEABLE and independent.

---

## Closed / Superseded

| PR | Reason |
|----|--------|
| #48 — API Platform Phase 2 Track 1 | Superseded by `merge: test-coverage/saas-service` (2026-07-28) |
| #52 — Operations dashboard | ✅ Merged into `reorg/monorepo-visibility` |

---

## CI Health (verified locally 2026-08-03)

| Gate | Status | Notes |
|------|--------|-------|
| `make lint` (web + api + policy) | ✅ PASS | Fixed: eslint ignores for .tmp/tmp, 24 ruff errors, ASYNC240, docs-inventory |
| `make type-check` | ✅ PASS | |
| `make check-api-boundaries` | ✅ PASS | route_no_direct_storage + service_no_route_dependency enforced |
| `make check-api-cycles` | ✅ PASS | 1 baseline-allowed cycle (secrets.auth↔vault_adapter) |
| `make check-capability-boundaries` | ✅ PASS | 6 capabilities governed |
| `make check-api-calls` | ✅ PASS | Frontend API path contract valid |
| `make sdk-check` | ⚠️ LOCAL ONLY | Requires Node 20/22; local env has Node 26. CI pins Node 20 — passes there. |

---

## Definition of Done

- [ ] No conflicted open PRs
- [ ] No superseded open PRs
- [ ] All open PRs have a documented merge order (this file)
- [ ] `main` CI and deployment green
- [ ] This file deleted