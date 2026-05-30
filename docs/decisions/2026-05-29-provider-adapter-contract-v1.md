# Provider Adapter Contract v1

## Status
accepted

## Context
Provider behavior was exposed through mixed interfaces (`invoke`, `stream`, `health_check`) and concrete provider modules were easy to import outside the provider boundary. This increases leakage risk and makes orchestration/provider evolution brittle.

## Decision
Define a strict provider adapter contract consumed by dispatch/orchestration:
- Required v1 surface: `chat`, `stream_chat`, `health`, `capabilities`
- `embeddings` is optional in v1 and exposed via capabilities
- Base provider implements the v1 adapter methods as compatibility wrappers
- Concrete provider modules must not be imported from non-provider domains

## Consequences
- New provider implementations must satisfy one explicit contract.
- Routing/orchestration can remain provider-agnostic.
- Provider-specific quirks stay inside adapters.

## Operational Notes
- Enforced by `scripts/architecture/check_capability_boundaries.py`.
- Capability metadata is centralized in `apps/api/architecture-capabilities.json`.

