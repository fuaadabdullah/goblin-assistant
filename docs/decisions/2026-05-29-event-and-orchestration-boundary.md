# Event and Orchestration Boundary

## Status
accepted

## Context
Orchestration logic can drift into direct provider/storage coupling, making execution flow hard to reason about and difficult to evolve.

## Decision
Treat orchestration as a coordination capability:
- It may consume typed provider contracts and shared services.
- It must not import provider implementation modules.
- It must not import storage modules directly.
- Route-level orchestration surfaces are lifecycle-classified (`stable|legacy|experimental|internal`).

## Consequences
- Coordination logic remains decoupled from provider/storage internals.
- Cross-capability integration happens via contracts and events, not direct implementation imports.

## Operational Notes
- Boundary rules are codified in `apps/api/architecture-capabilities.json`.
- Guardrails run in CI on PRs via `check_capability_boundaries.py`.

