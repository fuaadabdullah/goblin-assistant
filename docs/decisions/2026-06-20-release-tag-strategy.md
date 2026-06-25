# Release Tag Strategy

## Status
accepted

## Context
The repository already uses changelog-driven releases, but the release history needed an explicit policy so tag creation, changelog entries, and workflow verification stayed aligned over time.

## Decision
Use immutable semantic version tags as the release record.

Release rules:
- the changelog is updated first;
- the release commit is tagged with the matching `vX.Y.Z` tag;
- the release workflow verifies changelog/tag alignment before publishing artifacts;
- tags are not rewritten after publication unless a release is explicitly superseded;
- historical gaps are backfilled with the earliest missing public release tag before continuing forward.

## Consequences
- The changelog and tags together define the public release history.
- Releases can be verified mechanically instead of inferred from branch state.
- Backfills are intentional and auditable rather than ad hoc.

## Operational Notes
- Verification helper: `scripts/release/verify_release_history.sh`.
- Workflow gate: `.github/workflows/release.yml`.
- Release runbook: `docs/operations/RELEASE_PROCESS.md`.
- Current tag history should include the backfilled release boundary tag and the latest public tag.
