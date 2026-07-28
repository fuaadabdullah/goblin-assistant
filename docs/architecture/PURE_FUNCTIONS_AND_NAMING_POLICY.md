# Pure-by-Default and Intent Naming Policy

This policy is mandatory for trading-safety-critical code paths.

## Core Standard

All core/domain logic must be pure by default:

- Pure inputs produce predictable outputs.
- Hidden side effects are disallowed.
- Side effects must be explicit and isolated to approved boundary layers.

## Disallowed in Pure Zones

The following are disallowed in pure zones unless explicitly exempted:

- Mutating globals or module-level shared state.
- Silent file writes.
- Implicit external API calls.
- Runtime mutation of process environment variables.

## Approved Side-Effect Boundaries

Side effects are allowed only in modules with explicit boundary intent, such as:

- API routes/controllers
- Service adapters/integration clients
- Providers/model gateways
- Storage/repository layers

Boundary modules should expose clear contracts and keep side effects contained.

## Naming Standard

Names must expose intent.

Avoid vague names like:

- `data`
- `temp`
- `manager`
- `helper`
- generic `process()`

Prefer names like:

- `pending_orders`
- `risk_engine`
- `calculate_position_size()`

## Function Contracts

When behavior may imply side effects, document:

- Inputs consumed
- Outputs produced
- Explicit side effects (if any)

## Rollout

The rollout is warn-then-ratchet:

1. Phase 1: warnings and full-repo visibility reports.
2. Phase 2: PR changed-files gate blocks new violations.
3. Phase 3: tighten allowlists and convert mature rules to hard failures.

Legacy side-effect patterns may remain temporarily in documented boundary/legacy paths, but no new hidden side effects are allowed.
