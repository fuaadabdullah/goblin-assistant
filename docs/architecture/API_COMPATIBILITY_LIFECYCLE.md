# API Compatibility Lifecycle

Goblin Assistant uses an incremental compatibility model for API evolution.

The versioned-mount policy that makes this work is documented in [ADR-0002](../decisions/2026-07-06-api-versioning-v1-contract.md).

## Lifecycle Classes

- `stable`: current supported public contract.
- `legacy`: supported for compatibility; includes deprecation + sunset headers.
- `experimental`: subject to change and not guaranteed stable.
- `sunset`: deprecated and scheduled for removal at a defined boundary.
- `removed`: no longer served; references should point to the replacement or archive.
- `internal`: operational/debug surfaces not intended as product contracts.

## Compatibility Rules

- New integrations target `/api/v1`.
- Legacy routes remain available through sunset.
- Envelope format is required for migrated endpoints:
  - success: `{ "success": true, "data": ... }`
  - error: `{ "success": false, "error": { "code", "message", "details?" } }`

## Runtime Signals

- Every response includes `X-API-Lifecycle`.
- `legacy` responses also include:
  - `Deprecation: true`
  - `Sunset: <RFC3339 datetime>`

## Enforcement

- Route lifecycle policy checker: `scripts/architecture/check_route_lifecycle.py`
- Capability/boundary checker: `scripts/architecture/check_capability_boundaries.py`

## Migration Observability

- Runtime counters are exposed at `GET /debug/api/migration-metrics` (ops-auth required).
- Tracked metrics include:
  - lifecycle request totals (`stable|legacy|experimental|internal`)
  - `/api/v1` vs legacy usage totals
  - error-code distribution by status
  - provider probe failure rates
- The compatibility dashboard should be generated from route inventory plus
  runtime usage, not maintained as a handwritten alias list.
- Legacy routes are removable only when usage is zero for the agreed period,
  consumers have migrated, docs are updated, and CI confirms no references
  remain.
