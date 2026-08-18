# Gap, Caveat, and Issue Register

> Current working register for repo health and release readiness. Use this as
> triage context, not as release evidence by itself. The canonical machine
> evidence remains `make architecture-evidence`,
> `make check-quality-baseline`, `make contract-checks`, and focused runtime
> tests for the touched surface.

**Updated:** 2026-08-18
**Branch:** `feat/goblin-query-api`
**Scope:** Goblin query API, architecture governance, docs consolidation,
contract generation, deprecated infra cleanup, and remaining dirty-tree risk.

---

## Executive Summary

The most important correction from older snapshots: the Goblin query endpoints
are no longer known 501 stubs. The current API router wires concrete handlers
for goblin catalog, history, and stats, and
`apps/api/src/api/tests/test_goblin_query_api.py` asserts that OpenAPI exposes
200 response schemas instead of 501 responses.

The current risk profile has shifted from "missing endpoint implementation" to
"integration and release hygiene." Architecture boundary checks now pass, but
the working tree is still very broad and several commits are not yet the clean
sequence originally requested. Deprecated Terraform/Kubernetes/Fly-style
deployment assets have been removed or archived in dedicated commits, and the
root script/tooling cleanup has also landed. The remaining risk is now
concentrated in broad app/API churn, CI gate changes, generated-contract drift,
and release proof that has not yet been rerun after the latest dirty-tree state.

## Current Evidence Snapshot

Latest verified checks on 2026-08-18:

| Check | Result | Caveat |
|---|---:|---|
| `make check-api-boundaries` | Pass | Run at repo root after an initial wrong-directory attempt failed because the target does not exist under `apps/api`. |
| `make check-api-cycles` | Pass | Older cycle debt in this document was stale. |
| `make check-capability-boundaries` | Pass | Capability boundary violations are currently zero. |
| `python3.11 tooling/quality/quality_baseline.py --timeout-seconds 10 --partial-output .tmp/quality-baseline-partial.json --quiet` | Pass | This is a ratchet/baseline gate, not proof that suppression debt is gone. |
| `status_code=501` / `HTTP_501` search across API/web/packages | 0 hits | Does not replace endpoint smoke tests against a running API. |
| `node scripts/check-contrast.js` | Pass | Wrapper now delegates to `tooling/quality/check-contrast.js`. |
| `node scripts/guard-no-inline-styles.js` | Pass | Wrapper now delegates to `tooling/quality/guard-no-inline-styles.js`. |
| `node scripts/guard-no-client-v1.js` | Pass | Guard now scans production web source while ignoring tests/MSW fixtures. |
| `PYTHONPATH=packages/shared/src python3.11 scripts/generate-providers-json.py --check` | Pass | Wrapper delegates to canonical generator. |
| `node scripts/generate-theme-css.js` | Pass | Generator is self-contained and aligned to current warm theme seeds. |
| `bash -n` on modified ops/setup/deploy scripts | Pass | Syntax only, not runtime proof. |
| `python3.11 -m py_compile` on modified Python tooling/scripts | Pass | Syntax/import parse only. |

Current quality baseline metrics:

| Metric | Count |
|---|---:|
| Web type assertions (`as any` / `as unknown`) | 80 |
| Web files with ESLint/TS suppressions | 10 |
| Python files with `noqa` | 120 |
| Xfail tests | 0 |
| Suppressions classified as clearly removable | 197 |
| Suppressions classified as legacy debt | 66 |
| Suppressions classified as interop/typing issue | 100 |
| Architecture boundary violations | 0 |
| Capability boundary violations | 0 |
| Total architecture violations | 0 |

Current working-tree scale:

| Git status class | Count |
|---|---:|
| Modified files | 688 |
| Deleted files | 123 |
| Untracked files/directories | 5 |
| Total status entries | 816 |

## Critical Gaps

### 1. Branch History Is Still Not the Requested Clean Story

