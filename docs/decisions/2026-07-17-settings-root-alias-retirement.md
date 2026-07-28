# ADR-0005: Settings Root Alias Retirement

## Status
accepted

## Date
2026-07-17

## Context
The API previously carried a bare `/settings/` compatibility mount alongside the
versioned `/api/v1/settings/` surface. The repository has since standardized on
`/api/v1` as the canonical public API prefix, and the unversioned root alias is
no longer needed for internal or external callers.

## Decision
Retire the bare `/settings/` backend alias and keep `/api/v1/settings/` as the
only supported settings mount.

- API tests should assert that `/api/v1/settings/` remains available.
- API tests should also fail if `/settings/` reappears as a live mount.
- Migration docs should describe the retirement rather than preserving the alias
  as active compatibility debt.

## Consequences
- The backend contract becomes simpler and easier to reason about.
- Any future attempt to reintroduce the bare alias will be visible as drift.
- Callers that still depend on `/settings/` will now receive a hard failure
  instead of silent compatibility recovery.

## Operational Notes
- Keep route-alias coverage focused on the versioned settings mount.
- Update checked-in route inventories and docs from the canonical `/api/v1`
  surface only.
- The remaining settings sub-routes may continue to use the `/settings/*`
  logical path in generated inventory, but the live backend mount is versioned
  only.
