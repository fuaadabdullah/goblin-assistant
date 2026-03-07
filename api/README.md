# Goblin Assistant FastAPI Backend

This directory contains the checked-in FastAPI backend used by the `goblin-assistant` app.

## Entry Point

- App module: `main.py`
- Dev command from repo root:

```bash
uvicorn api.main:app --reload --port 8001
```

If you `cd api`, use:

```bash
uvicorn main:app --reload --port 8001
```

## Required Environment

Minimum for startup:

```bash
JWT_SECRET_KEY=replace-me
```

Common additional env vars:

- `ENVIRONMENT`
- `ALLOWED_ORIGINS`
- `REDIS_URL`
- `SENTRY_DSN`
- provider keys such as `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`, `TOGETHER_API_KEY`, `SILICONEFLOW_API_KEY`

## Route Groups In `api/main.py`

Mounted route prefixes in the current app:

- `/api`
- `/auth`
- `/routing`
- `/execute`
- `/parse`
- `/raptor`
- `/chat`
- `/health`
- `/ops`
- `/search`
- `/settings`
- `/secrets`
- `/sandbox`
- `/api/privacy`
- `/debug`

OpenAPI docs come from FastAPI at `/docs` and `/openapi.json`.

## Important Note About Versioning

The checked-in backend mounts mostly unversioned routes.

The frontend and some proxy handlers still expect `/v1/...` endpoints for auth, provider registry, search, sandbox, and other flows. Those `/v1` aliases are not defined in `main.py`.

That means:

- backend chat and health routes are the safest local surfaces
- several frontend modules require contract alignment before they work against this local FastAPI app

## What Is Implemented Here

- JWT auth, Google OAuth helpers, CSRF token issuance, passkey routes
- conversation CRUD and message send flows
- contextual/semantic chat helpers
- routing/orchestration endpoints
- health, ops, observability, privacy, and secrets endpoints
- sandbox job APIs with Redis/RQ-backed execution model

## What To Read Next

- `docs/README.md`: route inventory and current API notes
- `../docs/ARCHITECTURE_OVERVIEW.md`: how the frontend talks to this backend