The branch currently contains decomposed commits, but one commit has a
misleading subject:

| Commit | Subject | Issue |
|---|---|---|
| `18ef9d25` | `chore(infra): remove orphaned k8s/ manifests` | Contents are architecture/quality/debt reporting files, not k8s removals. |

This is a release-hygiene problem because reviewers will reason from the commit
subject before reading the diff. It should be fixed only with an explicit
history-edit decision, because amending/rebasing published or shared history has
coordination risk.

### 2. Deprecated Infra Deletion Is Committed, but Stale References Remain

Deprecated Terraform, Kubernetes, `kind-config.yaml`, `terraform.tfvars.example`,
`docker-compose.redis.yml`, and archived deployment docs were removed in
dedicated commits. Active deploy workflows and root verification scripts were
normalized around Render/Vercel ownership and `/api/v1/health`.

Cleaned in the committed infra/script slices:

| Area | Examples | Risk |
|---|---|---|
| GitHub workflows | Removed `.github/workflows/terraform-plan.yml`; made staging/prod deploy workflows Render-only. | Needs final end-to-end workflow proof after remaining CI changes settle. |
| Dependabot | Removed Terraform ecosystem entry. | Covered by operational policy. |
| Verification scripts | Rewrote `scripts/verify-cicd-setup.sh` around Render/Vercel and retired-path checks. | Script passed before commit. |
| Setup scripts | Deleted Terraform/Fly/Kubernetes deployment helpers. | Structure/docs gates passed before commit. |
| Operations docs | Replaced Terraform/Fly/Kubernetes instructions with Render/Vercel docs or deprecated stubs. | Docs gates passed before commit. |
| Root script/tooling wrappers | Consolidated root wrappers to `tooling/generators/*` and `tooling/quality/*`. | Focused wrapper checks passed before commit. |

Remaining risk: stale production health references still exist outside the
latest staged slices, especially older docs and non-primary workflow surfaces.
Treat new executable references to removed assets or the old Render backend URL
as regressions.

### 3. Dirty Tree Is Too Broad for Confident Release Review

There are 816 status entries after the already-created commits. This is larger
than a normal focused feature branch and mixes backend, frontend, infra, docs,
generated contracts, scripts, tests, package locks, and deleted legacy trees.

Primary risk: unrelated work can be accidentally committed under a plausible
message. That already nearly happened during the infra split, and the current
state still has enough breadth for a repeat.

## Deep Dive Remaining Gaps

### 4. Frontend Churn Is the Largest Review-Risk Cluster

The dirty tree is dominated by `apps/`, with `apps/web` making up a large share
of the remaining modifications/deletions/untracked paths.

| Gap | Evidence | Why It Matters |
|---|---|---|
| App Router migration is only partially reviewable from status | `apps/web/src/app/` is still untracked while legacy page/test paths are deleted or modified. | Missing tracked files can make local tests pass while CI or reviewers cannot reproduce the app shape. |
| Web-local provider config was deleted | `apps/web/config/providers.toml` and `apps/web/src/config/providers.json` are deleted. | This is probably correct if root/shared provider config is canonical, but all imports must be proven migrated. |
| Barrel exports and feature indexes were deleted broadly | Multiple `apps/web/src/features/*/index.ts`, `hooks/index.ts`, and `components/index.ts` entries are deleted. | TypeScript path imports can fail outside the focused tests already run. |
| Auth/state surfaces changed heavily | Auth bootstrap, login, passkey, API key, session, and store files are modified/deleted. | These are high-value runtime paths; unit tests do not replace an authenticated browser journey. |
| Generated web types were removed | `apps/web/src/types/generated.ts` is deleted. | Safe only if SDK/shared generated types fully replace it and imports are clean. |
| Web env example is untracked | `apps/web/.env.example` is untracked. | Environment docs can drift from runtime validation if not intentionally committed. |

Recommended handling: make the App Router/web migration its own slice with
explicit typecheck, focused route tests, and one authenticated flow proof.

