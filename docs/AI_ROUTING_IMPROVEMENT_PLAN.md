# AI Provider Routing - Comprehensive Improvement Plan

## Executive Summary

This document outlines a comprehensive plan to improve the Goblin Assistant's AI provider routing system for better efficiency, cost optimization, and expanded capabilities.

**Current Date:** January 11, 2026  
**Branch:** `feat/chat-kamatera-integration`

---

## Current State Assessment

### ✅ Working Infrastructure

| Provider | Endpoint | Status | Models Available |
|----------|----------|--------|------------------|
| GCP Ollama | `34.60.255.199:11434` | ✅ **HEALTHY** | `qwen2.5:3b`, `llama3.2:1b` |
| GCP llama.cpp | `34.132.226.143:8000` | ✅ **HEALTHY** | `qwen2.5-3b-instruct-q4_k_m` |
| Kamatera Server 1 | `45.61.51.220:8000` | ❌ **UNREACHABLE** | - |
| Kamatera Server 2 | `192.175.23.150:8002` | ❌ **UNREACHABLE** | - |

### Existing Components

1. **Provider Dispatcher** (`api/providers/dispatcher.py`)
   - Basic provider selection
   - Auto-selection based on API key availability
   - TOML-based configuration
   - No real-time health checks
   - No cost-aware routing

2. **Circuit Breakers** (`api/ops_router.py`)
   - Simple failure counting (threshold: 5)
   - Recovery timeout: 60 seconds
   - States: CLOSED → OPEN → HALF_OPEN
   - **NOT integrated with routing decisions**

3. **Provider Configuration** (`config/providers.toml`)
   - 15+ providers configured
   - Cost scores defined but not used
   - Bandwidth scores unused
   - Priority tiers exist but not enforced

4. **Frontend Provider Store** (`src/lib/store/provider-store.ts`)
   - Routing strategies: `round-robin`, `performance`, `latency`
   - Not connected to backend routing

---

## Issues Identified

### 🔴 Critical Issues

1. **Dead Provider References**
   - Kamatera servers (45.61.51.220:8000, 192.175.23.150:8002) are unreachable
   - Still listed as priority providers in fallback chain
   - No automatic health check to remove dead providers

2. **No Intelligent Routing**
   - Provider selection is based only on API key existence
   - Cost scores in config are never used
   - Latency preferences ignored

3. **Circuit Breakers Disconnected**
   - Circuit breaker state not checked before provider invocation
   - No automatic failover when provider is in OPEN state

4. **No Fallback Chain**
   - If selected provider fails, no automatic retry with next provider
   - Single point of failure for each request

### 🟡 Medium Issues

1. **Cost Optimization Not Implemented**
   - `max_budget_per_hour = 10.0` defined but not enforced
   - No per-request cost tracking
   - No automatic switch to cheaper providers

2. **Missing Health Monitoring**
   - No background health checks
   - Provider health only discovered on request failure
   - No latency tracking for routing decisions

3. **Capability Routing Missing**
   - All providers used interchangeably
   - No routing based on task type (code, vision, embedding)

### 🟢 Improvement Opportunities

1. **Add streaming support validation**
2. **Implement provider warm-up**
3. **Add response caching for repeated queries**
4. **Implement request batching for efficiency**

---

## Improvement Plan

### Phase 1: Fix Critical Infrastructure (Immediate)

#### 1.1 Remove Dead Providers & Fix Fallback Order

```python
# NEW: Priority order should be:
# 1. GCP Ollama (free, healthy)
# 2. GCP llama.cpp (free, healthy)
# 3. Groq (cheap, fast)
# 4. SiliconeFlow (cheap)
# 5. OpenAI (quality fallback)
# 6. Anthropic (premium fallback)
```

**Files to modify:**

- `api/providers/dispatcher.py` - Update `_auto_select_provider()`
- `config/providers.toml` - Remove/disable dead Kamatera providers

#### 1.2 Integrate Circuit Breakers with Routing

```python
# Before invoking provider, check circuit breaker
if provider_id in circuit_breakers:
    breaker = circuit_breakers[provider_id]
    if not breaker.can_execute():
        # Skip to next provider
        return await self._try_next_provider(...)
```

### Phase 2: Intelligent Routing Engine (Week 1)

#### 2.1 Create Smart Router Service

