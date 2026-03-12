# Goblin Assistant

Goblin Assistant is a split Next.js + FastAPI application in `apps/goblin-assistant`.

- Frontend: Next.js Pages Router app in `src/`
- Backend: FastAPI app in `api/`
- Shared runtime/provider config: `config/providers.json`

## Canonical Deployment Targets (March 2026)

- Frontend: **Vercel**
- Backend: **Render**
- Canonical backend entrypoint: `api.main:app`

Use only these deployment scripts:

- `./deploy-vercel.sh` (frontend)
- `./deploy-render.sh` (backend)
- `./deploy.sh vercel|render|test` (wrapper)

Fly/GCP/Kamatera deploy wrappers and duplicate backend entrypoint artifacts were removed to reduce operational drift.

## Current Repo Status

The checked-in code supports these areas with matching implementation:

- Next.js pages for onboarding, startup, chat, login/register, help, account, search, sandbox, and admin
- Route protection in `middleware.ts`
- Backend conversation APIs under `/chat/*`
- Thin Next API proxy for prompt generation at `/api/generate`, which forwards to backend `/api/chat`
- FastAPI routers for auth, chat, routing, health, search, settings, privacy, secrets, ops, debug, and sandbox

### Security (March 2026)

- **CSRF Protection**: Redis-backed one-time tokens with 1-hour TTL
- **Rate Limiting**: Sliding window on auth endpoints (5 attempts/hr per IP)
- **Sentry Integration**: Privacy hooks for PII scrubbing in error reports
- **Auth Refresh**: Token exchange and revocation flows with session management
- **Memory Eviction**: TTL-based cleanup with max-size limits and user isolation

### Test Coverage

| Layer            | Suites | Tests | Status      |
|------------------|--------|-------|-------------|
| Backend (Python) | 9      | 51    | All passing |
| Frontend (Jest)  | 50+    | 278+  | All passing |

Run tests:

```bash
# Backend
source ../.venv/bin/activate
cd api && python -m pytest -o "addopts=" -v

# Frontend
TMPDIR=/tmp npx jest --no-coverage
```

### Known Caveats

- Some historical docs still mention `main:app` and `backend/main.py`; for this repo use only `api.main:app`
- Provider integrations may use external `/v1/*` upstream APIs internally, but frontend client code must use internal app routes only
- Use `npm run guard:no-client-v1` to enforce that frontend code does not call provider-style `/v1/*` paths

For the most reliable local flow in this checkout, start with chat and health endpoints.

## Quick Start

### Prerequisites

- Node.js 18+
- npm
- Python 3.11+

### Install

```bash
cd apps/goblin-assistant
npm install
python3 -m pip install -r requirements.txt
```

### Minimal local environment

Create `.env.local` in the project root:

```bash
JWT_SECRET_KEY=replace-me
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8001
BACKEND_URL=http://127.0.0.1:8001
```

Optional frontend flags used by `src/config/env.ts`:

```bash
NEXT_PUBLIC_FEATURE_SEARCH=true
NEXT_PUBLIC_FEATURE_SANDBOX=true
NEXT_PUBLIC_FEATURE_ADMIN=false
NEXT_PUBLIC_FEATURE_PASSKEY_AUTH=true
NEXT_PUBLIC_FEATURE_GOOGLE_AUTH=true
NEXT_PUBLIC_TURNSTILE_SITE_KEY_LOGIN=
NEXT_PUBLIC_TURNSTILE_SITE_KEY_CHAT=
NEXT_PUBLIC_TURNSTILE_SITE_KEY_SEARCH=
```

### Run

Backend:

```bash
uvicorn api.main:app --reload --port 8001
```

Frontend:

```bash
npm run dev
```

### Verify

```bash
curl http://127.0.0.1:8001/health
curl http://127.0.0.1:3000/api/health
```

Open `http://127.0.0.1:3000`.

## Documentation

- `docs/README.md`: app-level docs index and canonical docs list
- `docs/setup.md`: local setup and env configuration
- `docs/features.md`: feature status by capability
- `docs/ARCHITECTURE_OVERVIEW.md`: current frontend/backend topology
- `DEPLOYMENT_AND_TESTING.md`: deployment procedures and test strategy
- `SECURITY_IMPLEMENTATION_COMPLETE.md`: security feature details
- `api/README.md`: FastAPI backend entry guide
- `api/docs/README.md`: route inventory and API behavior notes

## Notes

- The frontend is a Next.js Pages Router app, not a Vite app.
- The backend entrypoint in this repo is `api/main.py`, not `backend/main.py`.
- Older docs in this repository include historical planning and migration notes. Treat the files listed above as the canonical starting points.
