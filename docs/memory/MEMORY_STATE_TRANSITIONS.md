# Memory State Transitions

## Overview

The memory system tracks facts through a lifecycle with six states. Each state represents a level of confidence and operational readiness. **Transitions are not arbitrary** — they enforce invariants about when facts can be used, when they're promoted, when they're deprecated, and when they're terminal.

This document is the canonical reference for:
- Which transitions are allowed
- What triggers each transition
- When facts are safe to use in inference
- How contradictions, corrections, and repetition affect state
- Failure modes and recovery paths

**Read this before troubleshooting memory behavior. This is survival gear.**

---

## State Definitions

### CANDIDATE (rank=0)
**Definition:** A fact is collected but not yet validated.

**When entered:**
- New facts with low confidence (`< 0.45`)
- New facts with `repetition_count < 2`
- Facts not authored and not pinned
- Contradictions detected (set to DEPRECATED first, can be demoted to CANDIDATE)

**Operational rules:**
- ❌ NOT used in inference by default
- ❌ NOT included in retrieval results (unless explicitly requested for analysis)
- ✅ Available for review and manual promotion
- ✅ Can be deleted without data loss

**Escape conditions:**
- Confidence rises to `>= 0.45` AND `repetition_count >= 2` → ACTIVE
- User explicitly promotes → ACTIVE or VERIFIED
- Pinned by user → ACTIVE (skip CANDIDATE)

---

### ACTIVE (rank=1)
**Definition:** A fact is ready for inference. Confidence is moderate or good. No contradictions known.

**When entered:**
- Confidence `>= 0.45` AND `repetition_count >= 1` (default promotion)
- User explicitly promotes from CANDIDATE
- Pinned by user (overrides confidence/repetition gates)
- Importance `>= 0.8` (high-impact facts are promoted)
- Source is conversation or memory (trusted sources)

**Operational rules:**
- ✅ Used in inference by default
- ✅ Included in retrieval results
- ✅ Used in context assembly
- ⚠️ Can be demoted to DEPRECATED if contradicted

**Escape conditions:**
- Direct correction from user → VERIFIED (promoted)
- Contradiction detected → DEPRECATED (demoted)
- User explicitly archives → ARCHIVED
- Later contradiction discovered → stays ACTIVE but marked `later_contradicted=True`

---

### VERIFIED (rank=2)
**Definition:** A fact has been explicitly validated or is author-provided with high confidence.

**When entered:**
- User provides direct correction
- Author provides fact AND confidence `>= 0.9` AND `repetition_count >= 2`
- User explicitly verifies a fact
- Fact is user-authored and meets confidence threshold

**Operational rules:**
- ✅✅ Highest priority in inference
- ✅✅ Preferred over ACTIVE facts in ambiguity
- ⚠️ CANNOT be demoted to ACTIVE (only to DEPRECATED via contradiction)
- ⚠️ If later contradicted, stays VERIFIED but marked `later_contradicted=True`

**Escape conditions:**
- Contradiction detected → DEPRECATED (terminal demotion)
- User explicitly archives → ARCHIVED
- User explicitly deletes → DELETED

---

### DEPRECATED (rank=1, terminal for quality)
**Definition:** A fact contradicts a newer/better fact. No longer used in inference.

**When entered:**
- Contradiction detected: newer/better fact supersedes this one
- VERIFIED or ACTIVE fact is contradicted
- Explicit deprecation by user via `supersedes` metadata

**Operational rules:**
- ❌ NOT used in inference
- ❌ NOT included in retrieval
- ✅ Retained for audit trail and conflict history
- ✅ Links to replacement fact stored in metadata
- ⚠️ **Cannot be promoted back to ACTIVE/VERIFIED** (terminal for quality)

**Metadata on deprecation:**
```python
deprecated_at: datetime
deprecated_reason: str  # e.g., "superseded by mem-456", "user corrected"
replacement_memory_id: str  # if applicable
conflict_metadata: dict  # original vs new fact
```

**Escape conditions:**
- None. DEPRECATED is terminal for quality. Manual resurrection requires re-ingestion.

---

### ARCHIVED (rank=-1, terminal)
**Definition:** A fact is intentionally removed from active use. User-initiated, reversible administratively.

**When entered:**
- User explicitly archives
- Metadata flag `force_archive=True`
- Retention period expired (automatic, configurable per MemoryKind)

**Operational rules:**
- ❌ NOT used in inference
- ❌ NOT included in retrieval
- ✅ Retained in storage for compliance/audit
- ✅ Can be un-archived by admin/user

