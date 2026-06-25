# API Contract Matrix

This matrix tracks the high-risk frontend/backend surfaces that matter for launch.
It is intentionally narrow: auth, account, sandbox, support, and admin navigation.

| Surface | Frontend entrypoint | Backend endpoint | Status | Notes |
| --- | --- | --- | --- | --- |
| Auth: login/register/logout/validate | `apps/web/src/lib/api/auth.ts` | `/api/v1/auth/login`, `/api/v1/auth/register`, `/api/v1/auth/logout`, `/api/v1/auth/validate` | Implemented | `validateToken()` uses the Next proxy at `/api/auth/validate`; the rest hit backend API routes directly. |
| Auth: passkey | `apps/web/src/lib/api/auth.ts` | `/api/v1/auth/passkey/challenge`, `/api/v1/auth/passkey/register`, `/api/v1/auth/passkey/auth` | Implemented | Contract exists in the frontend client and generated OpenAPI. |
| Auth: Google sign-in | `apps/web/src/lib/api/auth.ts` | `/api/v1/auth/google/url`, `/api/v1/auth/google`, `/api/v1/auth/google/callback` | Implemented | Browser flow is fronted by the API client and backend auth routes. |
| Account | `apps/web/src/lib/api/account.ts` | `/api/v1/account/profile`, `/api/v1/account/preferences` | Implemented | Both save paths are direct backend calls. |
| Sandbox | `apps/web/src/lib/api/sandbox.ts` | `/api/v1/sandbox/jobs`, `/api/v1/sandbox/jobs/{job_id}/logs`, `/api/v1/sandbox/run` | Implemented | The frontend client is aligned with the generated SDK and now speaks the job-backed run/log flow. |
| Support | `apps/web/src/lib/api/support.ts` | `/api/v1/support/message`, `/api/v1/support/triage` | Implemented | Support message + triage paths are direct backend calls. |
| Admin navigation and provider ops | `apps/web/src/components/Navigation.tsx`, `apps/web/src/screens/*`, `apps/web/src/features/admin/providers/*` | `/api/v1/settings/*`, `/api/v1/routing/*`, `/api/v1/admin/providers/state` | Implemented | The browser-facing admin screens are backed by the general settings/routing client. The provider-state snapshot exists as an ops-only route and is intentionally `include_in_schema=False`, so it does not appear in the generated OpenAPI. |
| Coverage policy | `apps/web/vitest.config.ts`, `tooling/quality/run-critical-coverage.sh` | `apps/api/pyproject.toml` | Implemented | Web coverage thresholds live in one Vitest config; backend coverage gate lives in `pyproject.toml`. I did not find a second frontend threshold file during this pass. |

## Current Observations

- The contract surface for auth, account, sandbox, and support is present in both the frontend API client and the generated OpenAPI.
- The admin UI is implemented through the general settings/routing API surface, while the provider-state snapshot is exposed through an ops-only hidden route at `/api/v1/admin/providers/state`.
- The web coverage threshold is centralized in `apps/web/vitest.config.ts`; the backend coverage gate is in `apps/api/pyproject.toml`.
