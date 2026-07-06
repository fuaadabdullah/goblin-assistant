# ADR-0002: API Versioning and the `/api/v1` Contract

## Status
accepted

## Date
2026-07-06

## Context
The backend exposes a large public API surface, and the repo already checks in a route manifest plus OpenAPI snapshot as contract artifacts. A versioned primary mount keeps that surface stable while allowing compatibility aliases to exist only where migration still needs them.

## Decision
Treat `/api/v1` as the canonical public API mount for versioned backend routes.

- New or migrated backend consumers should target `/api/v1/...`.
- Compatibility aliases may exist temporarily for migration, but they are not the preferred contract.
- Checked-in OpenAPI and route-manifest artifacts remain the source of truth for route inventory and drift detection.

## Consequences
- Client code can depend on a stable versioned prefix.
- Legacy aliases remain explicit and reviewable instead of being ad hoc.
- Contract checks can compare the live app against the checked-in snapshots without guessing which paths are canonical.

## Operational Notes
- Related ADRs: ADR-0001, ADR-0003, ADR-0004.
- Removing a legacy alias requires updating the migration tracker, regenerating contract artifacts, and refreshing the route-alias tests.
- Frontend API helpers should continue to use the shared `V1_API_PREFIX` constant rather than hardcoding paths.
