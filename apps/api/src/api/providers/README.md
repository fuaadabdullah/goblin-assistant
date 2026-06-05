# Provider Developer Guide

This package owns provider adapters, dispatcher integration, and provider-side
runtime contracts for Goblin Assistant.

If you are adding a new provider, read this before writing the adapter. The
important part is not only getting a single request to work, but fitting into
the failover, health, quota, and routing behavior that already exists.

## Core surfaces

- `contracts.py`
  - Defines the `ProviderAdapter` protocol consumed by orchestration and
    dispatch layers.
- `base.py`
  - Provides the canonical `BaseProvider` implementation, `ProviderResult`,
    `ProviderHealth`, circuit-breaker behavior, and error classification
    helpers.
- `dispatcher.py`
  - Owns provider instantiation, alias resolution, candidate ordering, warmup,
    budget-aware reranking, and debug surfaces.
- `dispatcher_pkg/execution.py`
  - Owns dispatch attempt sequencing, stream wrapping, fallback, quota
    reservation/commit/release, and registry/metrics updates.
- `provider_registry.py`
  - Maps canonical provider ids to adapter classes and converts TOML config
    into runtime config objects.

## Lifecycle expectations

### `invoke(...)`

`invoke` is the non-streaming completion path used by the dispatcher.

Requirements:

- Accept normalized chat-style input via `messages` and `prompt`.
- Return `ProviderResult(ok=True, ...)` on success.
- Return `ProviderResult(ok=False, ...)` for handled upstream failures where the
  adapter can continue normally and the dispatcher should decide whether to
  fallback.
- Raise exceptions for unexpected adapter failures, serialization problems,
  network errors that you do not want to normalize locally, or truly broken
  provider responses.

The dispatcher will:

- reserve quota before the call,
- classify and sanitize failures,
- update registry and Prometheus metrics,
- record success/failure on the provider circuit breaker,
- try the next candidate when fallback is allowed.

If the provider can determine a reliable failure category, include
`error_category` on `ProviderResult(ok=False, ...)`. Otherwise the dispatcher
will classify the error from the message or exception.

### `stream(...)`

`stream` must return an async generator that yields normal output chunks only.

Contract:

- Yield content chunks as plain stream items.
- Do not emit ad hoc `"error"` chunks as a fallback mechanism.
- If the provider fails before producing usable output, raise.
- If the provider fails after streaming has started, raise.

Why this matters:

- `dispatcher_pkg.execution.stream_wrap()` treats exceptions as stream failure.
- Once a partial stream has been emitted to the caller, dispatcher failover is
  no longer safe because another provider cannot resume the same stream in a
  coherent way.

In practice, this means:

- pre-first-chunk failure -> exception, dispatcher can mark failure cleanly,
- post-first-chunk failure -> exception, request fails in place, no fallback.

### `health_check(...)`

`health_check` should be a lightweight probe that reports whether the provider
is reachable and minimally usable.

Return `ProviderHealth` with:

- `healthy`
- `latency_ms`
- `error` when unhealthy
- `billing_issue` when the failure is quota/billing related rather than a code
  bug

The dispatcher and health monitor use this to decide inventory state and
selectability.

### `warmup(...)` and `warmup_targets()`

`BaseProvider` now exposes:

- `warmup()` for a minimal startup probe, defaulting to a one-token `ping`
  invoke
- `warmup_targets()` for provider families that should warm multiple concrete
  backends

Only override these when the default probe is wrong or too expensive.

Example use case:

- a family provider such as the self-hosted GCP adapter warms each configured
  backend individually rather than warming only the aggregate wrapper.

### `capabilities()`

`capabilities()` advertises what the provider can do. This affects discovery and
selection surfaces, not just documentation.

Current expectations:

- chat providers should expose chat/stream/health support via `BaseProvider`
  defaults unless they genuinely differ,
- embedding support should only be declared when the adapter really implements
  it,
- limits should reflect real provider limits when known.

