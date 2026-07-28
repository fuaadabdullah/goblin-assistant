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

