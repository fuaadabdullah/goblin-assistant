# Memory Promotion Guidelines

## Overview

Memory Promotion Rules ensure that long-term memory stays **boring, stable, and provable**. This prevents the system from creating a false personality or storing unstable, emotional information.

## Canonical Memory Object

The runtime exposes long-term memory as a canonical superset object. Existing storage fields are still preserved, but callers should treat this shape as the source of truth:

```json
{
  "id": "mem_01JX...",
  "user_id": "usr_123",
  "type": "semantic",
  "scope": "global",
  "content": "User prefers concise technical explanations.",
  "summary": "Prefers concise technical explanations",
  "source": "conversation",
  "source_ref": {
    "conversation_id": "conv_456",
    "message_id": "msg_789"
  },
  "confidence": 0.94,
  "importance": 0.82,
  "recency_score": 0.71,
  "sensitivity": "low",
  "status": "active",
  "tags": ["preference", "style"],
  "entities": ["user"],
  "embedding_id": "emb_abc",
  "created_at": "2026-06-11T18:00:00Z",
  "updated_at": "2026-06-11T18:00:00Z",
  "last_accessed_at": "2026-06-11T18:03:00Z",
  "expires_at": null
}
```

Compatibility aliases such as `memory_type`, `source_kind`, `source_id`, `salience_score`, `entity_refs`, and `sensitivity_level` remain available for older callers.

## Conflict Handling

Humans contradict themselves. The memory system must keep the useful parts instead of flattening them into one false truth.

### Policy
- Explicit user correction wins over inferred memory.
- Newer high-confidence memory wins over stale lower-confidence memory.
- Repeated recent memory wins over a one-off older memory.
- Inferred memory loses to a direct statement.
- Stale memory gets demoted before it gets deleted.
- Different scopes can coexist when they describe different contexts.

### Resolution Rules
- Keep both memories when they are scoped differently, such as a global preference plus a project-specific override.
- Mark the losing memory `deprecated` when the new memory clearly supersedes it.
- Merge repeated confirmations into the same memory record when the content is materially the same.
- Preserve contradiction history in metadata and observability logs.

### Example

Old memory:
`User prefers short answers.`

New message:
`User wants more detail for architecture explanations.`

Result:
- keep both
- scope them separately
- general answers: concise
- architecture explanations: detailed

## Core Law

**Long-term memory must be boring, stable, and provable.**

If it's emotional, situational, or heat-of-the-moment, it stays out.
If it changes weekly, it stays out.
If it can't be stated as a clean sentence, it stays out.

## What Is Eligible for Promotion

Only these categories may ever become long-term memory:

### 1. Preferences
- **Communication style**: "I prefer concise technical explanations"
- **Tooling choices**: "I consistently use React for frontend development"
- **Model preferences**: "I prefer GPT-4 over other models"
- **Privacy stance**: "I value data privacy highly"

**Example:**
> "I prefer concise technical explanations."
> ✅ **Good.** Stable. Reusable.

### 2. Facts (User or System)
- **Ongoing projects**: "User is building Goblin Assistant as a production AI platform"
- **Roles**: "User is a senior software engineer"
- **Constraints**: "User works in a regulated industry"
- **Known objectives**: "User wants to optimize for performance over features"

**Example:**
> "User is building Goblin Assistant as a production AI platform."
> ✅ **Good.** Fact-based, not mood-based.

### 3. Identity Traits (Rare, High Bar)
- Must appear repeatedly
- Must survive time gaps
- Must be implicitly reinforced
- **Example**: "User values architectural rigor over speed"

**This only gets promoted after repetition. No first-date memory tattoos.**

## What Is Never Promoted

Let's be explicit so future-you doesn't get clever:

❌ **Emotions**: "I'm stressed today", "I'm excited about this"
❌ **One-off opinions**: "This is the best tool ever" (said once)
❌ **Temporary goals**: "I want to finish this by Friday"
❌ **Complaints**: "This API is so frustrating"
❌ **Jokes**: "LOL that's hilarious"
❌ **Vents**: "I'm so annoyed at my boss"
❌ **Hypotheticals**: "What if we tried...?"

**If it starts with "right now," it's out.**

## Promotion Preconditions (Hard Gates)

A memory item must pass **ALL** of these gates:

### Gate 1: Repetition
- Appears in ≥2 summaries
- Or reinforced across separate conversations
- **Purpose**: Ensures it's not a one-time comment

