# Memory Promotion Guidelines

## Overview

Memory Promotion Rules ensure that long-term memory stays **boring, stable, and provable**. This prevents the system from creating a false personality or storing unstable, emotional information.

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