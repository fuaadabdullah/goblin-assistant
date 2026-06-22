# Memory — Engine Pillar

## Purpose

The Memory pillar provides context-aware intelligence by assembling relevant information from multiple sources — long-term memory, working memory, semantic retrieval, and ephemeral conversation state — into structured prompt layers. It ensures the assistant remembers user preferences, prior conversations, and relevant facts across sessions.

---

## Architecture

```
Chat Request with query + conversation_id
     │
     ▼
┌─────────────────────────────────────────────────┐
│            ContextOrchestrator                    │
│   assemble_context(query, conversation_id,        │
│                   history, user_id)               │
└──────┬──────────┬──────────┬──────────┬─────────┘
       │          │          │          │
       ▼          ▼          ▼          ▼
┌─────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ Long-   │ │ Working  │ │ Semantic │ │Ephemeral │
│ term    │ │ Memory   │ │Retrieval │ │ Memory   │
│ Memory  │ │(current  │ │(pgvector │ │(recent   │
│ (memory │ │conversa- │ │ similarity│ │conversa- │
│ _core)  │ │tion msgs)│ │ search)  │ │tion hist)│
└─────────┘ └──────────┘ └──────────┘ └──────────┘
     │          │          │          │
     └──────────┴──────────┴──────────┘
                    │
                    ▼
          ┌─────────────────┐
          │ System Prompt   │ (always included, unbudgeted)
          │ + Assembled     │
          │ Context Layers  │ (token-budgeted)
          └────────┬────────┘
                   │
                   ▼
          Provider Invocation
```

---

## Core Components

### 1. Context Orchestrator (`services/context_orchestrator.py`)

The orchestrator is the central assembly point. It accepts a `ContextBudget` defining per-layer token limits and returns a structured context with layers, token usage, and degradation metadata.

**Context Budget** (from `config/system_config.py`):

| Parameter | Default | Purpose |
|---|---|---|
| `long_term_tokens` | 300 | Long-term memory facts |
| `working_memory_tokens` | 700 | Current conversation state |
| `semantic_retrieval_tokens` | 1200 | Vector search results |
| `ephemeral_tokens` | 500 | Recent message history |

**Assembly order** (fixed, cannot be reordered):

1. **System layer** — always included, not subject to token budget
2. **Long-term memory** — from `memory_core_service` (pgvector-backed)
3. **Working memory** — from active conversation state (requires `conversation_id`)
4. **Semantic retrieval** — from pgvector similarity search across all source types
5. **Ephemeral memory** — from recent conversation history (requires `history` parameter)

### 2. Memory Fact Lifecycle

Memory facts are persistent, semantically searchable items stored in the `embeddings` pgvector table with `source_type='memory'`.

```
Ingestion Pipeline:

Tool Result / User Input
     │
     ▼
┌──────────────────────────────┐
│ MemoryCoreService            │
│   ingest_memory_fact()       │  ← explicit storage
│   ingest_text()              │  ← from search index
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│ pgvector embeddings table     │
│ source_type='memory'         │
│ content, category, confidence │
│ user_id, created_at          │
└──────────────────────────────┘

Promotion Pipeline:

Tool Execution Result
     │
     ▼
┌──────────────────────────────┐
│ Tool Result Memory Service   │
│   extract_and_promote()      │
│   • confidence > threshold?  │  (MEMORY_PROMOTION_THRESHOLD = 0.7)
│   • content extractable?     │
└──────────┬───────────────────┘
           │ (if yes)
           ▼
┌──────────────────────────────┐
│ memory_core_service          │
│   ingest_memory_fact()       │
└──────────────────────────────┘

Retrieval Pipeline:

Query
     │
     ▼
┌──────────────────────────────┐
│ RetrievalSingleton           │
│   get_context_bundle()       │  ← all sources
│   retrieve_memory_facts()    │  ← memory only
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│ pgvector cosine similarity   │
│ WHERE user_id = ?            │
│ ORDER BY embedding <=> ?     │
│ LIMIT k                      │
└──────────────────────────────┘
```

### 3. Context Bundle (`semantic_chat_router.py`)

The context bundle is the output of a retrieval query, containing:

| Field | Source | Purpose |
|---|---|---|
| `summaries` | Conversation summaries | Pre-computed conversation digests |
| `messages` | Messages table | Recent or relevant message history |
| `ephemeral_messages` | Ephemeral store | Temporary context (not persisted) |
| `tasks` | Task store | Active or relevant tasks |
| `memory_facts` | Memory core | Long-term facts, preferences, learnings |
| `total_tokens` | Calculated | Sum of all layer tokens |
| `retrieved_at` | Timestamp | When the retrieval happened |

### 4. pgvector Indexes

All vector indexes live in the `embeddings` table, keyed by `source_type`:

