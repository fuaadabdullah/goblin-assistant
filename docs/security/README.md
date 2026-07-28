# Security Docs

Security, privacy, and secrets management documentation.

## Core policies

- `SECURITY.md`: baseline security controls and implementation guidance.
- `PRIVACY_IMPLEMENTATION.md`: privacy architecture and control model.
- `PRIVACY_INTEGRATION_GUIDE.md`: integration-specific privacy guidance.

## Secrets and incident response

- `SECRETS_ROTATION.md`: remediation notes for discovered or exposed secrets.
- `../operations/SECRET_EXPOSURE_INCIDENT_RESPONSE.md`: operational incident runbook.

## Operational dependencies

- `../operations/ENVIRONMENT_SETUP.md`: required environment variables and setup.
- `../operations/PRODUCTION_DEPLOYMENT_CHECKLIST.md`: deploy-time security checks.

## Scope

Use this directory for canonical security and privacy policy documents.
Operational procedures stay in `docs/operations/`.

Security document ownership is shared with the relevant subsystem maintainer, but security policy changes should be reviewed against the security docs index and the owning ADRs in `docs/decisions/`.
