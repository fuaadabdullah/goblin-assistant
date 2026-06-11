# Brain Departments — Decision Layer Architecture

## Purpose

Hide provider plumbing behind a functional decision layer. Users should never see
"I used Gemini" or "I used DeepSeek" as the product. They should feel:

- This reply was fast
- It was relevant
- It remembered the right stuff
- It picked the right tool
- It got the job done

GoblinOS acts like a **brain with departments**, not a "chat app with providers."

## Architecture

```
User Message
     ↓
┌──────────────────────────────────────────────┐
│  INTENT CLASSIFIER                            │
│  → intent label + confidence                  │
│  → task_type                                  │
└──────────────────┬────────────────────────────┘
                   ↓
┌──────────────────────────────────────────────┐
│  DEPARTMENT ROUTER (new)                      │
│  → Maps intent/task_type → Department         │
│  → Departments: REASONING, CODING, CREATIVE,  │
│    RECALL, TOOL_USE, RESEARCH, GENERAL        │
└──────────────────┬────────────────────────────┘
                   ↓
┌──────────────────────────────────────────────┐
│  DEPARTMENT DISPATCHER (new)                  │
│  → Department policy picks provider + model   │
│  → Handles fallback chain across providers    │
│  → All provider IDs stay INTERNAL             │
└──────────────────┬────────────────────────────┘
                   ↓
┌──────────────────────────────────────────────┐
│  RESPONSE CONTRACT                            │
│  → Returns: department, not provider          │
│  → Quality signals instead of model names     │
│  → Provider details ONLY in telemetry         │
└──────────────────────────────────────────────┘
```

## The Departments

| Department | Handles | Provider Chain (internal) |
|---|---|---|
| `reasoning` | Logic, analysis, math, planning | GPT-4o → Claude Sonnet → Gemini Flash |
| `coding` | Code generation, debugging, refactoring | Claude Sonnet → GPT-4o → Gemini Flash |
| `creative` | Writing, brainstorming, content | GPT-4o → Claude Sonnet → Gemini Flash |
| `recall` | Memory retrieval, context assembly | GPT-4o-mini → Gemini Flash → Claude Sonnet |
| `tool_use` | Function calling, structured actions | GPT-4o → Claude Sonnet → Gemini Flash |
| `research` | Deep research, multi-source synthesis | Gemini Flash → GPT-4o → Claude Sonnet |
| `general` | Catch-all for unclassified intent | GPT-4o-mini → Gemini Flash → Claude Sonnet |

## Key Files

### Backend (Python) — `apps/api/src/api/departments/`

| File | Purpose |
|---|---|
| `__init__.py` | Package exports |
| `models.py` | `DepartmentId`, `DepartmentPolicy`, `DepartmentSelection`, quality tiers, intent→department mapping |
| `registry.py` | `DEPARTMENT_REGISTRY` singleton with all department policies and provider chains |
| `router.py` | `DepartmentRouter.classify()` — maps intent/task_type/mode → DepartmentSelection |
| `dispatcher.py` | `DepartmentDispatcher.dispatch()` — invokes providers through the department chain with fallback |

### Frontend (TypeScript) — `apps/web/src/`

| File | Purpose |
|---|---|
| `domain/chat.ts` | `ChatMessageMeta` — added `department` and `department_reason` fields |
| `features/chat/api/index.ts` | `ChatResponse` — added `department` and `department_reason`; `SendMessageParams` — added `department` |
| `lib/api/chat.ts` | `sendConversationMessage` — passes `department` to backend; returns `department` from response |
| `lib/api/api-types.ts` | `ConversationSendResponse` — added `department` and `department_reason` fields |

### Shared — `packages/shared/src/constants/departments.ts`

| Export | Purpose |
|---|---|
| `DEPARTMENTS` | Record of department IDs with display names and descriptions |
| `DepartmentId` | Type union of all department IDs |
| `DepartmentInfo` | Interface for department metadata |
| `getDepartmentInfo()` | Lookup by ID |
| `listDepartments()` | Return all departments |
| `isValidDepartment()` | Type guard |

## API Changes

### Request Changes

```json
// Before (leaks provider)
POST /chat/conversations/{id}/messages
{ "message": "...", "provider": "openai", "model": "gpt-4" }

// After (uses department)
POST /chat/conversations/{id}/messages
{ "message": "...", "department": "reasoning" }
```

### Response Changes

```json
// Before (leaks provider)
{ "response": "...", "provider": "openai", "model": "gpt-4" }

// After (department only)
{ "response": "...", "department": "reasoning", "department_reason": "handled by reasoning" }
```

### Legacy Compatibility

- `provider` and `model` fields in requests are **deprecated** but still accepted
- If both `department` and `provider` are provided, `provider` takes precedence (transitional)
- Internal logging and telemetry still record the actual provider/model

## Streaming Changes

- SSE `complete` event: `provider` and `model` replaced with `department` and `department_reason`
- SSE `error` events: provider names removed from user-facing messages
- SSE `chunk` events: no provider info in individual chunks

## Error Message Changes

- Error messages no longer include provider names (e.g., "Authentication error" instead of "OpenAI authentication error")
- Error codes remain intact for programmatic handling
- Full provider details still logged server-side

## Department Routing Logic

The `DepartmentRouter` uses a 3-step resolution:

1. **Mode-based override**: If the request specifies a mode (e.g., `DEEP_RESEARCH`), map directly to a department
2. **Intent label mapping**: Map the intent classifier's label (e.g., `"coding"`, `"reasoning"`) to a department
3. **Fallback**: Default to `GENERAL` department

The `INTENT_TO_DEPARTMENT` mapping in `models.py` defines which intent labels map to which departments.

## Provider Chain Selection

When a department is selected, the `DepartmentDispatcher`:

1. Takes the department's `provider_chain` from the registry
2. Tries the primary provider first
3. On failure (auth, rate-limit, timeout, server error), falls through to the next provider in the chain
4. If all providers exhausted, returns a structured error

The chain order is defined in `registry.py` — edit that file to change provider assignments without touching any other code.

## Quality Tiers

Each department can select a quality tier based on the complexity score:

| Complexity | Tier | Behavior |
|---|---|---|
| 0.0–0.2 | `speed` | Fastest provider, simpler model |
| 0.2–0.4 | `economy` | Cheapest acceptable option |
| 0.4–0.7 | `balanced` | Default — good quality at reasonable latency |
| 0.7–1.0 | `quality` | Best possible output, more capable model |

## Telemetry and Monitoring

Provider details are intentionally kept in internal telemetry only:

- `decision_logger.py` — logs department selection and provider resolution
- `metrics_collector.py` — tracks latency and cost per provider (dimension: department)
- `retrieval_tracer.py` — internal tracing
- `tool_tracer.py` — internal tracing
- `circuit_breaker.py` — provider health tracking (dimension: department)
- `performance_metrics.py` — provider performance (dimension: department)

## Cost Tracking

Cost tracking systems continue to record provider and model info internally.
The department is added as a dimension for cost allocation and reporting.
Users see cost estimates but not which provider generated them.