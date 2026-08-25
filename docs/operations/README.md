# Operations Docs

Operational runbooks, checklists, and implementation procedures.

This directory is the canonical home for operational documentation previously under `docs/runbooks/`.

## Start here

- `ENVIRONMENT_SETUP.md`: environment variables and local setup.
- `DEPLOYMENT_AND_TESTING.md`: deployment validation flow.
- `PRODUCTION_DEPLOYMENT_CHECKLIST.md`: production readiness checks.
- `TESTING.md`: test execution strategy and commands.

## Security operations

- `SECRET_EXPOSURE_INCIDENT_RESPONSE.md`: incident response for exposed secrets.
- `LEGACY_EXCLUSIONS_REGISTER.md`: temporary exclusions with owners and review dates.
- `SANDBOX_README.md`: sandbox runtime operations and constraints.
- `MEMORY_PROMOTION_GUIDELINES.md`: canonical memory promotion, conflict, lifecycle, forgetting, and privacy policy.

## Provider operations

- `QUICKSTART_AI_PROVIDERS.md`: provider setup and smoke-test runbook.
- `PROVIDERS.md`: canonical provider matrix and env requirements.
- `JIRA_PROVIDER_OPS.md`: Jira provider incident automation, backlog conventions, and release workflow.
- `CONFLUENCE_PROVIDER_ARCHITECTURE.md`: repo-first Confluence workflow, source mapping, and provider-doc maintenance rules.
- `PROVIDER_DISPATCH_INCIDENT_RESPONSE.md`: triage for failing/degraded/
  misrouted provider dispatch — circuit breaker state, routing decisions,
  provider-leakage import errors.

## Release operations

- `RELEASE_PROCESS.md`: release cut checklist, tag policy, and verification flow.
- `DOGFOODING_V0_3.md`: v0.3 real-user dogfooding entry gates, feedback loop,
  support routing, and rollback rules.
- `DEPLOYMENT_ROLLBACK.md`: rolling back a bad deploy on OCI and/or Vercel,
  including the database-migration edge case.

## API compatibility tracking

- `API_ROUTE_MIGRATION_TRACKER.md`: settings-route compatibility matrix and
  sprint burn-down checklist.
- `../architecture/DOCUMENTATION_ARCHITECTURE_RFC.md`: docs IA and API lifecycle
  governance baseline.

## Notes

- Governance and lifecycle rules live in `docs/decisions/` (including release process, documentation ownership, and deprecation lifecycle ADRs).
- Keep architecture decisions in `docs/decisions/`.
- Keep security policy narratives in `docs/security/`.
- Keep deprecated or historical material in `docs/archive/`.