**Escape conditions:**
- Admin explicitly un-archives → returns to ACTIVE (or prior state)

---

### DELETED (rank=-2, terminal)
**Definition:** A fact is permanently removed. Irreversible in normal operation.

**When entered:**
- User explicitly requests deletion
- Compliance purge (GDPR, CCPA)
- Metadata flags: `deleted=True`, `deleted_at`, `tombstone=True`

**Operational rules:**
- ❌ NOT used in inference
- ❌ NOT returned in any query (soft-deleted, not removed)
- ✅ Retained as tombstone for forensic audit
- ❌ **Cannot be restored** (terminal)

**Escape conditions:**
- None. DELETED is irreversible.

---

## State Transition Diagram

```
                    ┌─────────────────────────────────────────────┐
                    │        CANDIDATE (rank=0)                   │
                    │  Low confidence, not yet validated          │
                    └──────────────────┬──────────────────────────┘
                                       │
                  ┌────────────────────┼────────────────────┐
                  │                    │                    │
          confidence>=0.45  user promotes  pinned user     │
          AND rep>=2        OR explicit    (bypass gate)    │
                  │                    │                    │
                  ▼                    ▼                    ▼
        ┌──────────────────────────────────────────────────────────┐
        │         ACTIVE (rank=1)                                  │
        │  Ready for inference, moderate confidence               │
        │  default state for new facts                            │
        └─────────┬───────────────────────────┬────────────────────┘
                  │                           │
        ┌─────────┴──────────┐    ┌──────────┴─────────────┐
        │                    │    │                        │
   direct correction    contradiction detected    user archives
   (verification)       (new fact supersedes)    or explicit archive
        │                    │                        │
        ▼                    ▼                        ▼
    ┌────────────┐    ┌──────────────┐        ┌──────────────┐
    │  VERIFIED  │    │ DEPRECATED   │        │  ARCHIVED    │
    │ (rank=2)  │    │ (rank=1)     │        │ (rank=-1)    │
    │ author-   │    │ superseded   │        │ user-        │
    │ validated │    │ by new fact  │        │ removed      │
    └─────┬─────┘    └──────────────┘        └──────────────┘
          │
          │ contradiction detected
          │ (new fact contradicts)
          │
          ▼
    ┌──────────────────────────────────────┐
    │        DELETED (rank=-2)             │
    │  Permanently removed (irreversible)  │
    └──────────────────────────────────────┘
```

### Terminal States (No Escape)

```
DEPRECATED  ──────────────────► (end of inference use, audit trail only)
ARCHIVED    ──────────────────► (can be un-archived by admin)
DELETED     ──────────────────► (irreversible, tombstone only)
```

---

## Transition Rules & Guards

### Rule 1: Confidence Gate
**Condition:** `confidence < 0.45` blocks ACTIVE/VERIFIED promotion.
**Exception:** User explicit promotion, pinned flag, source=conversation.

```python
if confidence < 0.45 and not (user_promoted or pinned or source_conversation):
    state = CANDIDATE
```

### Rule 2: Repetition Gate
**Condition:** `repetition_count < 2` blocks automatic ACTIVE.
**Exception:** User promotes, high importance, authored fact.

```python
if repetition_count < 1 and not user_promoted and importance < 0.8:
    state = CANDIDATE
```

### Rule 3: Direct Correction → VERIFIED
**Condition:** User provides explicit correction.
**Effect:** Immediate promotion to VERIFIED, no intermediate states.

```python
if direct_correction:
    state = VERIFIED
```

### Rule 4: Contradiction → DEPRECATED
**Condition:** Newer/better fact contradicts this one.
**Effect:** Irreversible demotion. Replacement tracked in metadata.

```python
if contradiction_detected and existing_state in {ACTIVE, VERIFIED}:
    state = DEPRECATED
    metadata.deprecated_reason = "superseded by " + replacement_id
```

### Rule 5: Terminal State Merge
**Condition:** Merging two states, one terminal.
**Effect:** Terminal always wins.

```python
def merge_states(current, incoming):
    if incoming in {DELETED, ARCHIVED}:
        return incoming  # Terminal always wins
    if incoming.rank > current.rank:
        return incoming  # Higher rank wins
    return current
```

### Rule 6: Pinned Overrides Confidence
**Condition:** Fact is pinned (`metadata.pinned=True`).
**Effect:** Skips CANDIDATE even if confidence low.

```python
if pinned and confidence < 0.45:
    # Skip CANDIDATE, go directly to ACTIVE
    state = ACTIVE
```

