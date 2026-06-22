# Architecture Decision Records (ADRs)

Use ADRs to capture why decisions were made, not just what changed.

This directory is the canonical ADR location (moved from `docs/adr/`).

## Required when

- A change affects architecture, boundaries, or subsystem integration.
- A change introduces operational constraints or assumptions.
- A subsystem interface/event/contract changes in a way future orchestration depends on.

## Minimal ADR format

1. Title
2. Status (`proposed`, `accepted`, `superseded`)
3. Context
4. Decision
5. Consequences
6. Operational notes

## File naming

- `YYYY-MM-DD-short-title.md`

## Current ADRs

- `2026-05-29-capability-ownership-model.md`
- `2026-05-29-provider-adapter-contract-v1.md`
- `2026-05-29-event-and-orchestration-boundary.md`
- `2026-05-29-api-envelope-and-compat-lifecycle-policy.md`
- `2026-05-30-assistant-tools-canonicalization.md`
- `2026-06-20-router-decomposition.md`
- `2026-06-20-dispatcher-decomposition.md`
- `2026-06-20-release-process.md`
- `2026-06-20-release-tag-strategy.md`
- `2026-06-20-documentation-ownership.md`
- `2026-06-20-deprecation-lifecycle.md`

## Status

- Canonical ADR directory exists and is active.
- ADR coverage is currently focused on API boundaries, provider contracts, tool canonicalization, router/dispatcher decomposition, and release policy.

## Next ADR candidates

- Documentation index hygiene: owner metadata, review cadence, and archive/supersession cleanup.
- ADR status audit for older decisions that may need `deprecated` or `superseded` status.
