# Routing — Engine Pillar

## Purpose

The Routing pillar is the brain's dispatch system. It classifies every incoming request into a brain department, then selects and invokes the best provider from that department's configured chain, with fallback logic, circuit-breaker isolation, cost awareness, and performance warmup.

---

## Architecture

```
User Request
     │
     ▼
┌─────────────────────────────────────┐
│         routing_router.py            │  POST /api/v1/routing/route
│   DepartmentRouteRequest             │
└─────────────────┬───────────────────┘
                  │ department: "coding"
                  ▼
┌─────────────────────────────────────┐
│      department_dispatcher.py        │  DepartmentDispatcher
│   • resolve_provider_id()            │
│   • dispatch(selection, payload)      │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│      dispatcher.py (Provider)        │  ProviderDispatcher
│   • _candidate_order()               │
│   • dispatch()                       │
│   • _stream_wrap()                   │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   dispatcher_pkg/                    │
│   • routing.py — ordering, budget   │
│   • lifecycle.py — circuit breaker  │
│   • warmup.py — self-hosted preheat │
│   • execution.py — invoke + stream  │
│   • selection.py — fallback chain   │
│   • debug.py — health + inventory   │
│   • health.py — per-provider check  │
└─────────────────────────────────────┘
```

---

## Core Components

### 1. Department Registry (`departments/registry.py`)

The `DEPARTMENT_REGISTRY` singleton holds seven department policies:

| Department | ID | Primary Provider | Purpose | Supports Tools | Supports Vision |
|---|---|---|---|---|---|
| General | `general` | gpt-4o-mini | Uncategorized requests, fallback | ✓ | ✓ |
| Reasoning | `reasoning` | gpt-4o | Logic, analysis, planning, math | ✓ | ✓ |
| Coding | `coding` | claude-sonnet-4 | Code generation, debugging, review | ✓ | ✗ |
| Creative | `creative` | gpt-4o | Writing, brainstorming, content | ✓ | ✓ |
| Recall | `recall` | gpt-4o-mini | Memory retrieval, info lookup | ✗ | ✗ |
| Tools | `tool_use` | gpt-4o | Function calling, automation | ✓ | ✗ |
| Research | `research` | gemini-2.5-flash | Deep research, multi-source synthesis | ✓ | ✗ |

Each department policy defines:
- `provider_chain`: ordered list of `(provider_id, model_name)` tuples
- `specializations`: optional sub-categories for future fine-grained routing
- `default_tier`: `SPEED`, `BALANCED`, or `QUALITY`
- `max_tokens`, `temperature_default`: generation constraints
- `supports_streaming`, `supports_tools`, `supports_vision`: capability flags

### 2. Provider Dispatcher (`providers/dispatcher.py`)

The `ProviderDispatcher` is the runtime that manages provider instances, configuration, and dispatch. Key responsibilities:

#### Provider Lifecycle
- **Startup preflight**: validates configuration on construction
- **Lazy instantiation**: providers are created on first use via `_ensure_provider()`
- **Background warmup**: self-hosted providers are probed on startup to reduce cold-start latency
- **Circuit state restoration**: on restart, previous circuit-breaker states are restored from Redis

#### Routing Decisions
- `_candidate_order()`: returns providers in priority order for a given request
- `_priority_order()`: respects explicit priority tiers from config
- `_cheapest_order()`: ranks by combined input + output cost
- `_hybrid_order()`: blends priority and cost
- `_local_order()`: local/self-hosted providers first
- `top_providers_for()`: returns top N providers matching a capability, optionally preferring local or cheap

#### Budget Controls
- `_budget_status()`: checks current hourly spend against cap
- `_apply_budget_rerank()`: if over budget, re-ranks candidates by cost ascending

### 3. Circuit Breaker

Each provider has an independent circuit breaker with three states:

| State | Behavior |
|---|---|
| **Closed** | Normal operation. Requests are routed normally. |
| **Open** | Provider is bypassed for a cooldown period (configurable per provider). No requests sent. |
| **Half-Open** | After cooldown, a canary request tests recovery. Success → closed. Failure → open again. |

Circuit breaker state is persisted to Redis and restored on restart.

**Configuration** (from `config/providers.toml`):
- `circuit_breaker_threshold`: consecutive failures before opening (default: 5)
- `circuit_breaker_cooldown_seconds`: time before half-open attempt (default: 120)
- `canary_percent`: percentage of requests used as canaries in open state (default: 10%)

### 4. Model Alias Resolution

Model aliases allow users to request models by friendly names that map to concrete provider+model pairs.

Types:
- **Direct aliases**: `"gpt-4": ("openai", "gpt-4o")`
- **Pattern aliases**: regex-based, e.g. `"claude-.*": ("anthropic", "<capture>")`

Resolution happens in `ProviderDispatcher._resolve_model_alias()`:
1. Check direct alias map
2. If no match, check pattern alias map (regex)
3. If alias found, validate provider consistency
4. Return resolved `(provider_id, model_name)` tuple

