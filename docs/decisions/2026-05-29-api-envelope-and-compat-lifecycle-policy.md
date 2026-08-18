# API Envelope and Compatibility Lifecycle Policy

## Status
accepted

## Context
Mixed response shapes and unmanaged migration paths make frontend/runtime integrations fragile during incremental API evolution.

## Decision
Adopt and enforce:
- Contract-first envelopes: success responses expose `success/data`, failures expose `success/error`.
- Versioned compatibility paths under `/api/v1` for key surfaces.
- Lifecycle classification on responses with headers:
  - `X-API-Lifecycle`: `stable|legacy|experimental|internal`
  - `Deprecation` and `Sunset` for legacy paths

## Consequences
- Consumers can migrate with explicit compatibility signals.
- Legacy routes remain available but governed by sunset policy.
- Error/response behavior becomes predictable across routers.

## Operational Notes
- Lifecycle logic is centralized in `api.core.route_lifecycle`.
- CI validates lifecycle policy with `scripts/architecture/check_route_lifecycle.py`.

## Compliance Status
- `GET /api/v1/api/goblins` — compliant as of 2026-08-18 (returns `GoblinListSuccessResponse`)
- `GET /api/v1/api/history/{goblin_id}` — compliant as of 2026-08-18 (returns `GoblinHistorySuccessResponse`)
- `GET /api/v1/api/stats/{goblin_id}` — compliant as of 2026-08-18 (returns `GoblinStatsSuccessResponse`)

Named success envelope subclasses (`Goblin*SuccessResponse`) are defined in `api.api_models`
and subclass `SuccessEnvelope[T]` from `api.core.contracts`. The frontend `unwrapEnvelope`
helper in `apps/web/src/lib/api/http-helpers.ts` transparently handles the envelope on all
`getBackend`/`getFrontend` calls, so SDK consumers receive the unwrapped payload.

