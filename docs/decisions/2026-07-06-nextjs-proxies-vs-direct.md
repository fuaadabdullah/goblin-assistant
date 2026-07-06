# ADR-0003: Thin Next.js Proxies vs Direct Backend Calls

## Status
accepted

## Date
2026-07-06

## Context
The frontend needs a browser-safe way to call a few backend endpoints from the same origin, but most product logic already lives in shared frontend API helpers that can call the FastAPI app directly. If the Next.js layer starts owning real business logic, the frontend/backend boundary becomes harder to maintain and test.

## Decision
Keep the Next.js `app/api` layer intentionally thin.

- Proxy routes exist only where same-origin browser access or auth/bootstrap flow needs them.
- The Next layer forwards requests rather than re-implementing backend behavior.
- Business rules, persistence, and contract validation stay in the FastAPI backend and shared client helpers.

## Consequences
- Browser-only convenience routes can stay available without becoming a second backend.
- The backend remains the source of truth for API shapes and persistence behavior.
- New proxy routes should be added sparingly and only when a browser/runtime constraint requires them.

## Operational Notes
- Related ADRs: ADR-0001, ADR-0002, ADR-0004.
- Existing proxy routes should be audited before adding any new one.
- If a proxy begins accumulating logic, that logic should be pushed back into the backend or a shared client helper.
