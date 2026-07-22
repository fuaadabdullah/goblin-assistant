# v0.3 Dogfooding Runbook

Status: active for v0.3.0 dogfood rollout.
Owner: Platform / release owner.
Start date: 2026-07-22.

## Purpose

Dogfooding begins only after the architecture freeze and Tier 0 journey gates are
green. The goal is to put real users on the v0.3 path without widening access
faster than support, privacy review, and rollback can handle.

## Entry Gates

- `VERSION` and `CHANGELOG.md` identify `0.3.0`.
- `make test-critical` passes for provider routing, memory, auth, sandbox,
  billing, and orchestration.
- `make check-api-boundaries`, `make check-api-cycles`,
  `make check-capability-boundaries`, and `make check-operational-policy` pass.
- `scripts/release/verify_release_history.sh` passes after the `v0.3.0` tag is
  created.
- A release owner has confirmed the deployment target, rollback path, and support
  channel before inviting users.

## Cohort

- Start with 3 to 5 trusted users who understand the product is in dogfood.
- Do not invite external production customers until the first 24 hours have no
  Tier 0 regression.
- Keep infrastructure secrets and user-managed provider keys separated; do not
  request secrets through chat, email, or screenshots.

## Latency Review

- Watch chat P95 against the SLO target in `SLO.md`.
- Review routing explanations for provider choice, fallback reason, and stage
  latency before changing policy.
- If one provider dominates slow responses, disable or down-rank that provider
  through the existing provider configuration path, regenerate provider artifacts,
  and redeploy.

## Feedback Loop

- Record each report with user, timestamp, route or feature, expected behavior,
  actual behavior, severity, and whether sensitive data was involved.
- Classify issues as Tier 0 blocker, dogfood blocker, follow-up, or product
  feedback.
- Tier 0 blockers stop new invites until fixed and verified with the named
  critical suite.

## Rollback

- Use `DEPLOYMENT_ROLLBACK.md` for production rollback.
- Roll back immediately for auth lockout, billing/quota mis-accounting, data
  leakage, provider-key exposure, or sustained chat P95 above the SLO threshold
  when routing policy mitigation does not recover service.
