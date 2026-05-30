# API and Frontend Standards

## API Contract-First Rules

- Every migrated FastAPI endpoint returns a response envelope.
- Success shape:
  - `{"success": true, "data": ...}`
- Error shape:
  - `{"success": false, "error": {"code": "SOME_CODE", "message": "Human readable message", "details": {...}}}`
- Use explicit `response_model` on routes.
- Prefer stable machine-readable error codes (`VALIDATION_ERROR`, `INTERNAL_ERROR`, etc).

## Versioning Rules

- Versioned aliases are exposed under `/api/v1`.
- Legacy unversioned routes remain available during migration.
- New integrations should target `/api/v1`.

## Frontend Boundary Rules

- Keep UI components presentational.
- Place async orchestration and API calls in feature hooks/services.
- For feature modules, follow:
  - `features/<feature>/components`
  - `features/<feature>/hooks`
  - `features/<feature>/api`
  - `features/<feature>/types`
- Component props must be typed.

## Enforcement

- ESLint warns when feature components import `@/api` directly.
- Prefer feature-level API adapters that wrap shared clients.

## Documentation Standard: Systems Over Obvious Code

- Do not document trivial line-by-line mechanics (for example, comments equivalent to `x += 1`).
- Document:
  - Why the subsystem exists and why the approach was chosen.
  - Architectural decisions and boundaries.
  - Constraints and tradeoffs.
  - Edge cases and failure modes.
  - Operational assumptions (runtime deps, environment expectations, rollback considerations).
- Preferred artifacts for non-trivial changes:
  - ADRs in `docs/decisions/`
  - Diagrams (sequence/component/data-flow)
  - Runbooks in `docs/operations/`
  - Onboarding docs for new contributors/operators

## GoblinOS Standard: Orchestration-Ready by Default

- Every subsystem must be future-ready for:
  - agents
  - queues
  - workflows
  - distributed execution
  - plugins
  - monitoring
  - automation hooks
- Expose and preserve:
  - clean interfaces
  - events
  - typed contracts
  - observability (logs/metrics/tracing hooks)
- Avoid direct hardwiring between subsystems for short-term speed.
- New integrations should favor adapter/event boundaries over direct cross-module coupling.

## Capability Ownership and Boundaries

- Capability ownership and allowed imports are defined in `apps/api/architecture-capabilities.json`.
- CI enforces ownership and provider-leakage rules via `scripts/architecture/check_capability_boundaries.py`.
- Non-provider modules must not import concrete provider implementations; use provider contracts/dispatcher boundaries.
