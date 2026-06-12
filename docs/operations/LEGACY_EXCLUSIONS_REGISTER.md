# Legacy Exclusions Register

Purpose: keep all intentional legacy exclusions explicit, temporary, and reviewable.

## Policy

- Every exclusion must have: owner, reason, and review date.
- Exclusions are temporary unless explicitly re-approved at review date.
- If an exclusion is no longer needed, remove it and delete the row.

## Current exclusions

No active legacy exclusions are currently registered.

## Maintenance checklist

When adding a new exclusion:

1. Add a row in this register in the same PR.
2. Add/update tests that protect behavior during migration.
3. Set a concrete review date (max 90 days recommended).
4. Link issue/ADR in the PR description for traceability.
