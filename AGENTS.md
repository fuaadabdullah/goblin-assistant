# AGENTS Map

This file is the canonical task map for coding agents and developers.

## Where To Edit

- Frontend features/pages/components: `apps/web/src`
- Next API proxy routes: `apps/web/app/api`
- Backend API routes/services/providers: `apps/api/src/api`
- Shared contracts/types: `packages/*` (use `packages/shared` for cross-app contracts)
- Infra/deploy/runtime scripts: `scripts`, `.github/workflows`, `docker-compose.yml`, `render.yaml`
- Non-runtime repo tooling: `tooling/*` (`codemods`, `generators`, `automation`, `quality`)

## Where To Run

- Install deps: `make install`
- Web dev: `make web-dev`
- API dev: `make api-dev`
- Lint/typecheck: `make lint` / `make type-check`
- Web tests: `make test-web`
- API tests: `make test-api`
- E2E tests: `make test-e2e`
- Test strategy buckets: `make test-integration`, `make test-contract`, `make test-performance`
- SDK generation: `make sdk-generate` / `make sdk-check`
- Route manifest export: `make generate-route-manifest`
- Contract drift checks: `make contract-checks`

## Where To Verify

- Backend health: `curl http://127.0.0.1:8001/health`
- Frontend health proxy: `curl http://127.0.0.1:3000/api/health`
- Contract artifacts: `make sdk-check` and `make contract-checks`
- CI config: `.github/workflows/ci.yml`

## Rules Of Thumb

- Keep app-local code inside its owning app directory.
- Put cross-app code in `packages/*` and keep contracts/types in `packages/shared`.
- Do not create root-level `src/`; shared code must live under `packages/*`.
- Prefer root Makefile and root package scripts for reproducible command entrypoints.
- Follow `docs/architecture/PURE_FUNCTIONS_AND_NAMING_POLICY.md` for pure-by-default side-effect boundaries and intent naming.
- Follow `docs/architecture/API_AND_FRONTEND_STANDARDS.md` for orchestration-ready interfaces/events/contracts/observability.
- Document architecture and operational assumptions in `docs/decisions/` and `docs/operations/` rather than trivial code commentary.
- **Refactor opportunistically, not by initiative.** Known tech-debt hotspots (e.g. fat `ProviderDispatcher`, fat `SettingsPage.tsx`, the 52 `as any` casts across the web app) are real but non-blocking. Clean them up when you are already in that file for an unrelated change. Do **not** open a dedicated "type-hardening pass" or "settings refactor" PR — that is procrastination in a nice suit. Each opportunistic fix should land in the same diff as the feature/bug that surfaced it.
- **No more docs automation.** The drift gate works. We are past the point of diminishing returns on tooling that generates/validates/lints prose. Don't add more.
- **Don't add Celery workers or priority queues.** Three worker pools at solo-dev scale is infrastructure cosplay. It won't hurt you today; just don't add to it.
- **ForgeTM stays deprioritized.** The call to deprioritize it was made for good reason. Don't quietly revive it as a side quest.
