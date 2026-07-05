# API Contract Gates

This repository treats the checked-in OpenAPI schema and route manifest as the
canonical API contract snapshots.

## Canonical Artifacts

- `packages/sdk/openapi/openapi.json`
- `packages/sdk/openapi/routes.json`

These files are generated from the live FastAPI app and committed to git so CI
can detect drift.

## Local Commands

- `make sdk-generate` regenerates OpenAPI, the route manifest, the SDK types,
  and the generated route inventory.
- `make sdk-check` fails if any generated contract artifact is stale.
- `make check-api-calls` fails if frontend API path literals do not match the
  checked-in manifest or the Next proxy routes.
- `make contract-checks` runs both contract gates together.

## CI Behavior

The GitHub Actions contract job runs `make contract-checks`, so CI and local
developer checks use the same entrypoint.
If the regenerated OpenAPI schema or route manifest differs from the checked-in
files, CI fails immediately.

If the frontend introduces an API path that is not represented by the manifest
or a proxy route, CI also fails.

## Notes

- We do not maintain a separate `route_manifest.txt` snapshot layer.
- The route manifest export stays deterministic by sorting the collected
  route/method pairs before writing the JSON snapshot.
- The generated route inventory in `docs/backend/API_ROUTE_INVENTORY.generated.md`
  is derived from the same snapshots and should be regenerated together with the
  contract artifacts.
- The settings-route compatibility burn-down list lives in
  `docs/operations/API_ROUTE_MIGRATION_TRACKER.md`.
