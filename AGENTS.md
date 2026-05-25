# AGENTS Map

This file is the canonical task map for coding agents and developers.

## Where To Edit

- Frontend features/pages/components: `apps/web/src`
- Next API proxy routes: `apps/web/pages/api`
- Backend API routes/services/providers: `apps/api/src/api`
- Shared contracts/types: `packages/shared`
- Infra/deploy scripts: `scripts`, `.github/workflows`, `docker-compose.yml`, `render.yaml`

## Where To Run

- Install deps: `make install`
- Web dev: `make web-dev`
- API dev: `make api-dev`
- Lint/typecheck: `make lint` / `make type-check`
- Web tests: `make test-web`
- API tests: `make test-api`
- E2E tests: `make test-e2e`

## Where To Verify

- Backend health: `curl http://127.0.0.1:8001/health`
- Frontend health proxy: `curl http://127.0.0.1:3000/api/health`
- CI config: `.github/workflows/ci.yml`

## Rules Of Thumb

- Keep app-local code inside its owning app directory.
- Put cross-app contracts in `packages/shared`.
- Prefer root Makefile and root package scripts for reproducible command entrypoints.
- Follow `docs/PURE_FUNCTIONS_AND_NAMING_POLICY.md` for pure-by-default side-effect boundaries and intent naming.
- Follow `docs/API_AND_FRONTEND_STANDARDS.md` for orchestration-ready interfaces/events/contracts/observability.
- Document architecture and operational assumptions in ADRs/runbooks rather than trivial code commentary.
