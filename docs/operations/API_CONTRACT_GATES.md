# API Contract Gates

This repository treats the live FastAPI schema as the source API contract and
the checked-in OpenAPI, route, and SDK files as generated snapshots.

## Ownership Chain

```text
FastAPI app schema
    |
    v
tooling/generators/export-openapi.py
    |
    v
packages/sdk/openapi/openapi.json
    |
    v
tooling/generators/generate-sdk-client.sh
    |
    v
packages/sdk/src/generated/*
```

Route snapshots and frontend proxy route contracts are generated in the same
`make sdk-generate` pass from the live FastAPI app.

## Canonical Artifacts

- `packages/sdk/openapi/openapi.json`
- `packages/sdk/openapi/routes.json`

These files are generated from the live FastAPI app and committed to git so CI
can detect drift.

## Local Commands

- `make sdk-generate` regenerates OpenAPI, the route manifest, the SDK types,
  the generated route inventory, and the shared API proxy spec.
- `make sdk-check` fails if any generated contract artifact is stale.
- `make check-api-calls` fails if frontend API path literals do not match the
  checked-in manifest-derived proxy spec or the explicit browser-only
  exceptions.
- `make contract-checks` runs both contract gates together.
- `make test-api-coverage` and `make test-web-coverage` run the merge-blocking
  backend and frontend coverage gates.

## CI Behavior

GitHub Actions now treats `lint`, `contract`, `test-backend`, and
`test-frontend` as the required pre-merge gate set. The `merge-gates` job fails
if any of those checks fail or are skipped.

`test-backend` runs `make test-api-coverage`; `test-frontend` runs
`make test-web-coverage`. The contract job runs `make contract-checks`, so CI
and local developer checks use the same entrypoint.

Operational policy checks are part of `make lint-policy`, which runs in both
GitHub Actions and CircleCI. The check keeps the hybrid CI/deploy model honest:
GitHub owns repository guardrails, CircleCI owns the heavy build/test/deploy
workflow, Render remains the canonical backend target, Fly.io remains archived,
and dependency update automation must stay configured.
If the regenerated OpenAPI schema or route manifest differs from the checked-in
files, CI fails immediately.

CI must never hand-edit generated SDK/OpenAPI output to quiet a diff. Regenerate
from the live FastAPI app, review the source route/schema change, and commit the
resulting generated artifacts together.

If the frontend introduces an API path that is not represented by the
manifest-derived proxy spec or one of the explicit browser-only handlers, CI
also fails.

## Notes

- We do not maintain a separate `route_manifest.txt` snapshot layer.
- The route manifest export stays deterministic by sorting the collected
  route/method pairs before writing the JSON snapshot.
- The generated route inventory in `docs/backend/API_ROUTE_INVENTORY.generated.md`
  is derived from the same snapshots and should be regenerated together with the
  contract artifacts.
- The settings-route compatibility burn-down list lives in
  `docs/operations/API_ROUTE_MIGRATION_TRACKER.md`.
