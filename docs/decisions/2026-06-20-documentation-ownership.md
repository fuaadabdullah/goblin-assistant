# Documentation Ownership

## Status
accepted

## Context
The repository has a large and fast-moving documentation surface across architecture, operations, security, and release notes. Without explicit ownership, docs drift becomes harder to notice than code drift because stale docs still look "finished".

## Decision
Assign documentation ownership by domain:
- `docs/decisions/` is owned by architecture and release governance.
- `docs/operations/` is owned by the runtime and operations maintainers for the relevant subsystem.
- `docs/security/` is owned by the security-conscious maintainer or security review owner for that area.

Documentation changes must follow these rules:
- Any behavioral or architectural change that affects a public surface must update the relevant doc set in the same change.
- New docs must either inherit an existing owner or establish a clear owner in the surrounding index/README.
- Stale or duplicated guidance should be corrected or removed instead of left as parallel truth.

## Consequences
- Ownership is explicit enough to route review and cleanup work.
- Docs are less likely to drift away from the code they describe.
- Readers can rely on the docs tree as a maintained system, not a passive archive.

## Operational Notes
- Indexes that reflect doc ownership should stay current, especially `docs/decisions/README.md`, `docs/operations/README.md`, and `docs/security/README.md`.
- High-impact doc updates should be reviewed with the corresponding code or operational change.
