# GoblinOS Request Pipeline Architecture

**Implemented:** 2026-06-10  
**Module:** `apps/api/src/api/pipeline/`

---

## Overview

Every message flows through a 4-stage pre-provider pipeline before reaching the LLM. None of the intermediate stages require a GPU or external API call — they are keyword classifiers, cosine similarity, Thompson Sampling, and weighted scoring tables.

```
User
 ↓
Intent Model       ← keyword classifier + cosine similarity        (no GPU)
 ↓
Memory Model       ← 5-layer context assembly (vector retrieval)   (no GPU)
 ↓
Routing Model      ← Thompson Sampling bandit                      (lightweight ML)
 ↓
Tool Selection     ← intent-weighted scoring table                 (pure Python)
 ↓
Provider           ← LLM call (Anthropic, OpenAI, Gemini, …)
 ↓
Response
```

---

## Stage 1 — Intent Model

**File:** `apps/api/src/api/routing/intent_classifier.py`

Classifies the user's message into one of 8 intent labels using keyword matching and cosine similarity over prototype vectors:

| Label | Description |
|-------|-------------|
| `coding` | Code generation, debugging, shell commands |
| `research` | Web search, academic papers, fact-finding |
| `finance` | Market data, portfolio, financial analysis |
| `agent_task` | Multi-step tasks, automation, scheduling |
| `business` | Strategy, operations, business analysis |
| `creative` | Writing, brainstorming, design |
| `reasoning` | Math, logic, complex analysis |
| `chat` | General conversation (no tools needed) |

Returns `IntentResult(label, confidence)`. Low confidence degrades downstream tool selection scores.

---

## Stage 2 — Memory Model

**File:** `apps/api/src/api/services/context_assembly_service/`

5-layer context assembly:

1. Recent conversation history (last 10 turns)
2. User long-term memory (vector search)
3. Document/attachment context
4. Workspace context (projects, tasks)
5. System context (date, user preferences)

Produces `assembled_context` injected into the system prompt. Controlled per-request by `enable_context_assembly` flag.

---

## Stage 3 — Routing Model

**File:** `apps/api/src/api/services/smart_router.py`

Thompson Sampling multi-armed bandit (`ML_BANDIT` strategy):

- Maintains beta distribution priors per provider+task_type pair
- Samples from priors at routing time (exploration/exploitation balance)
- Updates on success/failure with Bayesian posterior update
- Returns `ProviderSelection(provider_id, model, reason, fallback_chain)`

---

## Stage 4 — Tool Selection

**File:** `apps/api/src/api/pipeline/tool_selection.py`

Pure Python scoring table — no ML framework, no network call.

Scoring formula: `final_score = base_score × (0.5 + 0.5 × confidence)`

Low confidence halves the effective score. Threshold = 0.50.

Intent→category weights (excerpt):

| Intent | Top categories |
|--------|---------------|
| `coding` | terminal (0.90), files (0.80), git (0.75), github (0.65) |
| `research` | web (0.95), academic (0.85), research (0.80), memory (0.70) |
| `finance` | finance (0.95), web (0.65), memory (0.60) |
| `agent_task` | terminal (0.90), tasks (0.85), web (0.80), files (0.75) |
| `chat` | *(empty — no tools for pure conversation)* |

---

## Pipeline Carrier

**File:** `apps/api/src/api/pipeline/context.py`

`PipelineContext` is a typed dataclass that carries all signals from stage to stage:

```python
@dataclass
class PipelineContext:
    user_id: str
    conversation_id: str
    raw_message: str
    sanitized_message: str

    # Stage 1
    intent: Optional[IntentResult]
    task_type: Optional[str]
    complexity_score: float

    # Stage 2
    assembled_context: str
    context_metadata: Dict[str, Any]

    # Stage 3
    selected_provider: Optional[str]
    selected_model: Optional[str]
    fallback_chain: List[str]

    # Stage 4
    tool_candidates: List[str]
    tool_schemas: List[Dict[str, Any]]

    # Health
    pipeline_error: Optional[str]
    used_fallback: bool
```

---

## Error Handling

`RequestPipeline.run()` **never raises**. Each stage is wrapped in `try/except`:

- On stage failure: sets `ctx.used_fallback = True`, logs a warning, and continues
- Caller always receives a `PipelineContext` with whatever partial data is available
- Provider dispatch proceeds even if all 4 stages failed (degraded mode)

---

## Integration Point

The pipeline is called from `apps/api/src/api/chat_router/messages/router.py`:

```python
pipeline_ctx = await _messages_pkg._get_request_pipeline().run(
    raw_message=request.message,
    sanitized_message=sanitized_message,
    user_id=str(current_user.id),
    conversation_id=conversation_id,
    history_messages=history_messages,
    intent_result=_intent_result,       # pre-classified to avoid duplicate work
    preferred_provider=request.provider,
    preferred_model=request.model,
    enable_context_assembly=request.enable_context_assembly,
)
```

---

## Related Modules

| File | Role |
|------|------|
| `pipeline/__init__.py` | Package exports |
| `pipeline/context.py` | PipelineContext carrier |
| `pipeline/pipeline.py` | RequestPipeline orchestrator |
| `pipeline/tool_selection.py` | ToolSelectionModel |
| `chat_router/service_accessors.py` | `_get_request_pipeline()` factory |
| `providers/dispatcher_utils.py` | CircuitBreaker, LoadBalancer, MetricsCollector |
| `services/write_time_intelligence.py` | Write-time decision engine (canonical name) |
| `services/write_time_matrix.py` | Backward-compat shim → write_time_intelligence |
