# Memory Troubleshooting Guide

Quick reference for diagnosing memory system behavior.

## "Why Isn't This Fact Being Used?"

### Checklist

1. **Check state**
   ```python
   fact = memory_service.get_fact(fact_id)
   print(f"State: {fact.state}")
   ```
   - ❌ CANDIDATE, DEPRECATED, ARCHIVED, DELETED = not used
   - ✅ ACTIVE, VERIFIED = used in inference

2. **If CANDIDATE: Why?**
   - Confidence < 0.45? → needs confidence improvement
   - Repetition < 1? → needs to appear again
   - Not pinned? → user can pin to force ACTIVE
   - Source not trusted (not chat, not user-authored)? → user promotes explicitly

3. **If DEPRECATED: Check replacement**
   ```python
   metadata = fact.metadata
   replacement_id = metadata.get("replacement_memory_id")
   if replacement_id:
       replacement = memory_service.get_fact(replacement_id)
       print(f"Replaced by: {replacement.content}")
   ```
   → Use the replacement fact instead

4. **If ARCHIVED or DELETED: Was it intentional?**
   - ARCHIVED: User explicitly removed it (can be un-archived by admin)
   - DELETED: Permanent removal (tombstone retained for audit)

---

## "Why Did This Fact Get Demoted?"

### Possible Triggers

| Observation | Likely Cause | Resolution |
|---|---|---|
| Was VERIFIED, now DEPRECATED | Contradiction detected | Check `replacement_memory_id` in metadata |
| Was ACTIVE, now DEPRECATED | New fact contradicts it | Evaluate which is correct; correct the false one |
| Was ACTIVE, now CANDIDATE | No trigger expected | Check for external deprecation |

### Audit Trail

```python
fact = memory_service.get_fact(fact_id)
print(f"Current state: {fact.state}")
print(f"Deprecated at: {fact.metadata.get('deprecated_at')}")
print(f"Reason: {fact.metadata.get('deprecated_reason')}")
print(f"Replaced by: {fact.metadata.get('replacement_memory_id')}")
```

---

## "Two Facts Contradict Each Other — Which One Is Used?"

### Diagnosis

1. **Fetch both facts**
   ```python
   fact_a = memory_service.get_fact(fact_a_id)
   fact_b = memory_service.get_fact(fact_b_id)
   ```

2. **Check states**
   ```python
   print(f"Fact A: state={fact_a.state}, confidence={fact_a.confidence}")
   print(f"Fact B: state={fact_b.state}, confidence={fact_b.confidence}")
   ```

3. **Resolution order**
   - If one is DEPRECATED, the other is used ✅
   - If one is VERIFIED and the other is ACTIVE, VERIFIED is preferred ✅
   - If both are ACTIVE or both are VERIFIED → higher confidence is preferred
   - If tied on confidence and state → creation timestamp (newer wins)

4. **Correct the false one**
   ```python
   # If fact_a is wrong:
   memory_service.mark_fact_as_direct_correction(
       fact_id=fact_a_id,
       supersedes_ids=[fact_a_id]  # Self-supersedes to deprecate
   )
   # or explicitly provide the correction:
   memory_service.ingest_memory_fact(
       text="The correct fact is...",
       metadata={"direct_correction": True}
   )
   ```

---

## "A Fact Has `later_contradicted=True` — What Does That Mean?"

### Meaning

The fact was correct when created, but a later fact contradicts it. The original fact **was not auto-demoted** because it was VERIFIED or high-confidence ACTIVE.

### Scenarios

**Scenario 1: User preference changed**
```
Original: "I prefer coffee"       (VERIFIED)
Later:    "Actually, I prefer tea" (direct correction)

Result: First fact is marked later_contradicted=True
        First fact stays VERIFIED (user can use for history)
        Second fact becomes VERIFIED (newer authoritative source)
```

