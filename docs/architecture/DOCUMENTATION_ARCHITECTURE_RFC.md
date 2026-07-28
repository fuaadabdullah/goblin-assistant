# Documentation Architecture RFC

## Status
draft

## Summary

This RFC defines the documentation information architecture for the repository,
identifies the current canonical doc surfaces, and sets the cleanup and
governance rules that prevent duplicate truth from returning.

The core recommendation is to keep documentation organized by domain, keep
ADR content canonical in `docs/decisions/`, and treat `docs/adr/` as a
compatibility-only shim for legacy links. Operational and backend references
should converge on the domain indexes under `docs/operations/` and
`docs/backend/`, not on ad hoc moved-notice stubs.

## Inventory

The current `docs/` tree is already partitioned by domain:

- `docs/architecture/`: system boundaries, standards, and platform decisions.
- `docs/backend/`: backend API, routing, and contract references.
- `docs/frontend/`: UI implementation, migration notes, and component docs.
- `docs/infra/`: environment, deployment, and CI/CD guidance.
- `docs/security/`: privacy, secrets, and security policy.
- `docs/ux/`: accessibility, responsiveness, and visual verification.
- `docs/operations/`: runbooks, procedures, and compatibility trackers.
- `docs/archive/`: historical material and retired guidance.
- `docs/memory/`: memory-system behavior and lifecycle references.
- `docs/decisions/`: canonical ADRs.
- `docs/adr/`: backward-compatibility entrypoint only.

The machine-readable inventory for this RFC lives in
`docs/architecture/documentation-map.json` and is validated by
`make check-docs-inventory`.

### Findings

- Duplicate truth exists where moved notices point to paths that do not exist
  in this checkout, especially old backend docs-tree references.
- ADR home is already canonicalized in `docs/decisions/`; `docs/adr/` is a
  compatibility stub and should not receive new content.
- The API compatibility and deprecation policy is already captured in
  architecture ADRs, but the operational tracker still needs to move from a
  handwritten list toward generated status based on route inventory plus
  runtime usage.
- Several docs in `docs/operations/` are backend-adjacent runbooks that should
  point to the backend and contract indexes, not to a second backend docs tree.
- `docs/archive/` is correctly reserved for historical material and should be
  the destination for fully retired guidance, not an intermediate dumping
  ground.

## Information Architecture

| Area | Purpose | Owner | Audience | Generation model | Review cadence |
| --- | --- | --- | --- | --- | --- |
| `docs/architecture/` | System boundaries, architecture standards, and governance | Architecture + platform maintainers | Engineers, reviewers, agents | Mostly handwritten, some generated diagrams | Monthly and on architectural change |
| `docs/backend/` | Backend API, routing, and contract references | Backend maintainers | Backend and frontend engineers | Mostly handwritten, some generated inventories | Monthly and on contract change |
| `docs/frontend/` | UI architecture, migration notes, and component guidance | Frontend maintainers | Frontend engineers, QA | Mixed handwritten and generated reports | Per release or major UI change |
| `docs/infra/` | Environment, deployment, and CI/CD setup | Infra/release maintainers | Devs, release engineers | Handwritten runbooks with generated snippets | Quarterly and on infra change |
| `docs/security/` | Security and privacy policy | Security owner + subsystem owner | Engineers, reviewers | Handwritten policy with referenced runbooks | Quarterly and on security change |
| `docs/ux/` | Accessibility and visual verification | Frontend + design owner | Frontend engineers, QA, design | Mostly handwritten, some generated screenshots | Per release |
| `docs/operations/` | Runbooks, procedures, and migration trackers | Runtime/ops maintainers | Devs, operators, release owners | Handwritten operational docs plus generated trackers | Monthly and during active migrations |
| `docs/archive/` | Historical non-canonical material | Documentation owner | Reference only | Archived copies and summaries | Only on archive moves |
| `docs/memory/` | Memory-system behavior and lifecycle reference | Memory subsystem owner | Engineers working on memory stack | Handwritten technical reference | On memory-policy changes |
| `docs/decisions/` | Canonical ADRs | Architecture + release governance | Engineers, reviewers, agents | Handwritten decision records | On every architecture-impacting change |
| `docs/adr/` | Compatibility-only ADR entrypoint | Documentation owner | Legacy links only | Thin compatibility stub | Never expand |

## Classification Model

Every doc should land in exactly one of these classes:

- `canonical`: current source of truth for a domain.
- `generated`: produced from route manifests, OpenAPI snapshots, or other
  checked-in source data.
- `compatibility-stub`: points readers to the canonical replacement.
- `historical`: retained for reference in `docs/archive/`.
- `orphaned`: exists without an owner, canonical home, or clear audience.

### Repository-specific classifications

