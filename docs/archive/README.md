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

Completion reports — each records work finished on a given date:

- `AUTHENTICATION_IMPROVEMENTS.md`, `CHAT_FUNCTIONALITY_RESTORED.md`,
  `CONFIGURATION_VERIFICATION.md`, `PRIVACY_IMPLEMENTATION_SUCCESS.md`,
  `PRIVACY_EXECUTIVE_SUMMARY.md`, `PRIVACY_IMPLEMENTATION_SUMMARY.md`,
  `MONITORING_IMPLEMENTATION.md`, `DATADOG_PROCESS_MONITORING_SETUP.md`,
  `FINAL_SUMMARY.md`

Some of these reference paths from the pre-monorepo layout (`backend/`,
`apps/goblin-assistant/`) that no longer exist. That is expected — they are
preserved as written rather than rewritten.

## Usage rules

- Do not treat archive files as current operational policy.
- If an archived doc is still needed, promote the relevant content into
  `docs/operations/`, `docs/security/`, or `docs/decisions/` and link the source.
- Add a short note at the top of archived docs when possible:
  "Archived: not canonical."
