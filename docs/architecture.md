# Architecture

This document is the longer companion to `ARCHITECTURE_OVERVIEW.md`.

## Application Shape

The repository currently contains:

- a Next.js Pages Router frontend
- a FastAPI backend
- a few Next API proxy routes

It does not match the older `backend/`-based architecture described in some historical docs.

## Frontend

The frontend lives in `src/`.

Important parts:

- route files in `src/pages/`
- feature modules in `src/features/`
- auth/bootstrap state in `src/store/authStore.ts`
- cookie/local-storage session persistence in `src/utils/auth-session.ts`
- route protection in `middleware.ts`

Current pages include:

- `/`
- `/startup`
- `/chat`
- `/login`
- `/register`
- `/search`
- `/sandbox`
- `/account`
- `/settings`
- `/help`
- `/admin`, `/admin/providers`, `/admin/logs`, `/admin/settings`

## Backend

The backend lives in `api/`.

The FastAPI app in `api/main.py` wires together:

- middleware for errors, security headers, auth gating, CORS, and optional rate limiting
- routers for chat, auth, routing, health, search, privacy, secrets, ops, observability, and sandbox
- startup/shutdown tasks for Redis, database init, provider monitoring, and artifact cleanup

## Thin Proxy Routes

The frontend also ships a few Next API routes:

- `src/pages/api/generate.ts`
- `src/pages/api/models.ts`
- `src/pages/api/auth/validate.ts`
- `src/pages/api/health.ts`

Only `/api/generate` is clearly aligned with a route that exists in the checked-in FastAPI app. The other proxy routes expect `/v1/...` backend endpoints that are not mounted by `api/main.py`.

## Best-Supported Flow

The cleanest end-to-end path in this repo is chat:

1. user opens `/chat`
2. frontend bootstraps auth/session state
3. thread APIs call backend `/chat/conversations*`
4. prompt generation can also go through `/api/generate` -> backend `/api/chat`
5. provider/model metadata is attached to assistant messages when available

## Partial Areas

These areas exist in code but are not fully contract-aligned:

- auth from the frontend
- provider registry/admin tools
- search
- sandbox
- account save endpoints
- support form submission

For those areas, the architecture problem is mostly not missing UI. It is mismatched route versioning and differing request/response shapes between `src/api/apiClient.ts` and the FastAPI routers.
