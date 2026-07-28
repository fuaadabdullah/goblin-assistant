# Memory System Documentation

Complete reference for the memory system's behavior, architecture, and troubleshooting.

## Quick Navigation

### For Understanding How It Works
- **[MEMORY_STATE_TRANSITIONS.md](./MEMORY_STATE_TRANSITIONS.md)** — State definitions, transition rules, failure scenarios
  - Read this first to understand the state machine
  - Why facts transition between states
  - What each state means for inference

- **[MEMORY_CORE_SERVICE.md](./MEMORY_CORE_SERVICE.md)** — API reference and ingestion pipeline
  - How to ingest, retrieve, and update memories
  - Normalization and deduplication
  - Service methods and contracts

### For Debugging & Troubleshooting
- **[MEMORY_TROUBLESHOOTING.md](./MEMORY_TROUBLESHOOTING.md)** — Diagnostic guides and recovery steps
  - "Why isn't this fact being used?"
  - "Why did this fact get demoted?"
  - "Two facts contradict — which wins?"
  - Recovery procedures

### For Implementation Details
- **[SCORING.md](./SCORING.md)** — Confidence and importance calculation
  - How confidence scores are computed (weighted formula)
  - How importance scores are derived
  - Confidence bands and band transitions

- **[OBSERVABILITY.md](./OBSERVABILITY.md)** — Monitoring and alerting
  - State transition alerts
  - Contradiction detection logs
  - Memory health metrics

---

## The State Machine at a Glance

```
CANDIDATE → ACTIVE → VERIFIED
   ↓          ↓         ↓
   └─────DEPRECATED←────┘
            ↓
        ARCHIVED (user-initiated, reversible)
            ↓
        DELETED (terminal)
```

**Key facts:**
- CANDIDATE: Low confidence, not used
- ACTIVE: Ready for inference
- VERIFIED: User-validated, highest priority
- DEPRECATED: Contradicted by better fact, never returns to ACTIVE
- ARCHIVED: User removed, can be restored
- DELETED: Permanent removal

---

## Core Rules (Read These First)

1. **Confidence Gate:** Confidence < 0.45 blocks promotion to ACTIVE unless pinned or user-promoted
2. **Repetition Gate:** Fact needs to appear at least once to trigger automatic ACTIVE
3. **Direct Correction:** User provides explicit correction → VERIFIED (atomic, skips ACTIVE)
4. **Contradiction:** New fact contradicts existing → demote to DEPRECATED (irreversible)
5. **Terminal States Win:** In merge conflicts, DEPRECATED/ARCHIVED/DELETED always win
6. **Pinning Bypasses Gates:** Pinned facts go directly to ACTIVE regardless of confidence

---

## Troubleshooting Flowchart

**"Why isn't my fact being used?"**
```
1. Is state CANDIDATE, DEPRECATED, ARCHIVED, or DELETED?
   → YES: See MEMORY_TROUBLESHOOTING.md, "Why isn't this fact being used?"
   → NO: Continue

2. Is state ACTIVE or VERIFIED?
   → YES: Should be used. Check retrieval ranking or context limits.
   → NO: Unexpected state. Check logs.

3. Check confidence:
   - < 0.45: CANDIDATE gate blocking. See "High-confidence fact stuck in CANDIDATE"
   - >= 0.45: Check repetition. If rep < 1, needs to appear again.
   - >= 0.45 & rep >= 1: Should be ACTIVE. Check derivation logic.
```

---

## State Transition Decision Tree

**When a memory fact is ingested:**

```
1. Is it a direct correction?
   → YES: → VERIFIED (skip intermediate states)
   → NO: Continue

2. Is it authored (from user's chat)?
   → YES and confidence >= 0.9: → VERIFIED (trust user)
   → NO or low confidence: Continue

3. Is it pinned?
   → YES: → ACTIVE (bypass confidence/repetition gates)
   → NO: Continue

4. Check gates:
   - confidence >= 0.45 AND repetition >= 1: → ACTIVE
   - confidence >= 0.45 AND repetition < 1: → CANDIDATE (wait for repetition)
   - confidence < 0.45: → CANDIDATE (wait for confidence improvement)
```

**When a contradiction is detected:**

```
1. Mark original fact with:
   - metadata.contradiction = True
   - metadata.conflicting_memory_id = new_fact_id

2. Derive state for original:
   - If state is VERIFIED or ACTIVE: → DEPRECATED (demote)
   - If state is CANDIDATE: → CANDIDATE (no change)

3. Mark original with:
   - metadata.deprecated_at = now
   - metadata.replacement_memory_id = new_fact_id
   - metadata.deprecated_reason = "superseded by..."

4. New fact becomes preferred in inference
```

---

## Common Scenarios

### Scenario 1: User Provides Explicit Correction
```
User says: "Actually, I prefer tea, not coffee"

→ Ingested as direct_correction=True
→ Fact transitions to VERIFIED immediately
→ Old fact (if exists) marked as deprecated
→ New fact becomes inference-preferred
→ Old fact retained for audit trail
```