### 5. Backend Compatibility Churn Needs Import and Route Proof

The backend still has broad modifications and deletions under `apps/api/src/api`.
Several deleted files look like legacy module facades or old router locations.

| Gap | Evidence | Why It Matters |
|---|---|---|
| Legacy router files are deleted | Examples include `api_keys_router.py`, `ops_router.py`, `parse_router.py`, `routing_router.py`, `search_router.py`, `secrets_router.py`, `settings_router.py`, `stream_router.py`, and `write_time_router.py`. | Safe only if compatibility imports and route aliases are preserved elsewhere. |
| Middleware moved from file to package | `middleware.py` is deleted while `middleware/` files are modified. | Startup and import order can break even if isolated unit tests pass. |
| Tooling namespace moved | `api/tools/*` is deleted while `api/assistant_tools/*` is modified. | Backward-compatible imports matter for tests, plugin hooks, and external references. |
| Service modules were split/deleted | Retrieval, memory promotion, write-time, and context assembly files are changed. | These are cross-cutting runtime services with high regression blast radius. |
| Root API test files were deleted | Several `apps/api/src/api/test_*.py` files are deleted while many `src/api/tests/*` files are modified. | Test relocation is good only if collection and coverage remain intact. |

Recommended handling: before any backend consolidation commit, run
`pytest --collect-only`, a focused import-compatibility smoke, and the route
manifest/contract gates from the final source state.

### 6. CI/CD Changes Are High Leverage and High Risk

Several CI files remain modified after the infra and scripts commits.

| Surface | Current Risk |
|---|---|
| `.github/workflows/ci.yml` | Changes turn formerly report-only API lint/policy into hard gates and add quality/architecture jobs. This is good governance, but it can block merges immediately if baseline assumptions are wrong in CI. |
| `.circleci/config.yml` | It introduces a much larger pipeline, deploy jobs, autofix hooks, Codecov uploads, and stricter security gates. It still contains `/health` checks instead of `/api/v1/health` in at least the shown diff. |
| CircleCI pnpm install | Uses `pnpm install --frozen-lockfile=false`, which weakens reproducibility compared with the repo’s frozen-lockfile preference. |
| CI autofix | `tooling/automation/ci_autofix_trigger.py` switches model/turn budget and is wired into failure paths. This has credential, cost, and safety implications. |
| Package scripts | `packages:type-check` and `packages:build` now enumerate package configs explicitly. This is stricter, but less tolerant of package moves/removals. |

Recommended handling: split CI changes into a governance commit, normalize
health paths, keep frozen installs unless there is a documented reason, and
validate YAML plus representative dry-run commands before committing.

### 7. Security Bucket Is Promising but Not Yet Integrated Safely

`tests/manifests/security.json` is untracked and `tooling/quality/run-test-bucket.py`
now accepts a `security` bucket.

| Gap | Caveat |
|---|---|
| The security manifest installs `pip-audit` during the gate | Network-dependent installs inside a gate are brittle unless cached or part of setup. |
| `bandit` and `audit-ci` availability is assumed | CI jobs must install them or fail with tool-not-found noise. |
| Secret scan path is referenced | `scripts/security/scan_secrets.py` must be present, executable, and safe against false positives before this becomes blocking. |
| No root `test:security` script or Make target is shown yet | The bucket exists but may not be discoverable from standard workflows. |

Recommended handling: commit the manifest together with the CI/Make/package
entrypoints that run it, and decide whether it is blocking or report-only at
first.

### 8. Generated Artifacts Can Drift Again

`tooling/generators/route_manifest.py` now handles nested included routers more
accurately, and SDK/OpenAPI artifacts were already regenerated in an earlier
commit. The remaining backend/router churn means those generated artifacts can
become stale again before final closeout.

Required final proof:

