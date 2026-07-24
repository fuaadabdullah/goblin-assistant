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

## Daily Driver Runtime

- Default local runtime for the dogfood loop is Docker-first backend plus native
  frontend.
- Before the first run of a new stretch, build once from a clean backend cache:
  `docker compose build --no-cache goblin-assistant-backend`.
- Start the backend stack with `make api-docker-up` and verify
  `curl http://127.0.0.1:8001/api/v1/health` before opening the frontend.
- Run the frontend with `make web-dev` after the backend health check passes.
- If the backend does not reach healthy state, treat that as an environment
  bailout. Log it, stop the ritual for that session, and do not convert the day
  into opportunistic product work.

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
- During the run, log in [FRICTION.md](../../FRICTION.md). Do not fix while
  logging. The point of the week is to observe, not to silently repair the
  experience mid-stream.
- Do not promote guesses, predictions, or prior opinions into findings. If the
  log is empty, the finding is that the log is empty.
- Keep environment bailouts separate from product friction. Note the blocked
  ritual and the failing command or health check, but do not rewrite that into a
  product brief.
- Classify issues as Tier 0 blocker, dogfood blocker, follow-up, or product
  feedback.
- Tier 0 blockers stop new invites until fixed and verified with the named
  critical suite.

## Hypotheses Under Test

- The ticker sanitization fix stays as an observed bug fix.
- Additional workflow and finance behavior changes remain shipped, but they are
  treated as hypotheses under test until real dogfood usage validates them.
- `FINANCE_ANALYST` and related prompt/archetype shaping should not be expanded
  further during the observation window unless repeated real usage clearly
  demands it.

## Rollback

- Use `DEPLOYMENT_ROLLBACK.md` for production rollback.
- Roll back immediately for auth lockout, billing/quota mis-accounting, data
  leakage, provider-key exposure, or sustained chat P95 above the SLO threshold
  when routing policy mitigation does not recover service.
