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
- `2026-05-30-assistant-tools-canonicalization.md`
- `2026-06-20-router-decomposition.md`
- `2026-06-20-dispatcher-decomposition.md`
- `2026-06-20-release-process.md`
- `2026-06-20-release-tag-strategy.md`
- `2026-06-20-documentation-ownership.md`
- `2026-06-20-deprecation-lifecycle.md`
- `2026-07-17-settings-root-alias-retirement.md`
- `2026-07-17-supabase-only-auth.md`

## Indexed ADRs

Stable ADR IDs are the canonical reference key. Filenames are convenience labels.

| ADR ID | Title | File | Status |
| --- | --- | --- | --- |
| `ADR-0001` | Next.js App Router Over Pages Router | `2026-07-06-nextjs-app-router-over-pages-router.md` | accepted |
| `ADR-0002` | API Versioning and the `/api/v1` Contract | `2026-07-06-api-versioning-v1-contract.md` | accepted |
| `ADR-0003` | Thin Next.js Proxies vs Direct Backend Calls | `2026-07-06-nextjs-proxies-vs-direct.md` | accepted |
| `ADR-0004` | Sandbox Architecture and Job Execution Model | `2026-07-06-sandbox-architecture.md` | accepted |
| `ADR-0005` | Settings Root Alias Retirement | `2026-07-17-settings-root-alias-retirement.md` | accepted |
| `ADR-0006` | Supabase-Only Authentication | `2026-07-17-supabase-only-auth.md` | accepted |

## Status

- Canonical ADR directory exists and is active.
- ADR coverage is currently focused on API boundaries, provider contracts, tool canonicalization, router/dispatcher decomposition, release policy, and route-retirement decisions.

## Next ADR candidates

- Documentation index hygiene: owner metadata, review cadence, and archive/supersession cleanup.
- ADR status audit for older decisions that may need `deprecated` or `superseded` status.