**Scenario 2: Environment changed**
```
Original: "I work in NYC"         (ACTIVE, confidence=0.8)
Later:    "I moved to SF"         (new information)

Result: First fact is marked later_contradicted=True
        Both facts retained for timeline/history
        Inference uses "I work in SF" (newer)
```

### What to Do

1. **Check timestamp** — which fact is newer?
2. **Evaluate both** — did circumstances change or was the original wrong?
3. **If original was wrong:** provide direct correction to deprecate it
4. **If circumstances changed:** both facts are correct in context; inference should use the newer one

---

## "Why Is This High-Confidence Fact Still in CANDIDATE?"

### Root Causes

1. **Repetition gate blocking**
   ```python
   print(f"Confidence: {fact.confidence} (need >= 0.45)")
   print(f"Repetition: {fact.repetition_count} (need >= 1)")
   ```
   → Confidence high, repetition < 1? Fact needs to appear again

2. **Source not trusted**
   ```python
   print(f"Source: {fact.source_kind}")
   print(f"Authored: {fact.metadata.get('authored')}")
   ```
   → If source_kind is not 'conversation' or 'memory', auto-promotion may not trigger

3. **Not pinned**
   ```python
   print(f"Pinned: {fact.metadata.get('pinned')}")
   ```
   → Pinning bypasses confidence/repetition gates

### Solutions

- **Wait for repetition:** Same fact mentioned again automatically promotes
- **Pin it:** `memory_service.pin_fact(fact_id)` forces ACTIVE
- **User promotes:** Explicit promotion → ACTIVE
- **Ingest as authored:** Mark `metadata["authored"]=True` → VERIFIED on next ingest

---

## "Facts Keep Flipping Between ACTIVE and CANDIDATE"

### Cause: Confidence Oscillation

Confidence is computed dynamically. If confidence hovers near 0.45:

```python
print(f"Confidence: {fact.confidence}")
print(f"Confidence band: {fact.confidence_band}")
```

Confidence may cross the gate on each update:
- confidence=0.46 → ACTIVE ✅
- confidence=0.44 (new signal) → CANDIDATE ❌
- confidence=0.46 (new signal) → ACTIVE ✅

### Fix

1. **Stabilize confidence** by providing explicit signals:
   ```python
   memory_service.ingest_memory_fact(
       text=fact.content,
       metadata={
           "direct_correction": True,  # Atomic promotion to VERIFIED
           "authored": True,            # Trust the source
           "confidence": 0.95           # Explicit strong signal
       }
   )
   ```

2. **Or pin the fact** to force ACTIVE regardless of gates:
   ```python
   memory_service.pin_fact(fact_id)
   ```

3. **Or increase repetition** to stabilize:
   ```python
   # Just ingest the same fact again
   memory_service.ingest_memory_fact(
       text=fact.content,
       metadata={"repetition_count": fact.repetition_count + 1}
   )
   ```

---

## "A Lot of Facts Are DEPRECATED — Is This Normal?"

### Assessment

Check the ratio:
```python
facts = memory_service.list_all_facts(user_id)
deprecated_count = sum(1 for f in facts if f.state == DEPRECATED)
total_count = len(facts)
ratio = deprecated_count / total_count

print(f"Deprecated ratio: {ratio:.1%}")
```

**Healthy:** 5–15% deprecated (some facts get contradicted over time)  
**Warning:** 20%+ deprecated (many facts being invalidated, check quality)  
**Critical:** 50%+ deprecated (something is systematically wrong)

### If Ratio Is High

1. **Check for bulk contradictions**
   ```python
   recent_deprecations = [
       f for f in facts 
       if f.state == DEPRECATED and f.metadata.get("deprecated_at") > cutoff
   ]
   print(f"Deprecations in last 24h: {len(recent_deprecations)}")
   ```

2. **Identify patterns**
   ```python
   for fact in recent_deprecations[:10]:
       replacement_id = fact.metadata.get("replacement_memory_id")
       if replacement_id:
           print(f"Deprecated: {fact.content}")
           print(f"Replaced by: memory_service.get_fact({replacement_id}).content")
   ```

