# Legacy Exclusions Register

Purpose: keep all intentional legacy exclusions explicit, temporary, and reviewable.

## Policy

- Every exclusion must have: owner, reason, and review date.
- Exclusions are temporary unless explicitly re-approved at review date.
- If an exclusion is no longer needed, remove it and delete the row.

## Current exclusions

| ID | Scope | Excluded from | Source of exclusion | Owner | Reason | Review by | Exit criteria |
| --- | --- | --- | --- | --- | --- | --- | --- |
| LEGACY-WEB-TESTS-001 | `apps/web/tests/legacy/**` | Web lint + standard Jest CI run | `apps/web/eslint.config.cjs` (`tests/legacy/**` in `ignores`), legacy files are not in Jest default `*.test`/`*.spec` pattern | Web platform | Historical JS smoke scripts from pre-current test architecture | 2026-08-31 | Port scenarios into `src/**/__tests__` or remove obsolete scripts |
| LEGACY-API-MODULE-001 | `apps/api/src/api/legacy/**` | API static type checks (mypy/pyright) | `apps/api/pyproject.toml` (`[tool.mypy].exclude`), `apps/api/pyrightconfig.json` (`exclude`) | API platform | Legacy compatibility surface retained while typed services are being consolidated | 2026-08-31 | Migrate/remove legacy module and drop exclude entries |

## Maintenance checklist

When adding a new exclusion:

1. Add a row in this register in the same PR.
2. Add/update tests that protect behavior during migration.
3. Set a concrete review date (max 90 days recommended).
4. Link issue/ADR in the PR description for traceability.
