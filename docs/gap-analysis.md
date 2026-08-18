# Comprehensive Gap & Incompletion Analysis — goblin-assistant

> Historical snapshot only. Do not use this document as current release
> evidence. Generate the canonical architecture evidence report with
> `make architecture-evidence`; it writes `artifacts/architecture-evidence.json`
> with commit SHA, timestamp, tool version, parser failures, scanned files,
> violations, skipped files, and unresolved parsing failures.

**Generated:** 2026-08-03
**Scope:** Full repository analysis — backend (Python/FastAPI), frontend (Next.js/TypeScript), tests, CI, documentation, architecture

---

## 🔴 CRITICAL — Unimplemented API Endpoints (501 Not Implemented)

Three endpoints are registered but intentionally return 501:

| Endpoint | File | Line | Status |
|----------|------|------|--------|
| `GET /api/goblins` | `apps/api/src/api/api_router.py` | 310 | 501 — "temporarily unavailable" |
| `GET /api/history/{goblin_id}` | `apps/api/src/api/api_router.py` | 318 | 501 — "temporarily unavailable" |
| `GET /api/stats/{goblin_id}` | `apps/api/src/api/api_router.py` | 325 | 501 — "temporarily unavailable" |

These represent core product features (listing goblins, viewing history, viewing stats) that are completely unimplemented. The helper function `_raise_not_implemented()` at line 54 wraps all three.

---

## 🔴 CRITICAL — Architecture Boundary Violations (64 total)

Per the 2026-07-17 tech-debt report, running `make check-api-boundaries` reveals:

### Import-Rule Violations (25)
- **21 route → direct storage imports** — Includes `api_router.py`, `debug_system_router.py`, and others importing from `api.storage`, `api.storage.tasks`, etc.
- **4 service → route dependency inversions**

### Capability Boundary Violations (39)
- **11 provider leakage violations** (specifically `provider_registry.py`)
- **27 allowed-dependency violations** (missing prefixes for `supabase_events`, `pricing`, and others)
- **1 orchestration forbidden import**

### Undocumented Circular Dependencies (9)
Only 7 cycles are listed in `architecture-boundaries.toml`'s `[ignore_cycles]`. Nine cycles were detected but not documented or acknowledged, suggesting the cycle list is out of sync with reality.

---

## 🟠 HIGH — Backend TODO Items (Unfinished / Deferred)

### Google Workspace Services
| File | Line | TODO |
|------|------|------|
| `services/canvas-tools.ts` | 198 | Implement fuzzy match or embeddings-based de-duplication for canvas |
| `services/canvas-tools.ts` | 211 | Improve UX for "file not found" error (open file picker on client) |
| `services/google-docs.ts` | 168 | Add pagination to fetch all changes if more than 100 |
| `services/google-docs.ts` | 310 | Implement batch update for multiple insertions |
| `services/google-docs.ts` | 315 | Implement batch update for multiple insertions (duplicate) |

### Gemini Provider
| File | Line | TODO |
|------|------|------|
| `services/gemini/gemini.ts` | 14 | API keys should come from config/env, not be hardcoded |
| `services/gemini/gemini.ts` | 15 | Add support for different model variants (pro, flash, etc.) |

### Google Sheets
| File | Line | TODO |
|------|------|------|
| `services/google-sheets.ts` | 462 | Should we keep trying or fail fast? Current approach is fail-fast — needs decision |

### PDF Ingestion
| File | Line | TODO |
|------|------|------|
| `services/ingestion/pdf.ts` | 255 | Implement full text extraction for encrypted/protected PDFs |
| `services/ingestion/pdf.ts` | 270 | Implement OCR fallback for scanned PDFs |

### Health Checks
| File | Line | Message |
|------|------|---------|
| `health.py` | 132 | Latency history tracking not implemented for service |
| `health.py` | 142 | Service error tracking not implemented for service |
| `health.py` | 152 | On-demand retest not implemented for service |

---

## 🟠 HIGH — Abstract Base Classes with NotImplementedError

These are scaffolded abstractions with no concrete implementations, indicating an agent/search framework that was started but never completed:

| File | Line | Method | Context |
|------|------|--------|---------|
| `core/agents.py` | 44 | `Agent.select_action` | Abstract agent — no implementation |
| `core/agents.py` | 52 | `Environment.initial_percept` | Abstract environment — no implementation |
| `core/agents.py` | 56 | `Environment.do` | Abstract environment — no implementation |
| `core/search.py` | 234 | `PrioritySearcher.priority` | Abstract search — no implementation |

---

## 🟠 HIGH — Frontend Type Safety Gaps

**97 `as unknown` / `as any` type assertions** across the web application:

| Area | Count | Example |
|------|-------|---------|
| WebAuthn / PasskeyPanel.tsx | 6+ | Credential type casts for WebAuthn API |
| API response handling | 5+ | `(response as any).department`, `(response as any).department_reason` |
| Error handling | 4+ | `error as any` for status code extraction |
| Provider router | 3 | `as unknown as JsonProviderEntry` triple-cast |
| Chat history parsing | 2 | `parsed.messages as unknown[]` |
| Health header | 1 | `data as unknown as Record<string, unknown>` |