```python
# NEW FILE: api/services/smart_router.py

class SmartRouter:
    """Intelligent provider routing with health awareness."""
    
    async def select_provider(
        self,
        task_type: TaskType,
        latency_target: LatencyTarget,
        cost_priority: bool = True,
        required_capabilities: List[str] = None,
    ) -> ProviderSelection:
        """
        Select best provider based on:
        1. Health status (circuit breaker state)
        2. Real-time latency measurements
        3. Cost optimization preferences
        4. Required capabilities
        5. Current budget constraints
        """
```

#### 2.2 Implement Health Monitoring Service

```python
# NEW FILE: api/services/provider_health.py

class ProviderHealthMonitor:
    """Background service for provider health monitoring."""
    
    async def start_monitoring(self):
        """Start background health checks every 30 seconds."""
        
    async def get_healthy_providers(self) -> List[str]:
        """Return list of providers with healthy status."""
        
    async def get_provider_latency(self, provider_id: str) -> float:
        """Get average latency for provider (rolling 5-minute window)."""
```

#### 2.3 Cost-Aware Routing

```python
# NEW FILE: api/services/cost_tracker.py

class CostTracker:
    """Track and optimize AI provider costs."""
    
    # Cost per 1K tokens (input/output)
    PROVIDER_COSTS = {
        "ollama_gcp": (0, 0),           # Free (self-hosted)
        "llamacpp_gcp": (0, 0),         # Free (self-hosted)
        "groq": (0.05, 0.10),           # Very cheap
        "siliconeflow": (0.01, 0.03),   # Cheap
        "deepseek": (0.14, 0.28),       # Budget
        "openai_gpt4o_mini": (0.15, 0.60),
        "openai_gpt4o": (2.50, 10.00),
        "anthropic_sonnet": (3.00, 15.00),
        "anthropic_opus": (15.00, 75.00),
    }
    
    async def should_use_cheaper_provider(self) -> bool:
        """Check if current hour's budget is exceeded."""
        
    async def estimate_cost(self, provider: str, tokens: int) -> float:
        """Estimate cost for a request."""
```

### Phase 3: Fallback Chain Implementation (Week 1-2)

#### 3.1 Configurable Fallback Chains

```toml
# config/fallback_chains.toml

[chains.cost_optimized]
# Prioritize free/cheap providers
providers = [
    "ollama_gcp",
    "llamacpp_gcp",
    "groq",
    "siliconeflow",
    "deepseek",
    "openai",
]
max_retries = 3

[chains.quality_first]
# Prioritize quality providers
providers = [
    "openai",
    "anthropic",
    "groq",
    "deepseek",
    "ollama_gcp",
]
max_retries = 2

[chains.latency_optimized]
# Prioritize fast providers
providers = [
    "groq",
    "ollama_gcp",
    "openai",
    "anthropic",
]
max_retries = 2

[chains.code_generation]
# Best for coding tasks
providers = [
    "deepseek",      # DeepSeek Coder is excellent
    "anthropic",     # Claude great at code
    "openai",        # GPT-4 solid
    "ollama_gcp",    # qwen2.5 decent for code
]
```

#### 3.2 Automatic Failover Logic

```python
async def invoke_with_fallback(
    self,
    chain: str,
    payload: Dict,
    timeout_ms: int,
) -> Dict[str, Any]:
    """
    Invoke provider with automatic fallback chain.
    
    Returns result from first successful provider.
    Records failures to circuit breakers.
    """
    chain_config = self._get_chain(chain)
    
    for provider_id in chain_config.providers:
        # Skip unhealthy providers
        if not self.health_monitor.is_healthy(provider_id):
            continue
            
        # Skip providers with open circuit breakers
        if self._circuit_breaker_open(provider_id):
            continue
            
        try:
            result = await self.invoke_provider(provider_id, payload, timeout_ms)
            if result.get("ok"):
                self._record_success(provider_id)
                return result
            else:
                self._record_failure(provider_id)
        except Exception as e:
            self._record_failure(provider_id)
            continue
    
    return {"ok": False, "error": "all-providers-failed"}
```

### Phase 4: Capability-Based Routing (Week 2)

#### 4.1 Task Type Detection

```python
class TaskType(Enum):
    CHAT = "chat"
    CODE_GENERATION = "code"
    CODE_REVIEW = "code_review"
    REASONING = "reasoning"
    SUMMARIZATION = "summary"
    EMBEDDING = "embedding"
    IMAGE_GENERATION = "image"
    VISION = "vision"
    TRANSLATION = "translation"

async def detect_task_type(messages: List[Dict]) -> TaskType:
    """
    Analyze message content to detect task type.
    
    Uses keyword matching and simple classification.
    """
```

