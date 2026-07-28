# Feedback Loops — Closing the Learning Cycle

## Why Feedback Loops Matter

Without feedback, you have:
```
Prediction
 ↓
Decision
```

You need:
```
Prediction
 ↓
Decision
 ↓
Outcome
 ↓
Learning
```

Every decision GoblinOS makes — which department to route to, which provider to use, which tools to select, what to remember — must be followed by an observable outcome that can be used to improve future decisions.

## Core Signals

### Explicit Signals (user-initiated)

| Signal | Source | What It Tells Us |
|---|---|---|
| Thumbs up (+1) | MessageActions UI | Response was helpful |
| Thumbs down (-1) | MessageActions UI | Response was unhelpful |
| Regenerate | MessageActions UI | Response was rejected; user wants different output |
| Delete message | MessageActions UI | User actively removed the message |

### Implicit Signals (behavioral, observed automatically)

| Signal | Detection | What It Tells Us |
|---|---|---|
| Conversation continued | User sent another message after this assistant reply | Response was good enough to continue |
| Provider switched | User changed provider/model before next message | User dissatisfied with previous response's source |
| Session abandoned | User left without sending another message | Potential dissatisfaction (or task complete — correlate with positive rating) |
| Copy message | User copied response content | Response was valuable enough to reuse |
| Tool invoked | Tool was executed and returned results | Tool routing decision was correct |
| Regenerate → different provider | User regenerated and system chose different provider | Original provider selection may have been suboptimal |

## Architecture

```
User Action (thumbs up/down, regenerate, continue, switch provider)
     ↓
┌────────────────────────────────────────┐
│ FEEDBACK COLLECTOR (frontend + API)     │
│                                        │
│ Explicit: POST /api/v1/routing/feedback │
│ Implicit: Server-side event hooks       │
└────────────────┬───────────────────────┘
                 ↓
┌────────────────────────────────────────┐
│ FEEDBACK RECORDER                       │
│                                        │
│ Writes to:                              │
│ - feedback_events table (long-term)     │
│ - DomainEventModel (typed events)       │
│ - In-memory bandit state (quick update) │
└────────────────┬───────────────────────┘
                 ↓
┌────────────────────────────────────────┐
│ OUTCOME ANALYZER                        │
│                                        │
│ Correlates feedback with:               │
│ - Department selection                  │
│ - Provider chain used                   │
│ - Model selected                        │
│ - Task type / intent                    │
│ - Complexity score                      │
│ - Tool selected                         │
│ - Context assembly quality              │
└────────────────┬───────────────────────┘
                 ↓
┌────────────────────────────────────────┐
│ LEARNING APPLICATOR                     │
│                                        │
│ Updates:                                │
│ - Department routing weights            │
│ - Provider chain ordering               │
│ - Quality tier thresholds               │
│ - Thompson Sampling bandit priors       │
│ - Feature router importance weights     │
│ - User preference profiles              │
└────────────────────────────────────────┘
                 ↓
           Future Predictions
              (improved)
```

## Data Model

### `feedback_events` Table

```sql
CREATE TABLE feedback_events (
    event_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id            TEXT NOT NULL REFERENCES users(id),
    conversation_id    TEXT NOT NULL,
    message_id         TEXT NOT NULL,
    request_id         TEXT,             -- correlation to routing_events
  
    -- The feedback signal
    signal             TEXT NOT NULL,    -- 'thumbs_up', 'thumbs_down', 'regenerate', 
                                        -- 'delete', 'continue', 'provider_switch',
                                        -- 'session_abandon', 'copy'
    rating             SMALLINT,        -- +1 or -1 (for thumbs up/down)
  
    -- Context at time of signal
    department         TEXT,             -- department used for the response
    provider           TEXT,             -- provider used for the response  
    model              TEXT,             -- model used for the response
    task_type          TEXT,             -- classified task type
    intent_label       TEXT,             -- classified intent
    complexity_score   FLOAT,            -- complexity at time of response
  
    -- Previous context (for switches/comparisons)
    previous_provider  TEXT,             -- provider used before switch
    previous_model     TEXT,             -- model used before switch
  
    -- Learning application
    weight             FLOAT DEFAULT 1.0, -- importance weight for this feedback
    applied_to_bandit  BOOLEAN DEFAULT FALSE,
    applied_to_router  BOOLEAN DEFAULT FALSE,
    applied_to_profile BOOLEAN DEFAULT FALSE,
  
    -- Metadata
    metadata           JSONB DEFAULT '{}',
    created_at         TIMESTAMPTZ DEFAULT NOW(),
  
    -- Indexes
    PRIMARY KEY (event_id)
);

CREATE INDEX idx_feedback_events_user ON feedback_events(user_id, created_at DESC);
CREATE INDEX idx_feedback_events_message ON feedback_events(message_id);
CREATE INDEX idx_feedback_events_signal ON feedback_events(signal, created_at DESC);
CREATE INDEX idx_feedback_events_department ON feedback_events(department, created_at DESC);
CREATE INDEX idx_feedback_events_provider ON feedback_events(provider, created_at DESC);
```

### `message_outcomes` Table (tracking per-message behavioral signals)

