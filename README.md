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
# Use Node 20.x (CI baseline) or 22.x before installing dependencies.
# Example with nvm:
# nvm use 20

pnpm install
cd apps/api && python3.11 -m pip install -r requirements.txt -r requirements-vector.txt
```

### Provider Keys (first-time setup)

Run the interactive bootstrap to set all provider API keys at once:

```bash
python scripts/bootstrap-env.py          # prompts for each key, writes .env
python scripts/bootstrap-env.py --bw     # pull keys from Bitwarden vault
python scripts/bootstrap-env.py --check  # fail if a required value is missing
```

For dogfooding, configure at least one primary provider: `OPENAI_API_KEY` or
`ANTHROPIC_API_KEY`. The chat smoke automatically selects a healthy configured
one. GCP LLM endpoints were removed (VMs terminated 2026-01-11).

### Smoke Tests

```bash
# Auth flow: register → login → refresh → logout → login
make smoke-auth

# Chat E2E: proxy → backend → LLM → response
make smoke-chat
```

For viewport testing (mobile/tablet), see
[`docs/runbooks/VIEWPORT_TESTING.md`](docs/runbooks/VIEWPORT_TESTING.md).

For the sandbox/celery feature gate decision, see
[`docs/decisions/SANDBOX_CELERY_FEATURE_GATE.md`](docs/decisions/SANDBOX_CELERY_FEATURE_GATE.md).

### External USB Drive I/O Workaround

If the repository lives on an external USB drive, Next.js `.next` cache
compaction can take **20+ minutes** due to slow USB I/O.  Redirect the cache
to the faster internal disk with a symlink:

```bash
# One-time setup — symlink .next to the internal /tmp
ln -s /tmp/nextcache apps/web/.next
```

After symlinking, `next dev` compiles in ~43s on first request and ~107ms on
subsequent requests (acceptable for local dev).

> **Note:** `make web-dev` runs `next dev --webpack -p 3000` by
> default because the Turbopack RocksDB cache corrupts after restarts,
> causing the dev server to lock up (TCP connects but HTTP never responds).

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
- documentation and API lifecycle policy live in `docs/architecture/DOCUMENTATION_ARCHITECTURE_RFC.md`,
  `docs/architecture/API_COMPATIBILITY_LIFECYCLE.md`, and `docs/decisions/`

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

For the canonical API contract snapshots and CI gates, see
[`docs/operations/API_CONTRACT_GATES.md`](docs/operations/API_CONTRACT_GATES.md).