| Gate | Reason |
|---|---|
| `make generate-route-manifest` | Ensures nested-route logic is reflected in generated route inventory. |
| `make sdk-generate` or `make sdk-check` | Ensures OpenAPI/TypeScript clients match final API shape. |
| `make contract-checks` | Catches source/generated drift before review. |

### 9. Production Health Path Is Still Split Across Older Surfaces

Committed deploy scripts now use `/api/v1/health`, but repository-wide evidence
still shows stale `/health` references in docs, generated descriptions, older
workflow surfaces, and provider-specific health checks.

Not all `/health` strings are wrong. Some are legitimate logical paths,
provider health probes, compatibility aliases, or generated logical-path fields.
The gap is specifically executable production verification against the old
Render service or root health path.

High-signal follow-up searches:

| Search | Purpose |
|---|---|
| `rg "goblin-assistant-backend\\.onrender\\.com" .github scripts docs` | Finds old production backend URL references. |
| `rg "goblin-backend-dt30\\.onrender\\.com/health" .github scripts docs` | Finds current backend URL with old root health path. |
| `rg "curl .* /health|/health/ready" .github scripts docs` | Separates executable instructions from historical text. |

### 10. Untracked Files Need Ownership Decisions

Current untracked entries:

| Path | Likely Decision |
|---|---|
| `MERGE_ORDER.md` | Commit only if it is an intentional reviewer/merge aid; otherwise keep local or remove later. |
| `apps/web/.env.example` | Likely commit with web env validation changes. |
| `apps/web/src/app/` | Must be committed with the App Router migration or the web tree is incomplete. |
| `apps/web/src/config/__tests__/env-example.test.ts` | Commit with env example/runtime validation. |
| `tests/manifests/security.json` | Commit with security-bucket CI entrypoints or defer. |

### 11. Quality Debt Counts Need Recalculation After Final Slices

The register still includes quality-baseline counts from earlier evidence.
Because broad web/backend files remain dirty, those counts should be treated as
a snapshot, not final release evidence.

Final recalculation should include:

| Metric | Why |
|---|---|
| Web `as any` / `as unknown` count | Frontend changes may add or remove assertions. |
| Python `noqa` count | Backend compatibility moves can either reduce or grow suppressions. |
| Suppression classifications | The ratchet only helps if the baseline matches final source. |
| Architecture/capability violations | Boundary checks must run against the final diff, not an earlier midpoint. |

## High-Severity Issues

### 12. Goblin Query API Needs Runtime Proof, Not Just Unit/OpenAPI Proof

Resolved:

| Endpoint | Current router behavior |
|---|---|
| `GET /api/goblins` | Delegates to `GoblinQueryService.list_goblins()`. |
| `GET /api/history/{goblin_id}` | Delegates to `GoblinQueryService.get_history(...)`. |
| `GET /api/stats/{goblin_id}` | Delegates to `GoblinQueryService.get_stats(...)`. |

Remaining caveats:

| Gap | Why It Matters |
|---|---|
| No recent running-server smoke evidence captured in this pass | TestClient and OpenAPI checks do not prove deployed middleware, auth, route prefixing, or startup lifecycle. |
| Routes appear under `/api/v1/api/...` in tests/OpenAPI | The double `api` segment may be intentional compatibility, but it is user-facing awkwardness and should be explicitly accepted or deprecated. |
| Stats unavailable metrics are represented as `null` | This is honest, but consumers need contract tests so UI code does not treat nulls as real zero values. |
| History depends on repository scan limits/cursors | Pagination correctness needs at least one integration-style test with a realistic backing store or fixture volume. |

### 13. Quality Baseline Is Passing but Debt Remains Material

The quality gate is doing the right kind of thing: classifying and ratcheting
suppressions instead of pretending the repo is clean. But the baseline still
contains significant debt:

