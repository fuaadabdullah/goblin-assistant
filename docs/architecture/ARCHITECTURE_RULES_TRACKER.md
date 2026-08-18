# Architecture Rules Tracker

This is a historical burn-down snapshot for architecture-rule debt. It is not
release evidence. Use `make architecture-evidence` and inspect
`artifacts/architecture-evidence.json` for the canonical current report.

Note: the older `docs/tech-debt-report.md` snapshot from 2026-07-17 is stale for
the current workspace. The counts below come from a live local scan on 2026-07-29.

## Snapshot

- Boundary violations: 3
- Circular dependencies: 2
- Capability violations: 1

## Boundary Violations

| File | Line | Rule | Detail |
| --- | ---: | --- | --- |
| `apps/api/src/api/chat_router/schemas.py` | 43 | `parse-error` | `api.chat_router.schemas` has invalid syntax: invalid syntax |
| `apps/api/src/api/chat_router/service_accessors.py` | 31 | `parse-error` | `api.chat_router.service_accessors` has invalid syntax: expected an indented block after function definition on line 30 |
| `apps/api/src/api/sandbox_api.py` | 9 | `parse-error` | `api.sandbox_api` has invalid syntax: invalid syntax |

## Circular Dependencies

| File | Line | Rule | Detail |
| --- | ---: | --- | --- |
| `apps/api/src/api` | 1 | `no-circular-dependencies` | `api.chat_router.messages -> api.chat_router.streaming -> api.chat_router.messages` |
| `apps/api/src/api` | 1 | `no-circular-dependencies` | `api.integrations.secrets.auth -> api.integrations.secrets.vault_adapter -> api.integrations.secrets.auth` |

## Capability Violations

| File | Line | Rule | Detail |
| --- | ---: | --- | --- |
| `apps/api/src/api/chat_router/messages/stages.py` | 67 | `capability-allowed-deps` | `api.chat_router.messages.stages` (`chat`) imports `api.agents.dispatcher`, which is outside allowed dependency prefixes |

## Notes

- The boundary checker currently reports parser blockers before it can surface
  any import-boundary drift in the affected files.
- The capability checker currently hits a syntax error in
  `apps/api/src/api/sandbox_api.py`; that file is not counted as a capability
  violation here because the parser never reaches the import analysis stage.
- Keep this tracker aligned with the live checks until the backlog is at zero.