---

## Failure Scenarios & Recovery

### Scenario 1: Contradiction Detected in Retrieval

**Situation:** Memory system discovers fact A contradicts fact B during retrieval ranking.

**Response:**
```
1. Mark fact A as contradicted (metadata.contradiction=True)
2. Derive state for fact A:
   - If current state is VERIFIED → demote to DEPRECATED
   - If current state is ACTIVE → demote to DEPRECATED
   - If current state is CANDIDATE → stay CANDIDATE
3. Store replacement_memory_id → fact B in fact A's metadata
4. Fact B becomes preferred in future retrievals
5. Fact A is excluded from inference results
```

**Recovery:**
- If fact A is actually correct and B is wrong, user provides direct correction on A → A becomes VERIFIED, B is manually deprecated
- If ambiguity is genuine, keep both, mark conflict in metadata for logging

---

### Scenario 2: User Provides Correction (Direct Correction)

**Situation:** User says "Actually, I prefer X, not Y" about an ACTIVE fact.

**Response:**
```
1. Mark original fact as direct_correction=True
2. Transition original → VERIFIED (atomic, no intermediate)
3. Create new fact with user's preference (also VERIFIED)
4. If new fact contradicts old: mark old as deprecated
5. Inference now uses new fact, old is in audit trail
```

**Semantics:** Direct correction is user-authoritative. It always wins.

---

### Scenario 3: Repeated Low-Confidence Facts

**Situation:** Same fact mentioned 5 times, but each mention has low confidence (0.3).

**Response:**
```
1. Facts stay CANDIDATE (confidence < 0.45)
2. repetition_count increments to 5
3. But: confidence still 0.3 (repetition doesn't fix quality)
4. State remains CANDIDATE
5. Facts excluded from inference
```

**Intent:** Repetition of bad data doesn't make it good. Confidence score must also rise.

**Recovery:**
- User provides one high-confidence mention → confidence rises, repetition gate passes → ACTIVE
- Or: User corrects root cause, provides authoritative version → VERIFIED

---

### Scenario 4: Author-Provided Fact Meets High Thresholds

**Situation:** Fact from user's own chat, confidence=0.92, repetition_count=1.

**Response:**
```
1. authored=True (source is conversation)
2. confidence=0.92 >= 0.9 AND authored
3. Explicit kind (PREFERENCE) suggests high importance
4. Promote to VERIFIED (user-authored + high confidence)
5. Ready for inference immediately
```

---

### Scenario 5: Retention Period Expires

**Situation:** TASK_SIGNAL with `retention_days=30`, created 35 days ago.

**Response:**
```
1. Background job detects expires_at < now
2. Transition → ARCHIVED (not DELETED)
3. Retained in storage for compliance
4. Excluded from retrieval
5. Can be un-archived by admin if needed
```

**Semantic:** Expiration is administrative archival, not deletion.

---

### Scenario 6: Later Contradiction Discovered

**Situation:** Fact is VERIFIED/ACTIVE. User later contradicts it but doesn't explicitly deprecate.

**Response:**
```
1. Mark metadata.later_contradicted=True
2. Keep original state (VERIFIED stays VERIFIED)
3. Do NOT auto-demote to DEPRECATED (user choice point)
4. Flag in observability: conflict_metadata logged
5. Next retrieval pass: user can resolve via direct correction
```

**Intent:** Preserve audit trail. Don't silently demote VERIFIED facts. Make conflicts visible.

---

## State Transition Matrix

| Current State | Confidence ↑ | Contradiction | User Promotes | User Archives | Explicit Delete |
|---|---|---|---|---|---|
| **CANDIDATE** | → ACTIVE (if rep≥1) | → CANDIDATE | → ACTIVE | → ARCHIVED | → DELETED |
| **ACTIVE** | → ACTIVE | → DEPRECATED | → VERIFIED | → ARCHIVED | → DELETED |
| **VERIFIED** | → VERIFIED | → DEPRECATED | → VERIFIED | → ARCHIVED | → DELETED |
| **DEPRECATED** | ✗ no escape | ✗ terminal | ✗ no escape | (already deprecated) | → DELETED |
| **ARCHIVED** | ✗ archived | ✗ archived | ✗ archived | ✗ already | → DELETED |
| **DELETED** | ✗ deleted | ✗ deleted | ✗ deleted | ✗ deleted | ✗ deleted |

---

## Rank-Based Merging Algorithm

When two facts have conflicting states (e.g., one says ACTIVE, one says DEPRECATED):