| Debt | Count | Caveat |
|---|---:|---|
| Clearly removable suppressions | 197 | These should become opportunistic cleanup when touching affected files. |
| Python files with `noqa` | 120 | Many are compatibility/lazy-import seams, but density still reduces signal. |
| Web type assertions | 80 | Some are test doubles or WebAuthn/DOM interop; others are likely avoidable. |
| Legacy-debt suppressions | 66 | Needs ownership and removal criteria, not indefinite labeling. |

This should not block the Goblin query API by itself, but it should block any
claim that the repo is broadly type/lint clean.

### 14. Documentation Consolidation Changed the Information Architecture

The docs consolidation is valuable, but it deleted or moved many docs. The
runbook migration validator passed, which is good. Remaining risks:

| Gap | Why It Matters |
|---|---|
| Current docs now mostly reference deleted deployment assets only as retired/deprecated context | Needs final docs-link/inventory proof before commit. |
| Archived deployment docs were deleted in the infra cleanup commits | Good, but older current docs can still carry stale historical deployment language. |
| Some docs are intentionally historical, but not all historical references are clearly marked | Readers can mistake old deployment guidance for current policy. |
| The root docs map and operation docs need to stay aligned with generated indexes | Manual edits can drift again unless validated with existing checks. |

### 15. Workflow and Deployment Authority Is Split

Render is the documented canonical backend deployment target and Vercel is the
documented frontend target. This pass removed active Terraform/Kubernetes/Fly
deployment wiring from workflows, setup scripts, and current deployment docs.

Remaining caveats:

| Surface | Open Question |
|---|---|
| `fly.toml` | Kept intentionally as an archived reference because `check_operational_policy.py` requires that state. |
| `.circleci/config.yml` | Still modified elsewhere in the dirty tree; needs final review before release. |
| Root Docker Compose files | Need final docs/readme language to keep local-only versus production ownership clear. |
| Self-development Fly token note | May be a separate worker architecture rather than product deploy; not removed in this infra slice. |

## Medium-Severity Issues

### 16. Abstract Agent/Search Base Classes Remain Intentionally Incomplete

Current `NotImplementedError` production hits:

| File | Method |
|---|---|
| `apps/api/src/api/core/agents.py` | `Agent.select_action` |
| `apps/api/src/api/core/agents.py` | `Environment.initial_percept` |
| `apps/api/src/api/core/agents.py` | `Environment.do` |
| `apps/api/src/api/core/search.py` | `PrioritySearcher.priority` |

These may be valid abstract contracts, not product gaps. The caveat is that
they should be represented with `abc.ABC`/`@abstractmethod` if they are
framework contracts, and should not be listed as release blockers unless a
concrete runtime path instantiates them.

### 17. Health Placeholder Endpoints Still Return Empty/Not-Implemented Data

`apps/api/src/api/health.py` still includes service health endpoints that report
empty latency/error/retest state with messages saying the tracking is not
implemented for a service.

This is not the same as a 501 endpoint, but it is still product-visible
incompleteness if clients rely on operational telemetry.

### 18. Test Proof Is Focused, Not Comprehensive

Recent passing checks cover architecture gates, quality baseline, contract
generation, provider config, docs links/inventory, and focused Goblin query API
unit/OpenAPI behavior. Missing or not recently rerun in the current final state:

| Test/Gate | Caveat |
|---|---|
| Full `make test-api` | Not shown passing after the latest broad dirty-tree state. |
| Full `make test-web` | Not shown passing after frontend churn. |
| Full `make type-check` | Not shown passing after generated SDK and web changes. |
| Running backend smoke via `/api/v1/health` and Goblin endpoints | Needed before release claim. |
| E2E/authenticated chat journey | Still high value because route/middleware/proxy changes can pass unit tests and fail in-app. |

### 19. Generated Contract Artifacts Are Committed, but Need Drift Guard

The SDK/OpenAPI artifacts were regenerated and committed, but the remaining
dirty tree includes additional API and route-related changes. That means the
generated artifacts may become stale again before final closeout unless
`make contract-checks` is rerun at the end.

### 20. Provider Configuration Authority Still Needs Watchfulness

