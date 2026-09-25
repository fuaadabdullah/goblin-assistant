# Goblin Assistant

AI assistant with multi-provider LLM routing. It's a pnpm + Python monorepo.

## How to read this file

This file has two kinds of rules:

- **Hard rules**: CI or lint enforces them, and a violation fails the build. These are marked **(enforced)**.
- **Defaults**: the established pattern. Each comes with the reason behind it. Follow them unless the situation clearly calls for something else, and if you depart from one, say so and why.

If the code disagrees with this file, trust the code and flag the mismatch.

## Module map

| Module | Owns | Depends on |
| --- | --- | --- |
| `apps/web` | Next.js 16 / React 19 UI, same-origin proxy routes (`app/api/`), route guards (`proxy.ts`) | `packages/shared`, `packages/ui`; the backend only over HTTP |
| `apps/api` | FastAPI backend: chat, LLM providers, routing, sandbox, auth, storage | Its own code plus `packages/shared` (Python) |
| `packages/shared` | Cross-app contracts: API route and proxy definitions, provider config schema | Nothing app-specific |
| `packages/sdk` | Generated OpenAPI snapshot and TS types | Generated, never hand-edited |
| `packages/ui`, `types`, `config` | Shared UI primitives, types, config | Nothing app-specific |
| `tooling/`, `scripts/` | Generators, quality guards, architecture checks, ops scripts | Not imported at runtime |

Boundary principles:

- Keep app-local code inside its app. Code used by both apps goes in `packages/*`, never in a root `src/`.
- The web app never imports backend code. The two sides share only contracts, and those contracts are generated.
- In the backend, capabilities (`chat`, `providers`, `memory`, `sandbox`, `auth`, `orchestration`) declare the modules they own and what they may depend on, in `apps/api/architecture-capabilities.json` **(enforced)**. When new code has no clear owner, extend a capability's declaration on purpose rather than slipping the import in.
- Layer rules in `apps/api/architecture-boundaries.toml` **(enforced for new code)**:
  - Routes don't touch storage directly.
  - Services don't import routes or `fastapi`/`starlette`.
  - No new import cycles.

## Commands

Run commands from the repo root through the `Makefile`. The scripts are POSIX shell, so on Windows use Git Bash rather than PowerShell.

- Dev: `make web-dev` (:3000), `make api-dev` (:8001, needs `JWT_SECRET_KEY`)
- Check: `make lint`, `make type-check`, `make format`
- Test: `make test-web`, `make test-api`, `make test-e2e`
- Single test:
  - Web: `cd apps/web && NODE_OPTIONS=--no-experimental-webstorage npx vitest run <file>`
  - API: `cd apps/api && PYTHONPATH=src python3.11 -m pytest -o "addopts=" <file> -k <name>`
- Boundary checks: `make check-api-boundaries`, `make check-capability-boundaries`, `make check-api-cycles`
- Regenerate contracts after changing backend routes or proxy prefixes: `make sdk-generate`, then `make contract-checks` **(enforced, CI fails on stale output)**
- After editing `config/providers.toml`: `make generate-providers-json`

## Backend (`apps/api/src/api`)

- The import root is `api`, so set `PYTHONPATH=src`. The app is assembled in `app_factory.py` and routes are registered in `bootstrap/routes.py`. Public routes live under `/api/v1/...`.
- Layering: routes → services / `pipeline` / `departments` → `providers` / `routing` → `storage`. Put business logic in services so it can be tested without HTTP.
- Before adding or changing an LLM provider, read `providers/README.md`. Adapters return `ProviderResult`, and the dispatcher owns fallback, quota, circuit breakers and metrics, so adapters shouldn't re-implement them.
- `*_pkg/` directories hold pieces extracted from a large module next to them (for example `providers/dispatcher.py` → `dispatcher_pkg/`). When you split a module, follow the same pattern.

## Contracts (`packages/shared`, `packages/sdk`)

- `packages/shared/src/api_proxy_routes.py` is the single source for how frontend `/api/*` prefixes map to backend routes.
- Files in `packages/shared/src/generated/` and `packages/sdk` are generated. Change their source and regenerate.

## Frontend (`apps/web`)

- `app/` pages are thin shells around `src/screens/*`. Domain logic lives in `src/features/<domain>`, and shared pieces live in `src/components`, `src/hooks` and `src/lib`.
- Most requests go browser → `app/api/[...path]` (same-origin proxy) → FastAPI.
- State ownership:

| State | Home | Why |
| --- | --- | --- |
| Server data | React Query (`useQuery` / `useMutation`) | A single cache means data isn't duplicated and invalidation stays consistent. Avoid copying it into Zustand or `useState`. |
| UI state (modals, sidebars, toasts, theme) | Zustand `useUIStore` (`src/store/uiStore.ts`) | Components can read it without providers or unnecessary re-renders. |
| Context that must wrap a subtree | React Context (`ProviderContext`, `useContrastMode`) | Use only when Zustand can't model it. |

- Query keys live in `src/lib/query-keys.ts`, so cache invalidation can be found and refactored.
- API calls go through `apiClient` (`@/lib/api`), which handles auth, CSRF, retry and error handling. `make check-api-calls` validates the paths **(enforced)**.
- Auth: Supabase owns the session and there is no auth store. Read auth via `useAuthSession()` (React Query, `queryKeys.authValidate`, populated by `bootstrapAuthSession` in `src/lib/auth-state.ts`). `proxy.ts` guards protected and admin routes on the server.
- Styling: Tailwind or CVA (`src/lib/cva-factory.ts`). Inline `style=` fails lint **(enforced)**.

## Tech debt

The canonical inventory is `docs/tech-debt-report.md`. Architecture decisions live in `docs/decisions/`, and `TECH_DEBT_REDUCTION_PLAN.md` there is historical. Known hotspots:

- Existing boundary violations are recorded in the debt report: routes importing storage, and provider leakage across capabilities. The gates only block **new** violations.
- `providers/dispatcher.py` is large and is being decomposed into `dispatcher_pkg/` (see `docs/decisions/2026-06-20-dispatcher-decomposition.md`).
- Residual `as any` casts remain in the web app.
- Some modules are duplicated or near-duplicates, such as `attestation/`, the extensionless `attestation_` file, `attestation_service.py` and `attestation_webhook*`, and there are other legacy aliases. Before building on one, check which is live.

How to handle debt:

- **Fix it opportunistically, in the same diff.** When a change touches a hotspot, improve the part you're touching. Don't open standalone cleanup or "hardening" PRs.
- **Don't make it worse.** New code should meet the boundaries even when neighboring code doesn't, and should not copy a legacy pattern just because it's nearby.
- **Keep scope honest.** If a fix would spread well beyond the task, leave it, note it in your summary, and suggest adding it to the debt report.
- These are settled decisions, so don't reopen them unprompted:
  - No more docs-automation tooling.
  - No new Celery workers or queues.
  - ForgeTM stays deprioritized.

## Git / CI

- Branches: `feature|fix|refactor|infra/<name>`. Commit subjects follow Conventional Commits (`feat(scope): ...`) **(enforced)**.
- Merge gates: lint, contract drift, coverage (API ≥ 80%), and no new API import cycles.
- The pre-commit hook runs Ruff on staged API files, runs lint-staged on web files, and blocks committed SQLite DBs.
