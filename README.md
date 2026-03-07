# Goblin Assistant

Goblin Assistant is a split Next.js + FastAPI application in `apps/goblin-assistant`.

- Frontend: Next.js Pages Router app in `src/`
- Backend: FastAPI app in `api/`
- Shared runtime/provider config: `config/providers.json`

## Current Repo Status

The checked-in code supports these areas with matching implementation:

- Next.js pages for onboarding, startup, chat, login/register, help, account, search, sandbox, and admin
- Route protection in `middleware.ts`
- Backend conversation APIs under `/chat/*`
- Thin Next API proxy for prompt generation at `/api/generate`, which forwards to backend `/api/chat`
- FastAPI routers for auth, chat, routing, health, search, settings, privacy, secrets, ops, debug, and sandbox

The repo also contains UI/features that are present in code but not fully aligned end to end:

- Much of the frontend client calls `/v1/...`, while `api/main.py` mounts most routers at unversioned paths such as `/auth`, `/chat`, `/search`, `/settings`, and `/sandbox`
- `src/pages/api/models.ts` expects a backend `/v1/providers/models` endpoint that is not defined in the checked-in FastAPI app
- Search, sandbox, provider admin, account save, and support form flows currently expect backend contracts that do not match the local `api/` implementation

If you want the most reliable local flow in this checkout, start with chat and health endpoints.

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
- `api/README.md`: FastAPI backend entry guide
- `api/docs/README.md`: route inventory and API behavior notes

## Notes

- The frontend is a Next.js Pages Router app, not a Vite app.
- The backend entrypoint in this repo is `api/main.py`, not `backend/main.py`.
- Older docs in this repository include historical planning and migration notes. Treat the files listed above as the canonical starting points.