### 5. Warmup

Self-hosted providers (ollama, llama.cpp, custom endpoints) are prewarmed to reduce first-request latency.

- `_prewarm_enabled`: feature flag
- `_prewarm_latency_threshold_ms`: maximum acceptable latency after warmup
- Background task sends lightweight health probes to each self-hosted endpoint
- Providers are blocked from routing until warmup completes or the threshold is met

---

## Routing Flow (Step by Step)

### Normal Path

1. Client sends `POST /api/v1/routing/route` with `{department, payload, stream}`
2. `routing_router.route_through_department()` validates the department ID
3. `DepartmentDispatcher.dispatch()` resolves the department policy and primary provider
4. `ProviderDispatcher.dispatch()` computes candidate order, checks circuit breakers, applies budget rerank
5. The primary provider is invoked (non-streaming or SSE stream)
6. On success, response is returned with provider_id, model, and usage metadata
7. On failure, the next provider in the chain is tried (fallback)

### Fallback Path

1. Primary provider returns an error classified as `auth`, `rate_limit`, `timeout`, or `server_error`
2. The error category is checked against the circuit breaker
3. If circuit breaker threshold exceeded, the provider is opened and a canary percent is set
4. The dispatcher moves to the next provider in the chain (via `_candidate_order()`)
5. Steps 1-4 repeat until a provider succeeds or the chain is exhausted
6. If all providers fail, a `500` with `All providers in chain exhausted` is returned

### Budget Rerank Path

1. Before routing, `_budget_status()` checks current hourly spend
2. If spend > 90% of cap, `_apply_budget_rerank()` re-orders candidates by cost
3. A `routing.budget_rerank` event is emitted with the original and re-ranked order
4. Normal dispatch proceeds with the re-ranked order

---

## Failure Mode Matrix

| Failure Mode | Detection | Action | Event |
|---|---|---|---|
| Provider auth error | 401/403 from provider | Fallback to next provider | `routing.provider_invoked` (success=false) → `routing.fallback_triggered` |
| Provider rate-limit | 429 from provider | Fallback to next provider | `routing.provider_invoked` (success=false) → `routing.fallback_triggered` |
| Provider timeout | Request exceeds `timeout_ms` | Fallback to next provider | `routing.provider_invoked` (success=false) → `routing.fallback_triggered` |
| Provider server error | 5xx from provider | Fallback to next provider; increment circuit counter | `routing.provider_invoked` → `routing.circuit_opened` (if threshold reached) |
| Circuit open | Provider in cooldown | Skip provider entirely | Circuit state checked in `_candidate_order()` |
| All providers exhausted | Chain empty | Return 500 | No event (terminal) |
| Budget exceeded | Hourly spend > 90% cap | Re-rank by cost | `routing.budget_rerank` |
| Invalid department | Unknown department ID | Return 404 | No event |

---

## Key Configuration

All routing configuration lives in `config/providers.toml`. Key sections:

```toml
# Provider definitions
[openai]
api_key_env = "OPENAI_API_KEY"
models = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"]
priority_tier = 1
circuit_breaker_threshold = 5
circuit_breaker_cooldown_seconds = 120
canary_percent = 10

[anthropic]
api_key_env = "ANTHROPIC_API_KEY"
models = ["claude-sonnet-4-20250514"]
priority_tier = 2

# Model aliases
[model_aliases]
"gpt-4" = { provider = "openai", model = "gpt-4o" }
"claude" = { provider = "anthropic", model = "claude-sonnet-4-20250514" }

# Budget controls
[budget]
hourly_cap_usd = 5.0

# Warmup
[warmup]
self_hosted_prewarm_enabled = true
self_hosted_latency_threshold_ms = 2000
```

---

## Testing Guidance

### Unit Tests
- `tests/contract/test_routing_contract.py`: Assert input/output shape
- `apps/api/src/api/tests/test_department_registry.py`: All 7 departments exist, provider_chain is non-empty, no provider name leakage in public listing

### Integration Tests
- `tests/integration/engine/test_routing_fallback.py`: Inject provider failure, verify fallback chain is invoked
- `tests/integration/engine/test_routing_circuit_breaker.py`: Trip circuit, verify provider is skipped, canary restores it
- `tests/integration/engine/test_routing_budget.py`: Set low cap, verify budget rerank

### Performance Tests
- `tests/performance/test_routing_latency.py`: Measure routing decision latency (target < 50ms for cache-hit, < 200ms for full dispatch)

---

## Related Documents

- `ENGINE_CONTRACTS.md` — Canonical interface contract for this pillar
- `AGENT_ARCHETYPES.md` — How departments map to agent archetypes
- `BRAIN_DEPARTMENTS.md` — The department abstraction design
- `config/providers.toml` — Single source of truth for provider config
- `apps/api/src/api/providers/dispatcher.py` — Authoritative dispatcher implementation
- `apps/api/src/api/departments/registry.py` — Department policy definitions