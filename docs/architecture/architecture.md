# Architecture

This document is the longer companion to `ARCHITECTURE_OVERVIEW.md`.

## Application Shape

The repository currently contains:

- a Next.js App Router frontend
- shared feature modules and SDK consumers in `apps/web/src/`
- one shared Next API catch-all proxy route in `apps/web/app/api/[...path]/route.ts`
- a small set of explicit browser-only Next API handlers in `apps/web/app/api/`
- a FastAPI backend

The App Router and proxy-layer decisions are documented in [ADR-0001](../decisions/2026-07-06-nextjs-app-router-over-pages-router.md) and [ADR-0003](../decisions/2026-07-06-nextjs-proxies-vs-direct.md).

It does not match the older `backend/`-based architecture described in some historical docs.

## Frontend

The frontend lives in `apps/web/src/`.

Important parts:

- route files in `apps/web/app/`
- feature modules in `apps/web/src/features/`
- auth/bootstrap state in `apps/web/src/store/authStore.ts`
- cookie/local-storage session persistence in `apps/web/src/utils/auth-session.ts`
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

The backend lives in `apps/api/src/api/`.

The FastAPI app in `apps/api/src/api/main.py` wires together:

- middleware for errors, security headers, auth gating, CORS, and optional rate limiting
- routers for chat, auth, routing, health, search, privacy, secrets, ops, observability, and sandbox
- startup/shutdown tasks for Redis, database init, provider monitoring, and artifact cleanup

## Shared Proxy Route

The frontend ships one generated catch-all proxy route plus a small set of explicit browser-only Next API handlers:

- `apps/web/app/api/[...path]/route.ts`
- `apps/web/app/api/generate/route.ts`
- `apps/web/app/api/models/route.ts`
- `apps/web/app/api/auth/validate/route.ts`
- `apps/web/app/api/health/route.ts`
- `apps/web/app/api/auth/google/callback/route.ts`
- `apps/web/app/api/debug/model-usage/route.ts`
- `apps/web/app/api/system-status/route.ts`
- `apps/web/app/api/errors/route.ts`

The shared catch-all resolves manifest-derived backend prefixes through the generated proxy spec, while `apps/web/proxy.ts` stays the auth and redirect seam. Most frontend code skips these handlers and calls the FastAPI app directly under `/api/v1/...` through the configured backend origin.

## Best-Supported Flow

The cleanest end-to-end path in this repo is chat:

1. user opens `/chat`
2. frontend bootstraps auth/session state
3. thread APIs call backend `/api/v1/chat/conversations*`
4. prompt generation can also go through `/api/generate` -> backend `/api/v1/api/chat`
5. provider/model metadata is attached to assistant messages when available

## Partial Areas

These areas now exist in code and should be treated as contract surfaces rather than roadmap items:

- auth from the frontend
- provider registry/admin tools
- search
- sandbox
- account save endpoints
- support form submission

For those areas, the architecture concern is keeping the generated proxy spec, explicit browser-only handlers, backend versioned routes, and generated contract artifacts synchronized.

The versioning rationale lives in [ADR-0002](../decisions/2026-07-06-api-versioning-v1-contract.md).
