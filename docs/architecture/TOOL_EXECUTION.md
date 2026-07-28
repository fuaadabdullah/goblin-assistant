# Tool Execution — Engine Pillar

## Purpose

The Tool Execution pillar manages the lifecycle of assistant tool calls — from receiving structured tool requests from the provider, executing them against registered skills, promoting valuable results to memory, and returning structured outputs back to the chat pipeline.

---

## Architecture

```
Provider Response (with tool_calls[])
     │
     ▼
┌─────────────────────────────────────┐
│       Chat Message Pipeline          │
│   (messages/router.py)              │
└─────────────────┬───────────────────┘
                  │ tool_calls[]
                  ▼
┌─────────────────────────────────────┐
│         Assistant Executor           │
│   (assistant_tools/executor.py)     │
│                                      │
│   For each tool_call:               │
│     1. Validate arguments            │
│     2. Run skill function            │
│     3. Check memory promotion        │
│     4. Collect result + metadata     │
└──────┬──────────────────────────────┘
       │
       ├──► Skill Registry ───► web_search()
       ├──► Skill Registry ───► academic_search()
       ├──► Skill Registry ───► research_pdf_extract()
       ├──► Skill Registry ───► citation_graph()
       └──► Skill Registry ───► verify_sources()
              │
              ▼
       ┌──────────────────┐
       │ Memory Promotion  │
       │ (if confidence    │
       │  > threshold)     │
       └──────┬───────────┘
              │ memory fact
              ▼
       ┌──────────────────┐
       │ memory_core      │
       │ _service.ingest  │
       └──────────────────┘
```

---

## Core Components

### 1. Assistant Executor (`assistant_tools/executor.py`)

The executor is the central orchestration point for all tool calls. It is invoked by the chat message pipeline after a provider returns `tool_calls[]`.

**Input**: A list of tool call objects from the provider response.

```
ToolCall {
  id: string          // tool_call_id (e.g. "call_abc123")
  type: "function"
  function: {
    name: string      // tool/skill name (e.g. "web_search")
    arguments: string // JSON string of arguments
  }
}
```

**Processing per tool call**:

1. **Validation**: Arguments are parsed from JSON and validated against the skill's schema.
2. **Execution**: The skill function is called with parsed arguments and a timeout.
3. **Memory promotion**: The result is checked for extractable content meeting the promotion threshold.
4. **Visualization extraction**: The result is checked for plottable data.
5. **Collection**: Results are batched into the output.

**Output**:

```python
ToolExecutionResult {
    tool_results: List[ToolResult]
    memory_promoted: bool
    visualization_extracted: bool
}

ToolResult {
    tool_call_id: str
    output: Dict[str, Any]  # skill-specific output shape
    error: Optional[str]
    latency_ms: float
}
```

### 2. Skill Registry

Skills are registered tools that the assistant can invoke. Each skill has a name, input schema, output schema, and implementation function.

| Skill | Tool Name | Implementation | Input | Output |
|---|---|---|---|---|
| Web search | `web_search` | `skills/research_tool.py` | query, max_results, domain_filters | results[], source_count |
| Academic search | `academic_search` | `skills/academic_search.py` | query, max_results | papers[], source_count |
| Research PDF extract | `research_pdf_extract` | `skills/research_tool.py` | path, sections | extracted_text, metadata, references |
| Citation graph | `citation_graph` | `skills/research_tool.py` | paper_id, direction | references[], citations[] |
| Source verification | `verify_sources` | `skills/research_tool.py` | sources[] | verification[], overall_confidence |

### 3. Memory Promotion Pipeline

When a tool execution returns results, the `ToolResultMemoryService` (`services/tool_result_memory_service.py`) determines whether the result should be promoted to a long-term memory fact.

**Decision criteria**:
- Result must have extractable text content
- Content confidence must exceed `MEMORY_PROMOTION_THRESHOLD` (default 0.7)
- Content must be non-trivial (not empty, not an error)

**Promotion pathway**:
1. Extract key content from the tool result
2. Call `memory_core_service.ingest_memory_fact()` with:
   - `user_id`: owning user
   - `content`: extracted text
   - `category`: derived from tool name (e.g. `"web_search"`)
   - `confidence`: computed score
   - `source_kind`: `"tool_result"`
   - `source_id`: tool call ID
3. Emit `tool.memory_promoted` event

### 4. Visualization Extraction

The executor checks if tool results contain plottable data (tables, time series, comparisons). If so, it emits a flag for the frontend to render a visualization. Currently a gap for general data-analysis sandboxing — finance-specific sandbox templates exist but general analysis tooling is pending.

---

## Tool Execution Flow (Step by Step)

### Normal Path

1. Provider returns a response with `tool_calls[]`
2. Chat message pipeline detects tool calls and routes to `AssistantExecutor`
3. Executor iterates over each tool call:
   a. Parses `function.arguments` from JSON
   b. Looks up the skill by `function.name` in the registry
   c. Executes the skill with a timeout (default 30s)
   d. Collects `ToolResult` with output or error
   e. Checks memory promotion eligibility
4. If any tool calls were made, the executor sends results back to the provider for a follow-up response
5. The follow-up response is returned to the user

### Error Path

1. A tool call fails (timeout, invalid arguments, skill error)
2. The error is captured in `ToolResult.error` — does NOT block other tool calls
3. The failed result is sent back to the provider along with successful results
4. The provider may retry, adjust, or inform the user

### Memory Promotion Path

1. Successful tool result meets the promotion threshold
2. `extract_and_promote()` extracts content and calls `memory_core_service`
3. A `memory.fact_ingested` event is emitted
4. `memory_promoted: true` is set in the executor output

---

## Safety Controls

| Control | Implementation |
|---|---|
| Input sanitization | All tool arguments pass through `InputSanitizer` before execution |
| Timeout | Each tool call has a configurable timeout (default 30s, configurable via `TOOL_TIMEOUT_SECONDS`) |
| Error isolation | A failure in one tool does not affect other tools in the same batch |
| Rate limiting | Individual skill functions may apply their own rate limiting |
| Content filtering | Tool outputs are sanitized before being returned to the provider |

---

## Key Configuration

```python
# From environment / config
TOOL_TIMEOUT_SECONDS = 30          # Default timeout per tool call
MEMORY_PROMOTION_THRESHOLD = 0.7   # Minimum confidence for auto-promotion
MAX_TOOL_CALLS_PER_TURN = 10       # Maximum tool calls per response
```

---

## Testing Guidance

### Unit Tests
- `tests/contract/test_tool_execution_contract.py`: Assert input/output shape
- Test each skill function with valid and invalid inputs
- Test memory promotion logic with varying confidence thresholds

### Integration Tests
- `tests/integration/engine/test_tool_execution.py`: Execute a tool, verify result shape
- `tests/integration/engine/test_tool_failure_isolation.py`: Run one failing and one succeeding tool, verify success is returned
- `tests/integration/engine/test_tool_memory_promotion.py`: Execute with confidence above threshold, verify memory fact created

### Performance Tests
- `tests/performance/test_tool_execution_latency.py`: Measure tool call latency (target < 100ms for cache-hot skills, < 5s for network-bound skills)

---

## Related Documents

- `ENGINE_CONTRACTS.md` — Canonical interface contract for this pillar
- `AGENT_ARCHETYPES.md` — How tools map to agent capabilities
- `apps/api/src/api/assistant_tools/executor.py` — Executor implementation
- `apps/api/src/api/assistant_tools/skills/` — Skill implementations
- `apps/api/src/api/services/tool_result_memory_service.py` — Memory promotion