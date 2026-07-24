# Provider Dispatch Incident Response Runbook

Use this runbook when chat/completion requests are failing, degraded, or
routing to unexpected providers.

## 1. Confirm Scope

1. Check `GET /api/v1/providers/models` for the canonical provider
   inventory — `dispatcher.get_provider_inventory()` reports each
   provider's configured/healthy/selectable state. (`/api/v1/routing/providers`
   also returns provider IDs but is deprecated — prefer `providers/models`.)
   `GET /api/v1/routing/health` and `/api/v1/routing/health/{provider_id}`
   give per-provider health/analytics detail.
2. Determine scope:
   - Single provider degraded (others still serving traffic normally), or
   - Broad routing failure (most/all requests failing).
3. Check `GET /health/all` for a system-wide view before assuming the
   issue is provider-specific.

## 2. Per-Provider Circuit Breaker State

Each provider (`api.providers.base.BaseProvider`) tracks its own circuit
breaker state independently: `closed` → `soft_open` → `hard_open`.

1. A provider in `soft_open` is still attempted but deprioritized in
   ranking; `hard_open` means the dispatcher stops routing to it entirely
   until the breaker's cooldown elapses.
2. `record_failure()` trips the breaker; a provider recovers automatically
   once its failure window passes and a subsequent call succeeds — there
   is no manual "reset" endpoint. If a provider is stuck open longer than
   expected, check whether the underlying failure (bad API key, quota
   exhaustion, upstream outage) is actually resolved before assuming the
   breaker itself is broken.
3. `api.services.provider_health` and `api.providers.dispatcher_pkg.execution`
   auto-file Jira incidents via `api.ops.integrations.jira` on circuit-breaker
   trips and provider health degradation — check Jira first; the
   auto-filed ticket often already has the failing provider ID, error
   category, and timestamp.

## 3. Routing Decisions Look Wrong

If requests are reaching a provider but it's the *wrong* one:

1. Routing strategy (cost/latency/hybrid/ML-bandit) lives in
   `api.routing.router` (a façade over `policy_engine.py`,
   `router_registry.py`, `selection.py`) — check which strategy is active
   via the routing config, not the dispatcher.
2. `api.routing.learning_adapters` is the seam between routing decisions
   and the bandit/feature-router learning state (`ml_router`,
   `feature_router`) — if ranking seems to have drifted, check whether
   recent negative feedback (`routing/feedback_router.py`) skewed the
   bandit state for a provider, rather than assuming routing config
   changed.
3. `RoutingRegistryStore` persists provider stats to a SQLite file at
   `ROUTING_REGISTRY_DB_PATH` (or `<cwd>/routing_registry.db` if unset) —
   if this file is corrupted or unwritable (e.g. under a read-only root
   filesystem with no volume mounted), registry flushes fail silently and
   log `routing_registry_flush_failed`; check application logs for that
   event before assuming a routing logic bug.

## 4. Provider Leakage / Import Errors

If a deploy fails at import time with an unfamiliar `ImportError` in
`api.providers.*`:

1. `make check-capability-boundaries` enforces which modules may import
   concrete provider classes (`global_provider_import_owner_prefixes` in
   `apps/api/architecture-capabilities.json`). A new provider composite
   or registry module needs to be added to that list, not worked around
   with a local import.
2. `provider_registry.py`'s `DEFAULT_PROVIDER_CLASS_MAP` is the single
   source of truth for provider-id → class wiring — a missing/renamed
   entry there is the most common cause of "unknown provider" errors at
   dispatch time.

## Notes

- `make check-api-cycles` currently reports 9 undocumented circular
  dependencies clustered around `api.routing.*`/`api.providers.dispatcher`
  (see `docs/tech-debt-report.md` §3.2) — these are known and pre-existing,
  not a signal of a new regression, but be aware of them if a stack trace
  shows an unexpected import order during startup.
- `docker-socket-proxy` handles sandbox code execution, not provider
  dispatch — don't confuse the two failure domains (see
  `SANDBOX_README.md` for sandbox-specific triage).
