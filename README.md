# Goblin Assistant Monorepo

Goblin Assistant is organized as a monorepo for clearer ownership and faster developer/agent navigation.

## Workspace Layout

- `apps/web`: Next.js App Router frontend (`apps/web/app/` plus shared UI/state in `apps/web/src/`)
- `apps/web/app/api`: thin same-origin proxy routes for browser-safe calls
- `apps/api`: FastAPI backend (packaged Python `src/` layout)
- `packages/shared`: shared types/contracts for cross-app use
- `docs`: project documentation and runbooks

## Canonical Entrypoints

- Web dev: `make web-dev` or `pnpm --filter @goblin/web dev`
- API dev: `make api-dev` or `cd apps/api && PYTHONPATH=src uvicorn api.main:app --reload --port 8001`
- Contract generation: `make sdk-generate` or `make generate-route-manifest`
- Contract checks: `make sdk-check` or `make contract-checks`
- Root orchestrator: `Makefile`
- Agent/developer task map: `AGENTS.md`

## Quick Start

```bash
pnpm install
cd apps/api && python3 -m pip install -r requirements.txt
```

Run services:

```bash
# terminal 1
make web-dev

# terminal 2
make api-dev
```

Smoke checks:

```bash
curl http://127.0.0.1:8001/health
curl http://127.0.0.1:3000/api/health
```

The frontend uses a hybrid request model:

- `apps/web/app/api/*` handles a few browser-safe proxy endpoints such as `/api/generate`, `/api/models`, `/api/auth/validate`, and `/api/health`
- most frontend data access calls the FastAPI backend directly under `/api/v1/...`
- the backend also keeps a small set of legacy aliases such as `/settings` for compatibility

## Test Commands

```bash
make test-web
make test-api
make test-e2e
make test-integration
make test-contract
make test-performance
make sdk-generate
make contract-checks
```