```sql
CREATE TABLE message_outcomes (
    outcome_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id         TEXT NOT NULL REFERENCES messages(message_id),
    conversation_id    TEXT NOT NULL,
    user_id            TEXT NOT NULL REFERENCES users(id),
  
    -- Outcome flags (observed behavior)
    was_regenerated    BOOLEAN DEFAULT FALSE,
    was_deleted        BOOLEAN DEFAULT FALSE,
    was_copied         BOOLEAN DEFAULT FALSE,
    conversation_continued BOOLEAN DEFAULT FALSE,
    provider_switched_before_next BOOLEAN DEFAULT FALSE,
    model_switched_before_next   BOOLEAN DEFAULT FALSE,
    session_continued_duration_seconds INTEGER,  -- how long user stayed
  
    -- Correlation
    next_message_id    TEXT,             -- if continued, what was the next message
    previous_provider  TEXT,
    previous_model     TEXT,
    new_provider       TEXT,             -- if switched
    new_model          TEXT,             -- if switched
  
    -- Timestamps
    created_at         TIMESTAMPTZ DEFAULT NOW(),
    updated_at         TIMESTAMPTZ DEFAULT NOW(),
  
    PRIMARY KEY (outcome_id)
);

CREATE INDEX idx_message_outcomes_message ON message_outcomes(message_id);
CREATE INDEX idx_message_outcomes_conversation ON message_outcomes(conversation_id, created_at DESC);
```

## Signal Tracking Matrix

| Signal | Tracking Location | Collection Method | Current Status |
|---|---|---|---|
| Thumbs up/down | MessageActions.tsx | POST /routing/feedback | ✅ Implemented |
| Regenerate | useRegenerateMessage.ts | Server-side event on regenerate | 🔲 Hook needed |
| Delete | useDeleteMessage.ts | Server-side event on delete | 🔲 Hook needed |
| Copy | useCopyMessage.ts | Client-side event (no server impact) | 🔲 Track in message_outcomes |
| Conversation continued | sendMessage in useSendMessage.ts | Server detects next message after assistant | 🔲 Hook needed |
| Provider switch | QuickActions select | Server detected on next send | 🔲 Hook needed |
| Model switch | QuickActions select | Server detected on next send | 🔲 Hook needed |
| Session abandon | Presence/heartbeat | Server timeout detection | 🔲 Future |
| Tool invocation | Tool execution service | Auto-logged in usage events | 🔲 Correlation needed |

## Feedback-Driven Learning

### Thompson Sampling Bandit (existing in `ml_router.py`)

Already accepts `rating` parameter to update beta priors:
```python
bandit_cache.update(task_type, provider_id, success=None, rating=body.rating)
```

### Feature Router Weight Adaptation (existing in `feature_router.py`)

Already accepts `rating` in `record_outcome_by_request_id()`:
```python
feature_router.record_outcome_by_request_id(
    request_id=body.request_id,
    task_type=task_type,
    provider_id=provider_id,
    success=True,
    rating=body.rating,
)
```

### Preference Learner (existing in `preference_learner.py`)

Already accepts `explicit_rating`:
```python
preference_learner.record_response(
    user_id=str(user_id),
    provider_id=provider_id,
    model=None,
    intent_label=task_type or "unknown",
    completion_tokens=0,
    explicit_rating=body.rating,
)
```

### Department Router Weight Learning (planned enhancement)

The department router should learn from outcome data:
- If `reasoning` department consistently gets thumbs-down for math problems, route those to `coding` instead
- If a provider chain consistently fails, reorder the chain

## Dashboard Metrics

These metrics should be surfaced in an ops dashboard:

| Metric | Query | What It Means |
|---|---|---|
| Thumbs-up rate | `COUNT(signal='thumbs_up') / COUNT(signal IN ('thumbs_up','thumbs_down'))` | Overall satisfaction |
| Per-department satisfaction | Same, grouped by `department` | Which departments need tuning |
| Per-provider satisfaction | Same, grouped by `provider` | Which providers deliver best quality |
| Regeneration rate | `COUNT(signal='regenerate') / COUNT(assistant_messages)` | How often users reject responses |
| Continuation rate | `COUNT(conversation_continued=TRUE) / COUNT(assistant_messages)` | How engaging responses are |
| Provider-switch rate | `COUNT(provider_switched=TRUE) / COUNT(assistant_messages)` | User dissatisfaction with provider |
| Learning latency | Time from signal → model update | How fast we adapt |

## Implementation Checklist

- [x] Thumbs up/down UI (MessageActions.tsx)
- [x] POST /routing/feedback endpoint (feedback_router.py)
- [x] Bandit router rating update (ml_router.py)
- [x] Feature router outcome recording (feature_router.py)
- [x] Preference learner rating update (preference_learner.py)
- [ ] Create `feedback_events` SQLAlchemy model + Alembic migration
- [ ] Create `message_outcomes` SQLAlchemy model + Alembic migration
- [ ] Add server-side regeneration tracking (hook into message deletion/regeneration)
- [ ] Add server-side continuation tracking (detect next message after assistant)
- [ ] Add server-side provider/model switch tracking
- [ ] Add feedback event recording to existing POST /routing/feedback
- [ ] Add GET /feedback/stats endpoint for dashboard metrics
- [ ] Enhance MessageActions to track copy events
- [ ] Add feedback loop status to department router documentation
- [ ] Add dashboard view for feedback metrics

## Key Files

| File | Purpose |
|---|---|
| `docs/architecture/FEEDBACK_LOOPS.md` | This file — architecture and design |
| `apps/api/src/api/storage/feedback_models.py` | SQLAlchemy models for feedback_events + message_outcomes |
| `apps/api/src/api/services/feedback_service.py` | Feedback loop orchestration service |
| `apps/api/src/api/routing/feedback_router.py` | Enhanced feedback endpoint |
| `apps/api/src/api/pipeline/pipeline.py` | Hook outcome tracking into pipeline stages |
| `apps/web/src/features/chat/hooks/useMessages/useSendMessage.ts` | Track conversation continuation |
| `apps/web/src/features/chat/hooks/useMessages/useRegenerateMessage.ts` | Track regenerate as feedback signal |
| `apps/web/src/features/chat/hooks/useMessages/useDeleteMessage.ts` | Track delete as feedback signal |
| `apps/web/src/features/chat/components/MessageActions.tsx` | Wire up copy tracking |