### Gate 2: Time
- Spans at least one time boundary
- Same signal today and later
- **Purpose**: Ensures temporal stability

### Gate 3: Stability
- **Declarative**: "I prefer" not "I might prefer"
- **No emotional language**: No "frustrated", "excited", "stressed"
- **No conditionals**: No "if", "when", "maybe", "possibly"
- **Purpose**: Ensures objective, stable content

### Gate 4: Content Quality
- **No temporal indicators**: No "today", "right now", "currently"
- **No subjective statements**: No "I think", "I believe", "I feel"
- **No imperative language**: No "should", "must", "have to", "need to"
- **No humor/complaints**: No jokes, vents, or complaints
- **Purpose**: Ensures boring, factual content

## Examples

### ✅ **PROMOTABLE** (Passes All Gates)

**Preference:**
> "I prefer concise technical explanations."
- ✅ Declarative
- ✅ No emotional language
- ✅ Stable preference
- ✅ Reusable across conversations

**Fact:**
> "I work as a senior software engineer at a fintech company."
- ✅ Objective fact
- ✅ No temporal indicators
- ✅ Stable information
- ✅ Useful context

**Identity Trait (after repetition):**
> "I value architectural rigor over rapid development."
- ✅ Only after appearing multiple times
- ✅ Stable principle
- ✅ No emotional language

### ❌ **NOT PROMOTABLE** (Fails Gates)

**Emotional:**
> "I'm really stressed about this deadline today."
- ❌ Emotional language ("stressed")
- ❌ Temporal indicator ("today")
- ❌ One-time situation

**One-off Opinion:**
> "This is the best API I've ever used!"
- ❌ Subjective ("best")
- ❌ Exclamation (emotional)
- ❌ Likely to change

**Temporary Goal:**
> "I need to finish this feature by Friday."
- ❌ Temporal constraint ("by Friday")
- ❌ Temporary objective
- ❌ Not stable

**Conditional:**
> "I might prefer Python if it weren't so slow."
- ❌ Conditional ("if")
- ❌ Negative framing
- ❌ Not declarative

**Hypothetical:**
> "What if we tried using GraphQL instead?"
- ❌ Hypothetical ("what if")
- ❌ Not factual
- ❌ Exploratory, not established

## Implementation Details

### Gate Scoring

Each gate has a threshold:

- **Repetition**: ≥2 occurrences
- **Time Span**: ≥1 day between occurrences
- **Stability Score**: ≥0.8 (based on language analysis)
- **Content Quality**: ≥0.7 (based on emotional/temporal pattern detection)

### Promotion Process

1. **Extract Candidates**: From conversation summaries
2. **Apply Gates**: Check each gate sequentially
3. **Store if Passed**: Only if ALL gates pass
4. **Log Decision**: For transparency and debugging

## Lifecycle

Every memory item moves through explicit states instead of being treated as permanently active.

### States
- `candidate`: observed but not yet trusted enough for broad use
- `active`: usable in retrieval and context assembly
- `verified`: trusted, repeatedly reinforced, or directly corrected by the user
- `deprecated`: preserved for history, but downranked because it is stale or contradicted
- `archived`: retained for traceability but excluded from normal retrieval
- `deleted`: tombstoned in the normal lifecycle or removed by privacy erasure policy

### Lifecycle Rules
- Candidates need scoring or confirmation before they become active.
- Verified memories are the highest-trust durable memories.
- Deprecated memories stay visible for history and audit, but they should not outrank stronger evidence.
- Archived memories are preserved for traceability and compaction.
- Deleted memories are terminal; privacy erasure may hard-delete them immediately.

## Forgetting

Memory without forgetting becomes clutter.

### Automatic Forgetting
- Trigger on low usage.
- Trigger on low importance.
- Trigger on expiration.
- Trigger on contradiction.
- Trigger on irrelevance.

### Decay Rules
- Memory scores should slowly decay unless reinforced.
- Important memories can be pinned internally so they resist decay.
- Low-salience memories should be archived before they are deleted.
- Stale or contradictory memories should be demoted, not immediately removed.

### User-Requested Forgetting
- If the user explicitly says delete, forget, or remove, obey the privacy policy and remove the memory through the erasure flow.
- Treat user erasure as higher priority than ordinary lifecycle decay.

## Privacy and Safety

