# Archive Docs

Historical and legacy documentation kept for reference.

Archived docs are non-canonical and may require verification before reuse.

For active tracking of temporary legacy exclusions, use `../operations/LEGACY_EXCLUSIONS_REGISTER.md`.

## What belongs here

- Superseded guides replaced by newer canonical docs.
- Historical implementation summaries and migration notes.
- One-time reports preserved for context.

## Contents

Deployment snapshots — each describes the state of one past deploy:

- `DEPLOYMENT_STATUS.md` (v0.2.0), `DEPLOYMENT_COMPLETION_GUIDE.md`,
  `POST_DEPLOYMENT_GUIDE.md`, `QUICKSTART_PRODUCTION.md`

Audits and migration logs — each records findings or progress at a point in time:

- `ENDPOINT_AUDIT.md` (Dec 2025 endpoint smoke test), `WEBHOOK_AUTH_AUDIT.md`
  (findings since resolved in `../operations/ATTESTATION_WEBHOOK_DEPLOYMENT.md`),
  `STORAGE_MIGRATION.md`, `PRIVACY_PYTHON_313_NOTE.md`

Completion reports — each records work finished on a given date:

- `AUTHENTICATION_IMPROVEMENTS.md`, `CHAT_FUNCTIONALITY_RESTORED.md`,
  `CONFIGURATION_VERIFICATION.md`, `PRIVACY_IMPLEMENTATION_SUCCESS.md`,
  `PRIVACY_EXECUTIVE_SUMMARY.md`, `PRIVACY_IMPLEMENTATION_SUMMARY.md`,
  `MONITORING_IMPLEMENTATION.md`, `DATADOG_PROCESS_MONITORING_SETUP.md`,
  `FINAL_SUMMARY.md`

Frontend and UX implementation reports — theme rollout, component migration,
logo and UI passes, accessibility remediation, visual-regression setup:

- `THEME_COMPLETE_REPORT.md`, `THEME_IMPLEMENTATION_SUMMARY.md`,
  `THEME_AND_ACCESSIBILITY_VERIFICATION.md`, `COMPONENT_ATOMIZATION_SUMMARY.md`,
  `COMPONENT_MIGRATION_COMPLETE.md`, `MIGRATION_PROGRESS.md`,
  `LOGO_OPTIMIZATION_SUMMARY.md`, `UI_IMPROVEMENTS_SUMMARY.md`,
  `ZUSTAND_AXIOS_HEALTH_CHECK.md`, `ACCESSIBILITY_SUMMARY.md`,
  `ACCESSIBILITY_TESTING_CHECKLIST.md`, `UX_IMPROVEMENTS.md`,
  `VISUAL_REGRESSION_COMPLETE.md`

Designs that did not ship:

- `API_QUICK_REF.md` and `DASHBOARD_API_CONSOLIDATION.md` describe an
  `/api/dashboard/*` surface that was never registered in the backend.

Some of these reference paths from the pre-monorepo layout (`backend/`,
`apps/goblin-assistant/`), a Vite dev server, or `src/App.tsx` — none of which
exist now. That is expected; they are preserved as written rather than
rewritten. Colour values in the theme reports predate the move to the warm
palette, so treat any contrast figure there as superseded by
`../ux/ACCESSIBILITY.md`.

## Usage rules

- Do not treat archive files as current operational policy.
- If an archived doc is still needed, promote the relevant content into
  `docs/operations/`, `docs/security/`, or `docs/decisions/` and link the source.
- Add a short note at the top of archived docs when possible:
  "Archived: not canonical."
