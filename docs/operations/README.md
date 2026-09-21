# Operations Docs

Operational runbooks, checklists, and implementation procedures.

This directory is the canonical home for operational documentation previously under `docs/runbooks/`.

Every file in this directory is listed below. If you add one, add it here too — an
unlisted doc is an undiscoverable doc.

## Start here

- `ENVIRONMENT_SETUP.md`: environment variables and local setup.
- `contributing.md`: contributor onboarding — local env, branch and PR conventions, code of conduct.

## Testing

- `TESTING.md`: test execution strategy and commands.
- `CRITICAL_TESTING_POLICY.md`: Tier 0 risk tiers, test-pyramid shape, and the
  eight-journey E2E budget cap.
- `VISUAL_TESTING.md`: Storybook and Chromatic commands for visual regression runs.
  Largely superseded by `../ux/VISUAL_REGRESSION_TESTING.md`, which is fuller.

## Deployment operations

- `DEPLOYMENT_AND_TESTING.md`: deployment validation flow — the canonical
  entry point for deploying and verifying a release.
- `DEPLOYMENT_ARCHITECTURE.md`: how the deployed system is laid out across
  Render (backend) and Vercel (frontend).
- `RENDER_DEPLOYMENT_GUIDE.md`: Render-specific backend deployment,
  environment configuration, and verification steps.
- `PRODUCTION_DEPLOYMENT_CHECKLIST.md`: production readiness checks.
- `DEPLOYMENT_ROLLBACK.md`: rolling back a bad deploy on Render and/or
  Vercel, including the database-migration edge case.
- `PDF_ATTACHMENT_EXTRACTION.md`: runtime flags, chunk and character budgets, and
  optional OCR dependencies for PDF attachment text.

## Release operations

- `RELEASE_PROCESS.md`: release cut checklist, tag policy, and verification flow.
- `CI_CD_PIPELINE_README.md`: the GitHub Actions, CircleCI, and Terraform pipeline,
  required secrets, and staging-to-production gates.
- `PHASE_GATES.md`: staged bring-up gates from baseline chat loop to routing to
  the agent loop.
- `DOGFOODING_V0_3.md`: v0.3 real-user dogfooding entry gates, feedback loop,
  support routing, and rollback rules.
- `SELF_DEVELOPMENT_AGENT_LOOP.md`: the agent task API, worker payload contract,
  generate-test-repair loop, and PR review flow.

## Security operations

- `SECRET_EXPOSURE_INCIDENT_RESPONSE.md`: incident response for exposed secrets.
- `LEGACY_EXCLUSIONS_REGISTER.md`: temporary exclusions with owners and review dates.
- `SANDBOX_README.md`: sandbox runtime operations and constraints.
- `AUTHENTICATION_SETUP.md`: Supabase auth env vars, register/login/refresh request
  shapes, and the mock-auth dev fallback.
- `ATTESTATION_WEBHOOK_DEPLOYMENT.md`: deploying the Kubernetes attestation admission
  webhook with cert-manager, mTLS, and Redis rate limiting.
- `supabase-smtp-setup.md`: configuring Resend or built-in Supabase SMTP so signup
  confirmation emails send.

## Privacy operations

- `PRIVACY_QUICKSTART.md`: five-minute local bring-up of sanitization, the RLS
  migration, and privacy endpoints.
- `PRIVACY_QUICK_REFERENCE.md`: copy-paste commands, GDPR export/delete endpoints,
  and code snippets for the privacy layer.
- `PRIVACY_DEPLOYMENT_CHECKLIST.md`: staging-then-production rollout of the
  privacy/PII stack, with rollback and sign-off.

## Provider operations