3. **Possible issues**
   - User providing many conflicting memories (normal, expected)
   - Memory system inferring contradictions incorrectly (check metadata)
   - External data refresh is overwriting old facts (expected in some domains)

---

## "Why Did My Fact Go From VERIFIED to DEPRECATED?"

### Meaning

A fact you explicitly corrected/verified is now contradicted by something newer.

### Implications

**VERIFIED facts should not be demoted lightly.** If this happened:

1. **Check what contradicts it**
   ```python
   fact = memory_service.get_fact(fact_id)
   replacement_id = fact.metadata.get("replacement_memory_id")
   replacement = memory_service.get_fact(replacement_id)
   print(f"Your fact: {fact.content}")
   print(f"Contradicted by: {replacement.content}")
   ```

2. **Evaluate correctness**
   - Is the replacement actually correct?
   - Did circumstances change?
   - Is the system detecting a false contradiction?

3. **Recover**
   ```python
   # If your VERIFIED fact is correct and replacement is wrong:
   memory_service.ingest_memory_fact(
       text=fact.content,
       metadata={
           "direct_correction": True,
           "supersedes_memory_ids": [replacement_id]
       }
   )
   # This promotes your fact back to VERIFIED and deprecates the replacement
   ```

---

## "I Ingest the Same Fact Multiple Times — What's the State?"

### Behavior

Each ingest increments `repetition_count` and may update confidence.

```python
# First ingest
ingest_memory_fact("I like coffee", metadata={"confidence": 0.5})
# state=CANDIDATE (confidence < 0.45, rep=1)

# Second ingest (same fact)
ingest_memory_fact("I like coffee", metadata={"confidence": 0.7})
# state=ACTIVE (confidence >= 0.45, rep=2)

# Check deduplication
facts = memory_service.list_facts(user_id)
duplicate_facts = [f for f in facts if f.content == "I like coffee"]
print(f"Deduplicated to {len(duplicate_facts)} fact(s)")
# Deduplication key: (user_id, fact_text, memory_type)
# So only ONE fact exists, rep=2, confidence=0.7
```

---

## "What's the Difference Between ARCHIVED and DELETED?"

### Comparison

| Aspect | ARCHIVED | DELETED |
|---|---|---|
| **Reversibility** | Can be un-archived | Permanent, irreversible |
| **Inference use** | ❌ Not used | ❌ Not used |
| **Retention** | ✅ Stored | ✅ Soft-deleted (tombstone) |
| **Audit trail** | ✅ Full history | ✅ Tombstone for forensics |
| **When used** | User manually removes | GDPR/CCPA purge, user delete request |
| **Recovery** | Admin can restore | Not recoverable |

### Guidance

- **Use ARCHIVED** for user preferences that may come back ("I'll revisit")
- **Use DELETED** for compliance/legal (GDPR, etc.) or user delete requests

---

## Quick Reference: Which State Is This Fact In?

```python
def diagnose_fact(fact_id):
    fact = memory_service.get_fact(fact_id)
    
    print(f"State: {fact.state}")
    print(f"Confidence: {fact.confidence} (band: {fact.confidence_band})")
    print(f"Repetition: {fact.repetition_count}")
    print(f"Used in inference: {fact.state in {ACTIVE, VERIFIED}}")
    
    if fact.state == DEPRECATED:
        print(f"Deprecated at: {fact.metadata.get('deprecated_at')}")
        print(f"Reason: {fact.metadata.get('deprecated_reason')}")
        print(f"Replaced by: {fact.metadata.get('replacement_memory_id')}")
    
    if fact.metadata.get("later_contradicted"):
        print("⚠️ This fact was contradicted later (but not auto-demoted)")
```

---

## See Also

- [Memory State Transitions](./MEMORY_STATE_TRANSITIONS.md) — Full transition rules
- [Memory Core Service](./MEMORY_CORE_SERVICE.md) — API reference
- [Scoring & Confidence](./SCORING.md) — How confidence is computed
