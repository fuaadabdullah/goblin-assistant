# Operations Docs

Operational runbooks, checklists, and implementation procedures.

This directory is the canonical home for operational documentation previously under `docs/runbooks/`.

Key references:

- `LEGACY_EXCLUSIONS_REGISTER.md`: intentional temporary exclusions (legacy tests/modules), owners, and review dates.
- `SECRET_EXPOSURE_INCIDENT_RESPONSE.md`: detection, rotation/revocation, purge, and verification flow for exposed credentials.
- `QUICKSTART_AI_PROVIDERS.md`: provider setup/testing runbook and canonical alias matrix (including `siliconeflow` alias mapping).
- `PROVIDERS.md`: canonical provider matrix (provider → env vars → default model → tier → active/visible/selectable semantics).
- `COLAB_WORKER.md`: disposable Colab/ngrok worker runbook with dual API contract and backend heartbeat integration.