#### 4.2 Capability Matching

```python
PROVIDER_CAPABILITIES = {
    "ollama_gcp": ["chat", "code", "reasoning"],
    "llamacpp_gcp": ["chat", "code"],
    "groq": ["chat", "code", "reasoning"],
    "openai": ["chat", "code", "reasoning", "vision", "embedding", "image"],
    "anthropic": ["chat", "code", "reasoning", "vision"],
    "deepseek": ["chat", "code", "reasoning"],
    "siliconeflow": ["chat", "code"],
}

async def get_capable_providers(task_type: TaskType) -> List[str]:
    """Return providers capable of handling task type."""
```

### Phase 5: Analytics & Monitoring (Week 2-3)

#### 5.1 Routing Decision Logging

```python
class RoutingDecisionLog:
    """Log all routing decisions for analysis."""
    
    async def log_decision(
        self,
        request_id: str,
        task_type: TaskType,
        selected_provider: str,
        fallback_chain: List[str],
        selection_reason: str,
        latency_ms: float,
        cost_estimate: float,
        success: bool,
    ):
        """Log routing decision with full context."""
```

#### 5.2 Dashboard Metrics

New endpoints for `/ops/routing`:
- `GET /ops/routing/stats` - Routing statistics
- `GET /ops/routing/costs` - Cost breakdown by provider
- `GET /ops/routing/latency` - Latency percentiles
- `GET /ops/routing/failures` - Failure analysis
- `GET /ops/routing/decisions` - Recent routing decisions

---

## Implementation Priority

### Immediate (Do Now)

1. **Fix `dispatcher.py`** to:
   - Remove dead Kamatera references from priority list
   - Add GCP providers as primary
   - Integrate circuit breaker checks

2. **Update `providers.toml`** to:
   - Mark Kamatera providers as `is_active = false`
   - Update priority tiers for working providers

### Week 1

3. Create `smart_router.py` with basic health-aware selection
4. Create `provider_health.py` for background monitoring
5. Implement fallback chains

### Week 2

6. Add cost tracking
7. Implement capability-based routing
8. Add routing analytics

### Week 3

9. Dashboard integration
10. Performance tuning
11. Documentation

---

## New File Structure

```
apps/goblin-assistant/api/
├── services/
│   ├── smart_router.py          # NEW: Intelligent routing
│   ├── provider_health.py       # NEW: Health monitoring
│   ├── cost_tracker.py          # NEW: Cost optimization
│   └── routing_analytics.py     # NEW: Decision logging
├── providers/
│   ├── dispatcher.py            # UPDATED: Health integration
│   └── ...
├── config/
│   ├── providers.toml           # UPDATED: Fixed priorities
│   └── fallback_chains.toml     # NEW: Fallback config
└── ops/
    └── routing_router.py        # NEW: Routing analytics API
```

---

## Configuration Changes

### Updated `providers.toml` Priority Tiers

```toml
# Tier 0: Free/Local (highest priority)
ollama_gcp.priority_tier = 0
llamacpp_gcp.priority_tier = 0

# Tier 1: Very Cheap Cloud
groq.priority_tier = 1
siliconeflow.priority_tier = 1

# Tier 2: Budget Cloud
deepseek.priority_tier = 2

# Tier 3: Standard Cloud
openai.priority_tier = 3
anthropic.priority_tier = 3
google.priority_tier = 3

# Tier 99: Disabled
ollama_kamatera.priority_tier = 99  # Dead
llamacpp_kamatera.priority_tier = 99  # Dead
mock.priority_tier = 99
```

---

## Expected Benefits

### Cost Savings
- **50-80% reduction** in API costs by routing to free GCP instances first
- Automatic budget controls prevent overspending
- Real-time cost tracking enables informed decisions

### Reliability
- **99.9% uptime** through automatic failover
- Circuit breaker integration prevents cascading failures
- Health monitoring catches issues before user impact

### Performance
- **30-50% latency improvement** through smart provider selection
- Capability matching ensures best model for task
- Background health checks remove slow providers from rotation

### Observability
- Full visibility into routing decisions
- Cost breakdown by provider
- Latency tracking and SLA monitoring

---

## Next Steps

1. Review and approve this plan
2. Create feature branch `feat/smart-routing`
3. Begin Phase 1 implementation
4. Set up test environment for validation

---

*Document created: January 11, 2026*
*Author: AI Assistant*
*Status: Draft - Awaiting Review*