```python
STATE_RANK = {
    DELETED: -2,
    ARCHIVED: -1,
    CANDIDATE: 0,
    ACTIVE: 1,
    VERIFIED: 2,
    DEPRECATED: 1,  # Same rank as ACTIVE (quality concern)
}

def merge_states(current, incoming):
    # Terminal states always win
    if incoming in {DELETED, ARCHIVED}:
        return incoming
    
    # Higher rank always wins
    if RANK[incoming] > RANK[current]:
        return incoming
    
    # Same rank: incoming wins (newer information)
    if RANK[incoming] == RANK[current]:
        return incoming
    
    return current
```

**Key insight:** DEPRECATED has rank=1 (same as ACTIVE). If two facts with same rank conflict, incoming wins. This allows newer contradictions to override stale facts without explicit comparison.

---

## Inference Rules by State

| State | Confidence | Explicit Check | Default Include | Retrieval Rank |
|---|---|---|---|---|
| CANDIDATE | Low | ❌ Skip | ❌ | - |
| ACTIVE | Moderate | ✅ Use | ✅ | Medium |
| VERIFIED | High | ✅✅ Prefer | ✅ | Highest |
| DEPRECATED | (ignored) | ❌ Skip | ❌ | - |
| ARCHIVED | (ignored) | ❌ Skip | ❌ | - |
| DELETED | (ignored) | ❌ Skip | ❌ | - |

---

## Observability Signals

### State Transitions to Alert On

**🔴 Critical:**
- VERIFIED → DEPRECATED (high-confidence fact contradicted)
- ACTIVE → DEPRECATED (frequently used fact invalidated)

**🟠 Warning:**
- CANDIDATE count > threshold (many low-confidence facts accumulating)
- DEPRECATED count > threshold (many facts being superseded)

**🟡 Info:**
- CANDIDATE → ACTIVE (fact validation succeeded)
- ACTIVE → VERIFIED (fact confirmed by user)
- Contradiction detected (log both facts + replacement)

---

## Testing State Transitions

Every test of state transitions should verify:

1. **Current state** before transition
2. **Input condition** that triggers transition
3. **New state** after transition
4. **Metadata changes** (deprecated_at, replacement_id, etc.)
5. **Inference behavior** (would this fact be used?)

Example test:
```python
def test_verified_fact_contradicted_becomes_deprecated():
    fact = create_fact(state=VERIFIED, confidence=0.95)
    # Simulate contradiction
    contradiction_metadata = {"supersedes_memory_ids": [fact.id]}
    new_state = derive_memory_state(
        contradiction=True,
        metadata=contradiction_metadata,
        current_state=VERIFIED
    )
    assert new_state == DEPRECATED
    # Verify inference would skip this fact
    assert should_use_in_inference(fact, new_state) is False
```

---

## Migration Guide: Old States to New Model

If upgrading from a prior memory system:

| Old State | Maps To | Notes |
|---|---|---|
| UNVERIFIED | CANDIDATE | Low confidence, not ready |
| DRAFT | CANDIDATE | Not yet validated |
| PUBLISHED | ACTIVE | Moderate confidence, ready |
| CONFIRMED | VERIFIED | User-validated |
| INVALID | DEPRECATED | Contradicted by newer fact |
| ARCHIVED | ARCHIVED | Removed from use |
| DELETED | DELETED | Permanently removed |

---

## Key Takeaways

1. **States are not fluid.** Each transition represents a real change in operational readiness.

2. **DEPRECATED is terminal for quality.** Once a fact is contradicted, it never returns to ACTIVE. This is intentional — we don't want to flip-flop on contradictions.

3. **Confidence + Repetition gates prevent false promotion.** A fact with low confidence but high repetition stays CANDIDATE. Both must improve.

4. **User corrections are atomic and instant.** Direct corrections jump to VERIFIED, skipping intermediate states.

5. **Terminal states always win in merges.** If one fact is DELETED and another is ACTIVE, DELETED wins. No ambiguity.

6. **Contradictions are logged with replacement IDs.** We never silently discard facts — we track why they were deprecated.

7. **Inference respects rank.** VERIFIED facts are preferred over ACTIVE facts. This matters when facts conflict.

---

## See Also

- [Memory Core Service API](./MEMORY_CORE_SERVICE.md) — Ingestion, retrieval, and state derivation
- [Scoring & Confidence](./SCORING.md) — How confidence and importance are computed
- [Observability & Monitoring](./OBSERVABILITY.md) — State transition alerts
