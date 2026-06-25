# Release Process

## Status
accepted

## Context
Release history existed in the repository before the process was fully documented, which made it easy to ship without a consistent cutoff, changelog boundary, or tag policy. The repo already has a curated `CHANGELOG.md`, a release workflow, and published release tags, so the release process needs to describe how those pieces fit together.

## Decision
Use a simple release flow:
- Release candidates are the state of `main` after tests and release checks pass, with the changelog updated for the intended version.
- A release cut updates the changelog, creates the release tag, and uses the release workflow as the publish gate.
- Git tags are part of the release record and must be created for every public release.
- Tags are not rewritten after publication unless a release is explicitly superseded.

Backfill the missing inaugural release tag at the earliest release boundary in history, then continue tagging subsequent releases in order.

## Consequences
- The changelog and tags become the authoritative release history.
- Release decisions are traceable to a specific commit instead of being inferred from branch state.
- Retagging becomes exceptional, not routine.

## Operational Notes
- Release workflow: `.github/workflows/release.yml`.
- Release runbook: `docs/operations/RELEASE_PROCESS.md`.
- Release verification helper: `scripts/release/verify_release_history.sh`.
- Release workflow runs the verification helper before tests and packaging.
- Public release summary: `CHANGELOG.md`.
- Existing release tag: `v0.2.0`.
- Historical backfill tag: `v1.0.0`.