Memory is where assistant systems get creepy fast, so the storage rules need to stay tight.

### Rules
- Do not store sensitive data by default.
- Classify sensitive content before persistence.
- Separate inferred memory from explicit memory.
- Keep audit logs for promotion, demotion, and deletion.
- Support user deletion and export through the privacy flow.
- Avoid storing private health, legal, financial, or identity data unless the user explicitly asks and the policy allows it.

### Security Layers
- Encrypt sensitive storage at rest.
- Scope access by user and project.
- Log admin access.
- Redact memory content before sending it to model prompts when needed.
- Scan memory ingestion paths for secrets.

## Memory Acquisition Pipeline

Every user message and assistant response is scanned for memory-worthy content.

### Step 1: Detect Candidates
- Look for explicit requests like "remember this"
- Look for recurring preferences, goals, and architecture decisions
- Look for stable facts with future utility

### Step 2: Classify Type
- `semantic`
- `episodic`
- `procedural`
- `project`
- `preference`
- `task-related`

### Step 3: Score Signals
- usefulness
- stability
- confidence
- sensitivity
- duplication risk
- recency

### Step 4: Decide
- store automatically
- store with lower priority
- ask for confirmation
- reject
- merge with existing memory

### Step 5: Normalize
- Convert the raw statement into a clean summary
- Attach source metadata and timestamps
- Preserve privacy-safe aliases for older surfaces

## Memory Confidence Model

Memory confidence is probabilistic, not binary.

### Confidence Inputs
- explicitness of the statement
- repetition over time
- whether the memory was user-authored or inferred
- whether it conflicts with existing memory
- whether it came from a direct correction
- whether the user later contradicted it

### Confidence Bands
- `0.90-1.00`: strong stable memory
- `0.70-0.89`: likely true, usable
- `0.40-0.69`: weak, needs verification
- `<0.40`: do not use by default

Low-confidence memories stay visible for audit and retrieval, but they do not override stronger memories unless a direct correction or other fresh evidence raises them.

## Memory Importance Model

Importance controls retrieval, pinning, summarization, and forgetting.

### Importance Inputs
- frequency of use
- task relevance
- explicit user emphasis
- dependency level
- whether the memory affects future behavior

### Priority Examples
- `User likes concise answers` -> high importance
- `User mentioned a random anime once` -> low importance
- `Goblin uses department routing` -> high project importance

## Memory Scopes

Memory is scoped to prevent pollution.

- `global`: user style preferences, general identity, long-term goals
- `project`: repo, client, or initiative-specific context
- `conversation`: current thread or related follow-up only
- `tool`: a tool or subsystem boundary

If scope is not explicit, default to `global` unless metadata proves a narrower boundary.

## Storage Architecture

Use a split storage model instead of a single table pretending to be a strategy.

- PostgreSQL: authoritative memory records, metadata, lifecycle state, permissions, and audit trail
- Vector index: semantic retrieval and fuzzy recall
- Redis: hot/session/working-memory cache and temporary ranking data
- Graph-like relationships: represented first with Postgres links and metadata, not a new graph service

The runtime should keep `memory_facts` and embeddings compatible while deriving confidence, importance, and scope at write/read time.

### Monitoring

- **Promotion Rate**: Track how many candidates get promoted
- **Gate Failure Analysis**: Understand why content gets rejected
- **Quality Metrics**: Monitor the quality of promoted content

## Benefits

1. **Prevents False Personality**: No artificial emotional memory
2. **Maintains Objectivity**: Only factual, stable information
3. **Reduces Noise**: Filters out temporary/emotional content
4. **Improves Relevance**: Ensures long-term memory is actually useful
5. **Maintains Trust**: Users don't get confused by "remembered" emotions

## Anti-Patterns to Avoid

1. **First-Date Memory Tattoos**: Promoting information from first conversations
2. **Emotional Echo Chambers**: Remembering and reinforcing user emotions
3. **Context Drift**: Letting temporary situations become permanent memory
4. **Over-Personalization**: Creating a false sense of intimacy through memory
5. **Mood-Based Responses**: Using emotional memory to influence responses

## Conclusion

Memory Promotion Rules ensure that the system's long-term memory remains a reliable, objective repository of useful information rather than a collection of emotional artifacts. This maintains the assistant's professionalism and prevents the creation of artificial personality traits.

**Remember: Boring is beautiful when it comes to memory.**
