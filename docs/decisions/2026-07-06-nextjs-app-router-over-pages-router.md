# ADR-0001: Next.js App Router Over Pages Router

## Status
accepted

## Date
2026-07-06

## Context
The frontend already ships as a Next.js App Router application under `apps/web/app/`, with layouts, middleware, and route handlers built around that model. Reintroducing the Pages Router would split routing ownership, duplicate route guard behavior, and make the browser shell harder to reason about.

## Decision
Use the Next.js App Router as the only supported frontend routing model.

- New frontend routes, layouts, and route handlers belong in `apps/web/app/`.
- Shared feature code continues to live in `apps/web/src/`.
- Pages Router files are not part of the supported architecture going forward.

## Consequences
- Route composition stays aligned with App Router semantics and middleware.
- The browser shell can continue to use nested layouts and route handlers without dual routing conventions.
- Legacy Pages Router patterns are treated as dead code unless a separate compatibility decision says otherwise.

## Operational Notes
- Related ADRs: ADR-0002, ADR-0003.
- If a future feature appears to require Pages Router, the requirement should be justified in a separate ADR before adding files under a `pages/` tree.
- Architecture docs should refer to this ADR rather than restating the routing rationale.
