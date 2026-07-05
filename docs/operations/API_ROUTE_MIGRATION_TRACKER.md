# API Route Migration Tracker

This tracker records the remaining compatibility debt for the settings route
surface. It is the burn-down list for removing legacy mounts from
`apps/api/src/api/route_mounting.py` once callers no longer need them.
It follows the repository compatibility lifecycle policy in
[`docs/architecture/API_COMPATIBILITY_LIFECYCLE.md`](../architecture/API_COMPATIBILITY_LIFECYCLE.md).

## Policy

- Canonical replacements are the `/api/v1/settings/*` mounts.
- Keep legacy rows here until the last consumer has moved.
- Treat `Removal Date` as a sprint target or review date when the exact day is
  not yet locked.
- When a row reaches zero consumers, remove the duplicate mount, regenerate the
  checked-in route artifacts, and delete the row.

## Compatibility Matrix

| Legacy Route | Replacement | Consumers | Removal Date | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| `/settings/` | `/api/v1/settings/` | `apps/web/src/lib/api/providers.ts`, `apps/web/src/test/handlers.ts`, `apps/web/e2e/settings.spec.ts`, `apps/web/e2e/auth.spec.ts`, `apps/api/src/api/tests/test_settings_router.py`, `apps/api/src/api/tests/test_settings_router_additional.py` | TBD | Active | Primary dual mount for the settings index route. |
| `/settings/models/{model_name}` | `/api/v1/settings/models/{model_name}` | `apps/web/src/lib/api/providers.ts`, `apps/api/src/api/tests/test_settings_router.py`, `apps/api/src/api/tests/test_settings_router_additional.py` | TBD | Active | Model settings write path still needs the compatibility alias. |
| `/settings/providers/{provider_name}` | `/api/v1/settings/providers/{provider_name}` | `apps/web/src/lib/api/providers.ts`, `apps/api/src/api/tests/test_settings_router.py`, `apps/api/src/api/tests/test_settings_router_additional.py` | TBD | Active | Provider settings write path still needs the compatibility alias. |
| `/settings/test-connection` | `/api/v1/settings/test-connection` | `apps/web/src/lib/api/providers.ts`, `apps/api/src/api/tests/test_settings_router.py` | TBD | Active | Keep until connection-test callers no longer hit the legacy mount. |

## Burn-Down Rules

- Remove at least a couple of legacy rows every sprint when the callers are
  ready.
- Keep the tracker aligned with the route inventory and contract gates.
- When a row is ready to move, update its status to `deprecated` or `sunset`
  before removal so the lifecycle transition stays visible.
- When this table becomes empty, the `legacy/`, `compat/`, and `aliases/`
  compatibility surface should also be empty.
