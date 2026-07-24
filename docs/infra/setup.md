# Setup

This setup guide reflects the current repository layout:

- frontend: Next.js App Router app in `apps/web/app/` with shared modules in `apps/web/src/`
- backend: FastAPI app in `apps/api/src/api/`

## Prerequisites

- Node.js 18+
- pnpm
- Docker Desktop or Docker Engine

Optional for full native backend development:

- Redis
- Python 3.11+

## Install Dependencies

### Daily Driver Path

Use this path for the dogfood ritual and routine frontend work. It keeps the
backend in Docker so local Python package compilation does not gate the day.

From the repo root:

```bash
make install-web
docker compose build --no-cache goblin-assistant-backend
make api-docker-up
make web-dev
```

Verify the backend before opening the frontend:

```bash
curl http://127.0.0.1:8001/health
```

Use `make api-docker-down` to stop the backend stack when you are done.

### Full Native Development

From the repo root:

```bash
make install
```

`make install` remains the full native development path. It installs the backend
Python dependency set from `apps/api/requirements.txt` and
`apps/api/requirements-vector.txt`, which may require local build tooling that is
not needed for the Docker-first workflow.

## Environment

The safest local setup is a repo-root `.env.local`, because `apps/api/src/api/main.py` explicitly loads `.env.local` and `.env` from the project root.

### Minimal `.env.local`

```bash
JWT_SECRET_KEY=replace-me-with-a-random-secret
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8001
BACKEND_URL=http://127.0.0.1:8001
```

Why these matter:

- `JWT_SECRET_KEY`: required at import time by `api/auth/router.py`
- `NEXT_PUBLIC_API_BASE_URL`: used by the frontend HTTP clients for backend calls
- `BACKEND_URL`: used by Next API proxy routes such as `apps/web/app/api/generate/route.ts`

### Common frontend env vars

Defined in `apps/web/src/config/env.ts`:

- `NEXT_PUBLIC_BACKEND_URL`
- `NEXT_PUBLIC_FASTAPI_URL`
- `NEXT_PUBLIC_ENABLE_DEBUG`
- `NEXT_PUBLIC_MOCK_API`
- `NEXT_PUBLIC_FEATURE_RAG_ENABLED`
- `NEXT_PUBLIC_FEATURE_MULTI_PROVIDER`
- `NEXT_PUBLIC_FEATURE_PASSKEY_AUTH`
- `NEXT_PUBLIC_FEATURE_GOOGLE_AUTH`
- `NEXT_PUBLIC_FEATURE_ORCHESTRATION`
- `NEXT_PUBLIC_FEATURE_SANDBOX`
- `NEXT_PUBLIC_FEATURE_SEARCH`
- `NEXT_PUBLIC_FEATURE_ADMIN`
- `NEXT_PUBLIC_ENABLE_ANALYTICS`
- `NEXT_PUBLIC_DEBUG_MODE`
- `NEXT_PUBLIC_TURNSTILE_SITE_KEY_CHAT`
- `NEXT_PUBLIC_TURNSTILE_SITE_KEY_LOGIN`
- `NEXT_PUBLIC_TURNSTILE_SITE_KEY_SEARCH`
- `NEXT_PUBLIC_SENTRY_DSN`
- `NEXT_PUBLIC_GA_MEASUREMENT_ID`

### Common backend env vars

Used across `apps/api/src/api/main.py`, auth, sandbox, and provider/config modules:

- `ENVIRONMENT`
- `ALLOWED_ORIGINS`
- `REDIS_URL`
- `SENTRY_DSN`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `OPENROUTER_API_KEY`
- `TOGETHER_API_KEY`
- `SILICONEFLOW_API_KEY`
- `DEEPINFRA_API_KEY`
- `AZURE_API_KEY`
- `OLLAMA_GCP_URL`
- `LLAMACPP_GCP_URL`
- `SANDBOX_ENABLED`
- `SANDBOX_IMAGE`
- `API_AUTH_KEY`

## Run Locally

Backend, Docker-first:

```bash
make api-docker-up
```

Backend, native:

```bash
cd apps/api && PYTHONPATH=src uvicorn api.main:app --reload --port 8001
```

Frontend:

```bash
make web-dev
```

Open:

- frontend: `http://127.0.0.1:3000`
- backend docs: `http://127.0.0.1:8001/docs`
- backend health: `http://127.0.0.1:8001/health`

If `curl /health` fails in the Docker-first path, treat that as an environment
block for the dogfood run. Log the bailout, stop there, and do not use the day
to fix unrelated product behavior.

## What Works Best Locally

Most reliable in the current checkout:

- `/api/generate` prompt proxy
- backend `/health`
- backend `/chat/conversations*`

Currently requires additional contract alignment before it is reliable against the checked-in `api/` app:

- login/register from the Next.js frontend
- provider registry/admin screens
- search screen
- sandbox screen
- account preference saving
- help/support submission

Those areas depend on the checked-in `/api/v1/...` contract surfaces and the thin proxy routes in `apps/web/app/api/`.