| Source Type | Content | Used By |
|---|---|---|
| `memory` | Memory facts, user preferences | `memory_core_service` |
| `document` | Uploaded documents | Search router |
| `code` | Code snippets | Search router |
| `research` | Research notes | Search router |
| `task` | Task descriptions | Search router |
| `message` | Conversation messages | Semantic chat |

Each row stores:
- `id`: UUID primary key
- `source_type`: discriminator for the index
- `source_id`: optional reference to the source record
- `user_id`: owning user
- `content`: text content
- `embedding`: vector (1536 dimensions for OpenAI text-embedding-ada-002)
- `metadata`: JSON blob for structured filtering
- `created_at`: creation timestamp
- `expires_at`: optional TTL for ephemeral entries

### 5. Raptor Summarization

Raptor provides tree-structured conversation summarization for long-running threads. It recursively summarizes conversation chunks and stores the summaries as retrievable context items.

- Endpoint: `POST /api/v1/raptor/start`
- Status: `GET /api/v1/raptor/status`
- Logs: `GET /api/v1/raptor/logs`

When enabled, Raptor runs as a background process that:
1. Chunks long conversations into segments
2. Summarizes each segment
3. Recursively summarizes the summaries into a tree
4. Stores the leaf and node summaries in the retrieval index

---

## Memory Flow (Step by Step)

### Context Assembly

1. `semantic_chat_router.semantic_send_message()` receives a message with `conversation_id`
2. The router loads recent conversation history from `conversation_store`
3. The `ContextOrchestrator` is called with the budget and optional context
4. Each layer function is called in order:
   - `assemble_long_term_memory()`: queries `memory_core_service` for user facts
   - `assemble_working_memory()`: formats current conversation messages
   - `assemble_semantic_retrieval()`: queries pgvector for semantically similar content
   - `assemble_ephemeral_memory()`: formats recent conversation history as context
5. Each layer is truncated if it exceeds its token budget
6. The assembled context is injected into the system prompt
7. The provider is invoked with the enhanced messages

### Memory Fact Search

1. `GET /api/v1/semantic-chat/users/{user_id}/memory/search?query=...`
2. `RetrievalSingleton.retrieve_memory_facts()` embeds the query
3. Performs cosine similarity search on the `embeddings` table with `source_type='memory'` and matching `user_id`
4. Returns top-k facts with content, category, confidence, and source metadata

---

## Degradation Modes

| Failure | Behavior | Signal |
|---|---|---|
| Semantic retrieval fails | Orchestrator returns minimal context (system only) | `degraded_mode: true`, `degraded_reason: "semantic retrieval failed"` |
| Long-term memory fails | Layer skipped gracefully, other layers remain | Layer omitted from `layers[]` array |
| Working memory unavailable | Layer skipped if no `conversation_id` provided | Working memory omitted from output |
| Ephemeral memory unavailable | Layer skipped if no `history` provided | Ephemeral memory omitted from output |
| Single layer error (non-catastrophic) | System + semantic layers still assembled | `degraded_mode: false`, layer errors logged |
| Multiple layers fail | System-only context returned | `degraded_mode: true`, combined error reasons |

---

## Key Configuration

```python
# From config/system_config.py
config = {
    "memory": {
        "promotion_threshold": 0.7,      # Minimum confidence for auto-promotion
        "max_memory_items": 100,          # Max memory facts per user
        "memory_retention_days": 30,      # TTL for memory facts
    },
    "context_assembly": {
        "long_term_tokens": 300,          # Token budget for long-term memory
        "working_memory_tokens": 700,     # Token budget for working memory
        "semantic_retrieval_tokens": 1200,# Token budget for semantic search
        "ephemeral_tokens": 500,          # Token budget for ephemeral context
        "retrieval_timeout_seconds": 30,  # Timeout for retrieval operations
        "semantic_similarity_threshold": 0.7,  # Minimum similarity for inclusion
    }
}
```

---

## Testing Guidance

### Unit Tests
- `tests/contract/test_memory_contract.py`: Assert context bundle shape
- `apps/api/src/api/tests/test_context_assembly_coverage.py`: Budget enforcement, layer ordering, degradation

### Integration Tests
- `tests/integration/engine/test_memory_retrieval.py`: Store a fact, retrieve it by semantic similarity
- `tests/integration/engine/test_memory_promotion.py`: Execute tool, verify result is promoted to memory
- `tests/integration/engine/test_memory_degradation.py`: Disable pgvector, verify graceful degradation

### Performance Tests
- `tests/performance/test_memory_retrieval_latency.py`: Context assembly latency (target < 500ms for full assembly)

---

## Related Documents

- `ENGINE_CONTRACTS.md` — Canonical interface contract for this pillar
- `AGENT_ARCHETYPES.md` — How memory feeds into agent context windows
- `apps/api/src/api/semantic_chat_router.py` — Semantic chat endpoints
- `apps/api/src/api/services/memory_core.py` — Memory core service
- `apps/api/src/api/search_router.py` — pgvector-backed search
- `apps/api/src/api/raptor_router.py` — Raptor summarization