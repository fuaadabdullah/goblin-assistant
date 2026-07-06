# Documentation Index

Canonical docs for the monorepo:

- `../README.md`: monorepo overview and quickstart
- `../AGENTS.md`: task-oriented developer/agent navigation
- `architecture/README.md`: architecture, standards, and system boundaries
- `architecture/DOCUMENTATION_ARCHITECTURE_RFC.md`: docs information architecture and governance RFC
- `architecture/documentation-map.json`: machine-readable docs inventory and ownership map
- `backend/README.md`: backend API and routing references
- `frontend/README.md`: frontend implementation and UI architecture
- `infra/README.md`: environment, deployment, and CI/CD setup
- `security/README.md`: privacy, secrets, and security standards
- `ux/README.md`: accessibility, responsiveness, and UX verification
- `decisions/README.md`: architecture decision records (ADRs)
- `operations/README.md`: runbooks and operational procedures
- `operations/LEGACY_EXCLUSIONS_REGISTER.md`: tracked temporary legacy exclusions and review dates
- `archive/README.md`: historical/non-canonical documents

Migration notes:

- ADRs moved from `docs/adr/` to `docs/decisions/`.
- Runbooks moved from `docs/runbooks/` to `docs/operations/`.
- Root-level docs were rehomed into domain folders to reduce monorepo doc sprawl.
- `docs/adr/` and `docs/runbooks/` remain compatibility-only entrypoints.
- Legacy moved-notice stubs should point to the actual canonical location in
  this checkout, not to a second backend docs tree.