### Scenario 2: Fact Repeated Multiple Times
```
Day 1: "I like coffee" (confidence=0.5, repetition=1)
       → CANDIDATE (confidence < 0.45)

Day 3: "I like coffee" (confidence=0.6, repetition=2)
       → ACTIVE (confidence >= 0.45 AND repetition >= 1)
       → Deduped to same fact, confidence updated

Day 5: "I like coffee" (confidence=0.8, repetition=3)
       → Still ACTIVE (already in ACTIVE), confidence improves
```

### Scenario 3: Contradiction Detected
```
Existing: "I work in NYC" (ACTIVE, confidence=0.8, repetition=2)
New:      "I work in SF" (confidence=0.9, repetition=1)

→ System detects contradiction
→ Existing fact → DEPRECATED
→ New fact → ACTIVE (confidence >= 0.45)
→ Inference uses new fact, old retained in history
```

### Scenario 4: Fact Expires
```
TASK_SIGNAL created 35 days ago, retention_days=30

→ Background job detects expires_at < now
→ Fact → ARCHIVED (not DELETED)
→ Excluded from inference/retrieval
→ Can be un-archived by admin if needed
→ Retained for compliance
```

---

## When to Use Each Document

| Question | Document |
|---|---|
| "What does CANDIDATE mean?" | MEMORY_STATE_TRANSITIONS.md |
| "How do state transitions work?" | MEMORY_STATE_TRANSITIONS.md |
| "Why isn't my fact being used?" | MEMORY_TROUBLESHOOTING.md |
| "Two facts contradict — what happens?" | MEMORY_TROUBLESHOOTING.md |
| "How is confidence calculated?" | SCORING.md |
| "What API calls do I use?" | MEMORY_CORE_SERVICE.md |
| "What alerts should I set up?" | OBSERVABILITY.md |
| "How do I ingest a memory?" | MEMORY_CORE_SERVICE.md |
| "What's DEPRECATED vs ARCHIVED?" | MEMORY_TROUBLESHOOTING.md |

---

## Key Insights

### Why States Matter

States aren't just labels — they determine:
- Whether a fact is used in LLM context
- Whether contradictions flip it to DEPRECATED
- Whether it can be promoted to VERIFIED
- Whether it expires and moves to ARCHIVED
- Whether the system trusts it for inference

### Why Contradictions Are Terminal

When fact A contradicts fact B:
- B is marked DEPRECATED (not CANDIDATE, not demoted-then-promoted)
- B is never auto-promoted back to ACTIVE
- This prevents flip-flopping on contradictions

If B is actually correct and A is wrong, the user **provides a direct correction on B**, which promotes B back to VERIFIED. But this is explicit, not automatic.

### Why Repetition Matters

A fact mentioned 5 times with low confidence (0.3) doesn't become ACTIVE:
- Repetition only increases `repetition_count`
- Repetition doesn't fix `confidence`
- Both must improve for promotion

This prevents "if we keep saying it, it becomes true" behavior.

### Why Pinning Bypasses Gates

Pinning is a user override:
- "I know this is low confidence, but trust me"
- Sends fact directly to ACTIVE, skipping CANDIDATE
- Useful for user-provided facts they trust

---

## Architecture Overview

```
Ingestion Pipeline:
    raw fact
        ↓
    [classification] → determine memory_type, scope
        ↓
    [scoring] → compute confidence, importance, salience
        ↓
    [normalization] → derive state, confidence_band, etc.
        ↓
    [deduplication] → check for existing fact
        ↓
    [state derivation] → apply gates, derive final state
        ↓
    memory fact (CANDIDATE, ACTIVE, or VERIFIED)

Retrieval Pipeline:
    query
        ↓
    [search] → find candidate facts
        ↓
    [filter by state] → exclude DEPRECATED/ARCHIVED/DELETED
        ↓
    [rank] → prefer VERIFIED > ACTIVE
        ↓
    [check for contradictions] → mark conflicts
        ↓
    [assemble context] → return to LLM
```

---

## Files in This Directory

- `README.md` (this file) — Navigation and overview
- `MEMORY_STATE_TRANSITIONS.md` — Full state machine reference
- `MEMORY_TROUBLESHOOTING.md` — Diagnostic and recovery guides
- `MEMORY_CORE_SERVICE.md` — API and service reference
- `SCORING.md` — Confidence and importance calculation
- `OBSERVABILITY.md` — Monitoring and alerting

---

## Tests for Memory Behavior

See [`apps/api/src/api/tests/test_memory_normalization.py`](../../apps/api/src/api/tests/test_memory_normalization.py) for direct unit tests of:
- Confidence/importance bands (exact thresholds)
- Scope derivation (precedence rules)
- State transitions (boundary conditions)
- Score clamping (edge cases)
- Legacy alias compatibility
- Terminal state merging
- Empty/oversized payloads
- Reason string generation

---

## When You're Lost

1. **Start here:** [MEMORY_STATE_TRANSITIONS.md](./MEMORY_STATE_TRANSITIONS.md) — understand what state your fact is in
2. **Then here:** [MEMORY_TROUBLESHOOTING.md](./MEMORY_TROUBLESHOOTING.md) — diagnose why it's in that state
3. **If stuck:** Check the state transition decision tree above
4. **Still stuck:** Run the diagnostic function in MEMORY_TROUBLESHOOTING.md to print fact details

This is survival gear. Use it.
