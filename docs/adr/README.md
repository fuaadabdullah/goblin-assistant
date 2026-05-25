# Architecture Decision Records (ADRs)

Use ADRs to capture why decisions were made, not just what code changed.

## Required when

- A change affects architecture, boundaries, or subsystem integration.
- A change introduces operational constraints or assumptions.
- A subsystem interface/event/contract changes in a way future orchestration depends on.

## Minimal ADR format

1. Title
2. Status (`proposed`, `accepted`, `superseded`)
3. Context (problem, constraints, assumptions)
4. Decision
5. Consequences (tradeoffs, risks, edge cases)
6. Operational notes (monitoring, rollback, runbook links)

## File naming

- `YYYY-MM-DD-short-title.md`
