# Router Decomposition

## Status
accepted

## Context
The API router surface had grown into a mixed responsibility module that combined request handling, stream orchestration, history assembly, and legacy compatibility seams. That made it harder to evolve route logic without coupling unrelated behavior together.

## Decision
Keep `apps/api/src/api/api_router.py` as the compatibility-facing router entrypoint, but move reusable routing helpers into `apps/api/src/api/api_router_pkg/`.

The decomposition rules are:
- route handlers stay in the top-level router module so the public import surface remains stable;
- shared stream/history/text helpers move into package-local modules;
- legacy import and monkeypatch seams remain available from `api.api_router`;
- background task execution and sort/extract helpers are implemented behind package boundaries instead of duplicated inline.

## Consequences
- Route behavior can evolve without making the top-level router harder to read or test.
- Existing imports that target `api.api_router` continue to work.
- Helper logic can be reused by tests and future route modules without copying orchestration code.

## Operational Notes
- The canonical router package is `api.api_router_pkg`.
- Compatibility-sensitive tests should keep patching `api.api_router` unless they explicitly exercise the package helpers.
- Route additions should prefer helper extraction before adding more inline orchestration to the router module.
