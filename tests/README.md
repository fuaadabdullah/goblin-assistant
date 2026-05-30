# Tests Taxonomy

This root `tests/` directory is the canonical taxonomy map for test strategy visibility.

## Buckets

- `tests/integration`: integration boundary tests (API/service/system boundaries).
- `tests/e2e`: end-to-end user journey tests.
- `tests/performance`: performance/load/concurrency tests.
- `tests/contract`: API and consumer contract tests.

## Manifest Source of Truth

Manifests under `tests/manifests/*.json` map each bucket to real suites in-place (no forced relocation yet):

- API tests remain under `apps/api/src/api/tests`.
- Web unit/contract tests remain under `apps/web/src/**/__tests__`.
- Web E2E remains under `apps/web/e2e`.

Use:

- `make test-integration`
- `make test-contract`
- `make test-performance`
