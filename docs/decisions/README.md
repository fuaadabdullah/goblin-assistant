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
