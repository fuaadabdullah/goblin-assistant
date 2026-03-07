# Setup

This setup guide reflects the current repository layout:

- frontend: Next.js app in `src/`
- backend: FastAPI app in `api/`

## Prerequisites

- Node.js 18+
- npm
- Python 3.11+

Optional for broader backend coverage:

- Redis
- Docker

## Install Dependencies

From the app root:

```bash
cd apps/goblin-assistant
npm install
python3 -m pip install -r requirements.txt
```

`requirements.txt` is the broader backend dependency set. There is also `api/requirements.txt`, but the root file is the safer choice for the current backend.

## Environment

The safest local setup is a repo-root `.env.local`, because `api/main.py` explicitly loads `.env.local` and `.env` from the project root.

### Minimal `.env.local`

```bash
JWT_SECRET_KEY=replace-me-with-a-random-secret
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8001
BACKEND_URL=http://127.0.0.1:8001
```

Why these matter:

- `JWT_SECRET_KEY`: required at import time by `api/auth/router.py`
- `NEXT_PUBLIC_API_BASE_URL`: used by the frontend HTTP clients for backend calls
- `BACKEND_URL`: used by Next API proxy routes such as `src/pages/api/generate.ts`

### Common frontend env vars

Defined in `src/config/env.ts`:

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

Used across `api/main.py`, auth, sandbox, and provider/config modules:

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

Backend:

```bash
uvicorn api.main:app --reload --port 8001
```

Frontend:

```bash
npm run dev
```

Open:

- frontend: `http://127.0.0.1:3000`
- backend docs: `http://127.0.0.1:8001/docs`
- backend health: `http://127.0.0.1:8001/health`

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

Those areas mostly depend on `/v1/...` endpoints or payload shapes that do not match the local FastAPI routers.
