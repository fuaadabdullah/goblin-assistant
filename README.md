# Goblin Assistant Monorepo

Goblin Assistant is organized as a monorepo for clearer ownership and faster developer/agent navigation.

## Workspace Layout

- `apps/web`: Next.js Pages Router frontend
- `apps/api`: FastAPI backend (packaged Python `src/` layout)
- `packages/shared`: shared types/contracts for cross-app use
- `docs`: project documentation and runbooks

## Canonical Entrypoints

- Web dev: `pnpm --filter @goblin/web dev`
- API dev: `cd apps/api && PYTHONPATH=src uvicorn api.main:app --reload --port 8001`
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

## Test Commands

```bash
make test-web
make test-api
make test-e2e
make test-integration
make test-contract
make test-performance
make sdk-generate
```