**21 files** contain `eslint-disable` comments and **3 files** use `@ts-ignore` or `@ts-expect-error` directives.

---

## 🟠 HIGH — Missing Developer Onboarding File

The `CONTRIBUTING.md` instructs contributors to run:
```
cp apps/web/.env.example apps/web/.env.local
```

**`apps/web/.env.example` does not exist.** Only `apps/web/.env.local` exists (not committed to git, as expected). This is a blocker for new developers.

---

## 🟡 MEDIUM — Backend Lint Suppression Density

**126 files** contain `noqa` comments across `apps/api/src/api/`:

| Category | File Count |
|----------|------------|
| Production source files | 50+ |
| Test files | 70+ |

Key concentration areas:
- `providers/dispatcher.py` and sub-packages
- `routing/` — all files (`ml_router.py`, `policy_rules.py`, `selection.py`, etc.)
- `chat_router/` — messages, contextual, streaming
- `services/` — 20+ files
- `assistant_tools/` — 6+ files

This indicates persistent lint violations that were silenced rather than fixed over time.

---

## 🟡 MEDIUM — Test Coverage Gaps

### Suppressed/Disabled Tests
| File | Issue |
|------|-------|
| `test_financial_report_tool.py` | `@pytest.mark.xfail` |
| `test_sec_filings_tool.py` | `@pytest.mark.xfail` |
| `test_task_memory_integration.py` | `@pytest.mark.xfail` |
| `test_write_time_intelligence.py` | `@pytest.mark.skipif` (conditional on environment) |
| `test_performance.py` | Entire file xfail'd |
| `test_attestation_webhook.py` | 3 tests xfail'd |
| `test_privacy_router.py` | 1 test xfail'd |

### Missing Test Buckets
- **`tests/security/`** directory exists but has no test manifest entry — security tests have no CI coverage
- **Web consumer contract test** is a single file — contract testing is thin
- **`.coveragerc`** excludes all `test_*` files, `*/migrations/*`, and several specific modules from coverage measurement

---

## 🟡 MEDIUM — Dead Code Residue

Per the 2026-07-17 tech-debt report:
- Original debt: 46 Python dead-code findings, 5 unused files, 3 unused dependencies
- After cleanup: **4 known false positives remain** (not truly dead, but flagged by the tooling)

---

## 🟢 LOW — Operational & Config Gaps

### Script Sprawl
- **`apps/api/scripts/`** — 30+ shell scripts, many are one-off setup scripts
- **`scripts/`** (root) — 50+ scripts for CI, deployment, testing, credential setup, etc.
- Unclear which scripts are still maintained vs. obsolete

### Config Duplication
| Issue | Detail |
|-------|--------|
| `config/providers.json` vs `config/providers.toml` | Two config formats for providers — which is canonical? |
| `prometheus_rules.yml` vs `infra/alert_rules.yml` | Duplicate alert rule definitions |
| `docker-compose.yml` + `docker-compose.goblinos-override.yml` | Two compose files; override relationship undocumented |
| `Dockerfile` + `Dockerfile.sandbox` | Two Dockerfiles; sandbox purpose is clear but relationship could be documented |

### Stale Documentation
| File | Issue |
|------|-------|
| `docs/archive/` | Contains archived docs — unclear what's still relevant |
| `REFACTOR_SUMMARY.md` | Documents a completed refactor — may be stale |
| `docs/tech-debt-report.md` | Generated 2026-07-17 — 17 days stale at time of this analysis |

---

## 🟢 LOW — ForgeTM & Celery Notes

From the AGENTS.md guidelines, these are explicitly called out as **intentionally deprioritized** — not gaps per se, but noted for completeness:
- **ForgeTM** stays deprioritized
- **No more Celery workers / priority queues** should be added (three worker pools is sufficient for solo-dev scale)
- **No more docs automation** — drift gate is sufficient

---

## Summary Table

| Severity | Category | Count | Key Theme |
|----------|----------|-------|-----------|
| 🔴 Critical | Unimplemented endpoints | 3 | Core product features returning 501 |
| 🔴 Critical | Architecture violations | 64 | Boundary + capability + undocumented cycles |
| 🟠 High | Backend TODOs | 9+ | Google services, Gemini, PDF, health checks |
| 🟠 High | NotImplementedError stubs | 4 | Agent/search framework never completed |
| 🟠 High | Frontend type safety | 97 casts | Type assertions throughout web app |
| 🟠 High | Missing .env.example | 1 | Developer onboarding blocker |
| 🟡 Medium | Lint suppressions | 126 files | `noqa` and `eslint-disable` density |
| 🟡 Medium | Test gaps | 7+ xfail/skip | Plus missing security test bucket |
| 🟡 Medium | Dead code | 4 | False positives remaining |
| 🟢 Low | Script/config sprawl | 5+ | Duplication, stale docs |