- `QUICKSTART_AI_PROVIDERS.md`: provider setup and smoke-test runbook.
- `PROVIDERS.md`: canonical provider matrix and env requirements.
- `JIRA_PROVIDER_OPS.md`: Jira provider incident automation, backlog conventions, and release workflow.
- `CONFLUENCE_PROVIDER_ARCHITECTURE.md`: repo-first Confluence workflow, source mapping, and provider-doc maintenance rules.
- `PROVIDER_DISPATCH_INCIDENT_RESPONSE.md`: triage for failing/degraded/
  misrouted provider dispatch — circuit breaker state, routing decisions,
  provider-leakage import errors.
- `COLAB_WORKER.md`: standing up a disposable Colab GPU llama.cpp worker and
  registering it as provider `colab_worker`.
- `README_DEBUGGER.md`: the `/debug/suggest` endpoint and Raptor-versus-fallback
  model routing for debugging tasks.
- `confluence/`: repo-tracked source material for the Provider Architecture
  Confluence space; see `confluence/README.md`.

## Observability

- `OBSERVABILITY_README.md`: the OpenTelemetry, Prometheus, Grafana, and Jaeger
  instrumentation stack and how it is configured.
- `CULTURAL_RULES.md`: the "no black boxes" observability principles and the fields
  every decision must log.
- `SLO.md`: SLO targets, error-budget math, alert names, and per-SLO diagnostic runbooks.
- `PRODUCTION_MONITORING.md`: production middleware configuration — rate limits,
  CORS, structured logging, and RAG privacy guidance.
- `PRODUCTION_DATADOG_SETUP.md`: creating the Datadog RUM application and wiring
  production/staging credentials, logs, and alerts.
- `MONITORING_SETUP_GUIDE.md`: quick Datadog RUM, Vercel Analytics, and backend
  uptime-check setup. Overlaps `PRODUCTION_DATADOG_SETUP.md`, which is fuller.
- `WEB_VITALS_BUDGETS.md`: Core Web Vitals p75 targets, emitted metric names, and
  how to verify instrumentation.

## Data & storage

- `DATABASE_SETUP.md`: choosing and configuring SQLite, Postgres, or Supabase,
  initializing schema, and validating the connection.
- `REDIS_SETUP.md`: provisioning Redis for caching, sessions, and rate limiting,
  with Docker config, monitoring, and scaling.
- `MANAGED_DATA_LAYER_SETUP.md`: wiring Supabase Postgres with pgvector plus
  Upstash Redis as the managed data layer.
- `GOBLINOS_STORAGE_README.md`: symlinking node_modules, venv, Docker cache, and
  logs onto the GOBLINOS external drive. Local-workstation specific.

## Memory and context

- `MEMORY_PROMOTION_GUIDELINES.md`: canonical memory promotion, conflict, lifecycle,
  forgetting, and privacy policy.
- The memory and context-assembly design docs live in `../memory/` — see
  `../memory/README.md` for the state machine, scoring, stratification, write-time
  decisions, and retrieval ordering.

## API compatibility tracking

- `API_CONTRACT_GATES.md`: regenerating the checked-in OpenAPI and route-manifest
  snapshots, and the CI gates that block drift.
- `API_CONTRACT_MATRIX.md`: per-surface table of which frontend clients and backend
  endpoints are contract-aligned.
- `API_ROUTE_MIGRATION_TRACKER.md`: settings-route compatibility matrix and
  sprint burn-down checklist.
- `../architecture/DOCUMENTATION_ARCHITECTURE_RFC.md`: docs IA and API lifecycle
  governance baseline.

## Product guides

- `FINANCIAL_ANALYST_GUIDE.md`: end-user guide to the DCF, portfolio, earnings, and
  screener tools. Not an operations doc; it needs a product-docs home.

## Notes

- Governance and lifecycle rules live in `docs/decisions/` (including release process, documentation ownership, and deprecation lifecycle ADRs).
- Keep architecture decisions in `docs/decisions/`.
- Keep security policy narratives in `docs/security/`.
- Keep deprecated or historical material in `docs/archive/`.
- Frontend authoring docs — component library, design tokens, component
  architecture, directory organization, services and utils — live in `docs/frontend/`.
