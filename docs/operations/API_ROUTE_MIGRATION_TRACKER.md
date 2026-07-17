# API Route Migration Tracker

This tracker records the remaining compatibility debt for the settings route
surface. It is the burn-down list for removing legacy mounts from
`apps/api/src/api/route_mounting.py` once callers no longer need them.
It follows the repository compatibility lifecycle policy in
[`docs/architecture/API_COMPATIBILITY_LIFECYCLE.md`](../architecture/API_COMPATIBILITY_LIFECYCLE.md).
It is transitional by design and should eventually be generated from route
inventory plus runtime usage.

## Policy

- Canonical replacements are the `/api/v1/settings/*` mounts.
- Keep legacy rows here until the last consumer has moved.
- Treat `Removal Date` as a sprint target or review date when the exact day is
  not yet locked.
- When a row reaches zero consumers, remove the duplicate mount, regenerate the
  checked-in route artifacts, and delete the row.
- Preserve the compatibility dashboard as generated output rather than a
  manually curated matrix once usage telemetry is available.

## Compatibility Matrix

| Legacy Route | Replacement | Consumers | Removal Date | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| `/settings/models/{model_name}` | `/api/v1/settings/models/{model_name}` | `apps/web/src/lib/api/providers.ts`, `apps/api/src/api/tests/test_settings_router.py`, `apps/api/src/api/tests/test_settings_router_additional.py` | TBD | Active | Model settings write path still needs the compatibility alias. |
| `/settings/providers/{provider_name}` | `/api/v1/settings/providers/{provider_name}` | `apps/web/src/lib/api/providers.ts`, `apps/api/src/api/tests/test_settings_router.py`, `apps/api/src/api/tests/test_settings_router_additional.py` | TBD | Active | Provider settings write path still needs the compatibility alias. |
| `/settings/test-connection` | `/api/v1/settings/test-connection` | `apps/web/src/lib/api/providers.ts`, `apps/api/src/api/tests/test_settings_router.py` | TBD | Active | Keep until connection-test callers no longer hit the legacy mount. |

## Follow-Up Plan

The legacy `/settings/` backend mount was retired on 2026-07-17. Keep callers on
`/api/v1/settings/*` and treat any new unversioned backend route mount as contract drift.
- Update the route inventory and SDK artifacts to keep the legacy alias out of the checked-in contract.
- Re-run the settings and route-alias smoke tests to confirm only `/api/v1/settings/*` remains.
- Leave the remaining sub-route rows above in place until their own callers are retired.

## Burn-Down Rules

- Remove at least a couple of legacy rows every sprint when the callers are
  ready.
- Keep the tracker aligned with the route inventory and contract gates.
- When a row is ready to move, update its status to `deprecated` or `sunset`
  before removal so the lifecycle transition stays visible.
- When this table becomes empty, the `legacy/`, `compat/`, and `aliases/`
  compatibility surface should also be empty.