Provider config governance is improved, and provider checks passed earlier.
Remaining risk is operational rather than structural:

| Gap | Caveat |
|---|---|
| `config/providers.toml` and `config/providers.json` both exist | This is acceptable only if TOML remains canonical and JSON is generated/validated. |
| Web config copies were removed/changed | Verify no runtime import still expects deleted web-local provider files. |
| Generated provider artifacts can drift after manual edits | Keep `make check-providers-json` in the final proof bundle. |

## Low-Severity / Opportunistic Issues

### 21. Script Sprawl Is Smaller, but Ownership Still Needs a Final Pass

The latest script commit reduced root script sprawl by turning common entrypoints
into wrappers over `tooling/*` and deleting obsolete backend start helpers. Some
root/ops scripts and CI references still remain in the dirty tree. The risk is
mostly maintainability and contributor confusion.

Recommendation: do not create another docs checklist. Instead, converge scripts
behind Makefile targets and delete scripts only when no docs/workflows call
them.

### 22. Frontend Type Hardening Should Stay Opportunistic

The AGENTS guidance explicitly says not to open a dedicated type-hardening pass.
The right posture is:

| Do | Avoid |
|---|---|
| Remove nearby `as any`/suppression debt when already touching a file | Broad drive-by cleanup PRs |
| Improve test helper types as part of test edits | Churning tests only to satisfy aesthetics |
| Add shared contract types when a real API seam needs them | Creating unused constants/types frameworks |

### 23. Archived Docs and Historical Reports Need Clear Labels

Historical reports are useful if labeled. They are dangerous if they look
current. The current gap doc should remain the human risk register; generated
evidence should remain the machine truth.

## Release Caveats

Do not claim release readiness until all of the following are true:

| Required Before Release Claim | Current State |
|---|---|
| Working tree reduced to intentional, reviewable changes | Not true; 816 status entries remain. |
| Commit history matches the requested story or the mismatch is explicitly accepted | Not true; one commit subject is misleading. |
| Deprecated infra deletion has no active executable references | Mostly true after this pass; final search and policy checks still required. |
| Contract artifacts regenerated after final API changes | Partially true; must rerun at end. |
| Runtime smoke proves backend startup and Goblin endpoints | Not yet captured in this pass. |
| Web/API type and test gates run after final dirty-tree resolution | Not yet captured in this pass. |

## Recommended Remediation Order

1. Decide whether to rewrite/amend commit history so `18ef9d25` gets the
   correct architecture/quality subject.
2. Split and validate the remaining CI/CD governance changes. Normalize
   production health paths, preserve frozen installs unless deliberately
   changing policy, and decide whether autofix/security gates are blocking.
3. Commit or defer the security bucket with its Make/package/CI entrypoints.
4. Re-run docs gates after any remaining docs/reference cleanup:
   `check_docs_inventory`, `check_docs_links`, and
   `check_runbook_migration_map`.
5. Re-run contract gates after all API/router changes:
   `make contract-checks`, `make sdk-check`, and route manifest generation.
6. Run focused runtime smoke for `/api/v1/health`, `/api/v1/api/goblins`,
   `/api/v1/api/history/{goblin_id}`, and `/api/v1/api/stats/{goblin_id}`.
7. Only then run broader test/type gates or explicitly document why they are
   deferred.

## Resolved or Downgraded from Older Snapshots

| Older Finding | Current Status |
|---|---|
| Three Goblin query endpoints return 501 | Resolved in current source; no `status_code=501` or `HTTP_501` hits found across API/web/packages. |
| 64 architecture/capability violations | Stale; current root checks pass and quality baseline reports zero. |
| Undocumented API cycles | Stale; `make check-api-cycles` passes. |
| Missing `apps/web/.env.example` | Currently present as an untracked file; still needs intentional commit or ignore decision. |
| Xfail test debt | Current quality baseline reports zero xfail tests. |