Do not rely on model alias resolution as a substitute for accurate
capabilities/models metadata:

- alias resolution happens in the dispatcher before dispatch attempts,
- top-provider selection and inventory still depend on provider config metadata,
- TOML must still list supported capabilities and models accurately.

## Error handling and failover contract

### Return vs raise

Use this rule:

- expected upstream failure you can describe cleanly -> return
  `ProviderResult(ok=False, error=..., error_category=...)`
- unexpected adapter/runtime failure -> raise

Both paths are supported, but they lead to slightly different dispatcher
handling. The important thing is consistency.

### Circuit breaker interaction

`BaseProvider.record_failure()` and `record_success()` drive provider-local
circuit state.

Current behavior in `base.py`:

- repeated transient failures can move a provider to `soft_open`,
- auth/billing style failures can move a provider to `hard_open`,
- success resets the circuit state.

Avoid maintaining a second circuit-breaker implementation inside a concrete
adapter unless there is a clear provider-specific reason.

### Sanitization

Do not log raw credentials, tokens, or request headers directly from the
adapter. Dispatcher/provider logging now applies structured secret filtering,
and exception/user-facing error text is sanitized as a fallback. Still, the
cleanest path is to avoid binding sensitive values into logs at all.

## Configuration and registration

The single source of truth is `config/providers.toml`.

When adding a provider:

1. Add the adapter class in this package.
2. Register the canonical provider id in `provider_registry.py`.
3. Add the provider entry to `config/providers.toml`.
4. Add provider aliases or model aliases in TOML only when needed.
5. Regenerate any derived frontend/shared config artifacts if the repo workflow
   requires it.

Important config fields commonly used by the runtime:

- `endpoint` / `endpoint_env`
- `api_key_env`
- `default_model`
- `models`
- `capabilities`
- `priority_tier`
- `tier`
- `local_routing`
- `default_timeout_ms`
- `health_check_timeout_ms`

`provider_registry.py` converts the TOML source into `ProviderRuntimeConfig`,
which resolves environment-backed fields before the adapter is instantiated.

## Alias and model resolution

Dispatcher alias flow happens before dispatch:

1. provider aliases normalize input provider ids,
2. model aliases can rewrite both provider and model,
3. candidate ordering is computed from the resolved provider mode,
4. dispatch attempts run against concrete provider instances.

Implications for implementers:

- the adapter should accept the canonical provider id registered in the
  registry,
- the adapter should assume the model it receives has already passed through any
  alias rewrites,
- aliases belong in TOML, not in ad hoc adapter-specific branching unless there
  is no config-driven alternative.

## Registration checklist

Use this checklist for a new provider such as Mistral:

1. Implement the adapter class in `apps/api/src/api/providers/`.
2. Reuse `BaseProvider` unless there is a strong reason not to.
3. Add the canonical id to `DEFAULT_PROVIDER_CLASS_MAP` in
   `provider_registry.py`.
4. Add TOML config in `config/providers.toml` with accurate capabilities,
   models, priority, and env bindings.
5. Add provider/model aliases only if the public API needs them.
6. Verify:
   - provider inventory shape,
   - health endpoint behavior,
   - explicit dispatch,
   - auto/fallback behavior,
   - stream failure behavior,
   - cost/latency reporting if applicable.
7. Add focused tests:
   - adapter success/failure normalization,
   - dispatcher authority/routing coverage,
   - any provider-specific edge cases.

## Testing guidance

Prefer focused tests over broad end-to-end expansion when adding one provider.

Useful places to extend:

- `apps/api/src/api/tests/test_provider_dispatcher_authority.py`
  - dispatcher behavior, failover, sanitization, test-mode, warmup
- provider-specific tests near the adapter if the normalization logic is unique
- integration tests only when the change affects shared routing behavior across
  providers

The goal is to prove:

- the adapter conforms to `ProviderResult` / `ProviderHealth` contracts,
- failover still works,
- streams fail in the expected way,
- config registration is accurate.