- `docs/decisions/README.md` and its indexed ADRs are canonical.
- `docs/adr/README.md` is a compatibility stub only.
- `docs/backend/API_ROUTE_INVENTORY.generated.md` is generated.
- `docs/operations/API_ROUTE_MIGRATION_TRACKER.md` is a transitional
  compatibility tracker and should eventually become generated or be removed
  once legacy routes are gone.
- `docs/operations/ENDPOINT_AUDIT.md` and `docs/operations/PRODUCTION_MONITORING.md`
  should be normalized to canonical backend/operations pointers instead of
  referencing a non-existent legacy backend docs tree.

## Migration Plan

1. Normalize the docs indexes so each domain README only points to canonical
   documents for that domain.
2. Replace stale moved-notice banners with compatibility notes or archive
   notices that point at the actual canonical location in this checkout.
3. Convert route- and contract-derived docs into generated artifacts where
   possible, keeping handwritten migration notes only where active churn exists.
4. Add doc checks that flag broken canonical-location references, orphaned docs,
   duplicate ownership across domains, and compatibility-stub leakage.
5. Keep ADRs in `docs/decisions/` and leave `docs/adr/` as compatibility only
   unless a future RFC explicitly revises the canonical home.

## API Lifecycle Policy

The API lifecycle is part of the documentation architecture because it shapes
how compatibility debt is described and retired.

- Lifecycle states: `experimental`, `stable`, `legacy`, `sunset`, `removed`.
- Legacy routes must advertise lifecycle information through headers and
  runtime signals.
- Route removal is only eligible after usage drops to zero for an agreed
  period, consumers are migrated, docs are updated, and CI confirms no
  references remain.
- The compatibility dashboard should be generated from route inventory plus
  runtime usage, not maintained as a handwritten list.

## Governance

- Documentation ownership lives with the owning subsystem or governance group.
- Documentation changes that affect architecture, route contracts, or public
  lifecycle policy should update the relevant ADRs and indexes in the same
  change.
- Historical material should move to `docs/archive/` once it is no longer an
  active reference.
- Future docs work should prefer generated indexes and inventory outputs over
  parallel hand-maintained summaries.

## Risks, Trade-offs, Effort Estimates

The goal of this RFC is to reduce ambiguity before cleanup and deprecation
work begins. The estimates below assume the team chooses the lowest-risk path
for compatibility debt first, then expands into real persistence or deeper
observability only if the inventory and lifecycle gates justify it.

| Area | Risk | Trade-off | Effort |
| --- | --- | --- | --- |
| Docs and ADR reconciliation | Low | Front-loads time into alignment, but lowers confusion across the cleanup sprint | 6-8 hours |
| CI contract checks | Moderate | Requires scripting and debugging time, but prevents doc and route drift from reappearing | 12-16 hours |
| Placeholder endpoints via `501` | Low | Fastest way to make stubs explicit, but defers implementation work to a later sprint | 2-4 hours per endpoint |
| Placeholder endpoints via persistence | Higher | Produces the real feature, but introduces schema design, migration, and test risk | 1.5-2 days per endpoint |
| Observability | Moderate | Adds Prometheus / OpenTelemetry setup and maintenance overhead, but improves debuggability and removal safety | 2 days |
| Testing | Moderate | Takes time to build contract and smoke coverage, but is the main guard against regressions | 1.5-2.5 days |
| Cleanup | Low | Removes mental overhead and dead paths, but should only happen after tests and lifecycle gates pass | 1 day |

The practical program estimate is 60-80 hours over two weeks if the team uses
`501` stubs for two temporary endpoints and keeps persistence work out of the
critical path. If persistence is chosen for one or more endpoints, the effort
will increase materially because schema design and migration testing become
part of the sprint scope.

### Execution Notes

- Front-load docs, ADRs, and lifecycle policy so the rest of the sprint has a
  stable reference point.
- Treat alias removal as lifecycle debt retirement, not cleanup-only deletion.
- Require route metadata, deprecation headers, usage telemetry, and CI checks
  before any compatibility alias is eligible for removal.
- Prefer generated inventories and dashboards over handwritten alias lists.

### References

- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/) and
  [TestClient reference](https://fastapi.tiangolo.com/reference/testclient/).
- [Next.js Layouts and Pages](https://nextjs.org/docs/app/getting-started/layouts-and-pages)
  and the [root layout file convention](https://nextjs.org/docs/app/api-reference/file-conventions/layout).
- [Prometheus client libraries](https://prometheus.io/docs/instrumenting/clientlibs/)
  for exposing application metrics.
- [Architectural Decision Records](https://adr.github.io/) and the
  [ADR templates](https://adr.github.io/adr-templates/) guidance for structure
  and status fields.
- OpenAPI snapshot generation and diffing are implemented in this repository as
  a local contract-checking practice and are documented in the API tooling
  rather than a single upstream spec.
