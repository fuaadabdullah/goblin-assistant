# Capability Ownership Model

## Status
accepted

## Context
Domain boundaries were implicit, and cross-domain imports were easy to add without explicit ownership review.

## Decision
Define capability ownership as machine-checkable policy:
- Capabilities: `chat`, `providers`, `memory`, `sandbox`, `auth`, `orchestration`
- Each capability declares owned module prefixes.
- Each capability declares allowed dependency prefixes.
- Additional global rules prevent concrete provider leakage outside provider-owned domains.

## Consequences
- Boundary violations are caught in CI during PRs.
- Ownership is explicit and reviewable.
- Incremental refactors can tighten boundaries over time without a rewrite.

## Operational Notes
- Source of truth: `apps/api/architecture-capabilities.json`.
- Enforcement: `scripts/architecture/check_capability_boundaries.py`.

