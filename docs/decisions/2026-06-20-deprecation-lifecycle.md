# Deprecation Lifecycle

## Status
accepted

## Context
The repository already treats compatibility as a first-class concern for APIs and operational surfaces, but deprecation behavior was not captured as a single lifecycle. That creates two common failure modes: removing things too early, or keeping old surfaces around without a clear sunset plan.

## Decision
Use a consistent deprecation lifecycle for docs, routes, and features:
- `active`: current supported surface.
- `deprecated`: still usable, but a replacement exists and the old surface should carry a clear warning.
- `sunset`: the removal date or release boundary has been announced and should be treated as imminent.
- `removed`: the old surface is gone and references should point only to the replacement or archive.

Rules:
- Public API routes that are being retired must follow the existing compatibility lifecycle policy and emit the appropriate deprecation/sunset signals.
- User-facing docs and runbooks should call out the replacement while the old material is still needed.
- Deprecated material should move to an archive only after the sunset boundary has passed or the replacement is stable enough to stand alone.

## Consequences
- Consumers get a predictable upgrade path instead of surprise removals.
- Deprecated docs and routes remain visible long enough to be useful, but not so long that they become ambiguous.
- Cleanup work becomes a lifecycle step instead of an ad hoc judgment call.

## Operational Notes
- API lifecycle policy: `docs/architecture/API_COMPATIBILITY_LIFECYCLE.md`.
- Route lifecycle enforcement: `scripts/architecture/check_route_lifecycle.py`.
- Historical doc and runbook cleanup should use the archive conventions under `docs/archive/`.
