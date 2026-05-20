# Memory Stratification System

## Overview

The Goblin Assistant memory stratification system implements a three-tier memory architecture that transforms raw chat messages into structured, long-term knowledge. This system ensures that only valuable, stable information is retained while filtering out noise and temporary content.

## Architecture

### Three Memory Tiers

#### 1. Ephemeral Memory (Short-Term)
- **Purpose**: Conversational continuity and immediate context
- **Content**: Last 10-20 raw messages
- **Storage**: In-memory or fast cache
- **Lifespan**: Sliding window, no embeddings
- **Retrieval**: Never via vector search, only recent context

#### 2. Working Memory (Mid-Term)
- **Purpose**: Compressed conversation history and context
- **Content**: Rolling summaries of conversations
- **Storage**: Database with embeddings
- **Lifespan**: 7-30 days, updated via background jobs
- **Retrieval**: High priority in context building

#### 3. Long-Term Memory (Persistent Identity)
- **Purpose**: User traits, preferences, and stable facts
- **Content**: Distilled facts, preferences, user characteristics
- **Storage**: Database with embeddings and metadata
- **Lifespan**: Permanent, with consistency tracking
- **Retrieval**: Highest priority, forms assistant personality

## Message Classification Pipeline

### Classification Types

1. **CHAT** - General conversation, questions, casual talk
2. **FACT** - Statements about user background, skills, situation
3. **PREFERENCE** - Likes, dislikes, wants, needs, opinions
4. **TASK_RESULT** - Completed tasks, outputs, code, solutions
5. **SYSTEM** - Technical, memory, context, or system-related

### Classification Process

```python
# Example classification
message = "I am a software engineer with 5 years of Python experience"
classification = classifier.classify_message(message, "user")
# Result: FACT with high confidence
```

### Pattern Matching Rules

- **Fact patterns**: "I am", "My name is", "I live", "I work", "I have"
- **Preference patterns**: "I prefer", "I like", "I want", "I always"
- **Task patterns**: "Done", "Completed", "Here is", "Result"
- **System patterns**: "Memory", "Context", "Assistant", "System"

## Memory Promotion Pipeline

### Promotion Rules

1. **Confidence Threshold**: Minimum 80% confidence required
2. **Consistency Check**: Must not contradict existing memory
3. **Stability Filter**: Reject temporary or situational statements
4. **Duplicate Detection**: Semantic similarity > 85% = duplicate
5. **Content Quality**: Minimum length, no technical version specifics

### Promotion Process

```python
# Example promotion
promotion_result = await memory_promotion_service.promote_from_conversation(
    conversation_id="conv_123",
    user_id="user_456"
)
# Result: {"promoted_facts": 3, "rejected_facts": 2}
```

### Fact Categories

- **user_trait**: Name, age, location, occupation, background
- **preference**: Likes, dislikes, wants, needs
- **skill**: Knowledge, experience, expertise
- **goal**: Objectives, aims, purposes
- **constraint**: Limitations, restrictions, requirements
- **context**: Current situation, tools, environment

## Retrieval Priority System

### Priority Order

1. **Long-term memory facts** (score multiplier: 1.5)
2. **Working memory summaries** (score multiplier: 1.2)
3. **Relevant vector messages** (score: semantic + recency)
4. **Ephemeral recent messages** (score: 0.1)

### Retrieval Algorithm

```python
# Stratified retrieval
context = await retrieval_service.retrieve_context(
    query="What does the user prefer?",
    user_id="user_123",
    k=5  # Return top 5 results
)
# Results prioritized by memory tier
```

### Scoring Formula

```
Final Score = 
  (Semantic Similarity × Weight) +
  (Recency Decay × Weight) +
  (Source Priority × Weight)
```

## Schema Enhancements

### New Tables

1. **memory_items** - Enhanced long-term memory with promotion tracking
2. **memory_promotion_log** - Audit trail for promotion decisions
3. **memory_fact_extraction** - Track fact extraction from messages
4. **memory_consistency** - Track consistency checks between facts
5. **memory_usage** - Track retrieval patterns and usage

### Enhanced Fields

- **confidence**: 0.0-1.0 confidence score
- **consistency_score**: 0.0-1.0 consistency with existing memory
- **promotion_status**: promoted, rejected, duplicate
- **last_confirmed**: Timestamp of last confirmation
- **confirmation_count**: Number of times fact confirmed

## Background Tasks

### Periodic Operations

1. **Conversation Summarization** (every hour)
   - Summarize conversations with 10+ messages
   - Generate working memory summaries
   - Create embeddings for summaries

2. **Memory Promotion** (every 4 hours)
   - Extract facts from recent conversations
   - Apply promotion rules and consistency checks
   - Store promoted facts in long-term memory

3. **Index Optimization** (weekly)
   - Rebuild pgvector indexes
   - Optimize for performance
   - Maintain index health

4. **Cleanup Operations** (daily)
   - Remove old ephemeral messages
   - Archive old embeddings
   - Maintain database performance

## Integration Points

### Chat Router Integration

```python
# Enhanced chat processing
@router.post("/conversations/{conversation_id}/messages")
async def send_message(conversation_id: str, request: SendMessageRequest):
    # 1. Classify message
    classification = await classification_pipeline.process_message(
        message_id=message_id,
        content=request.message,
        role="user",
        conversation_id=conversation_id,
        user_id=conversation.user_id
    )
    
    # 2. Store with classification metadata
    await conversation_store.add_message_to_conversation(
        conversation_id=conversation_id,
        role="user",
        content=request.message,
        metadata={
            "classification": classification["classification"],
            "memory_type": classification["classification"]["type"]
        }
    )
```

### Retrieval Integration

```python
# Enhanced context building
context_bundle = await retrieval_service.get_context_bundle(
    query=user_message,
    user_id=user_id,
    conversation_id=conversation_id,
    max_tokens=2000
)

# Build prompt with stratified context
prompt = ContextBuilder.build_contextual_prompt(
    user_message=user_message,
    context_bundle=context_bundle,
    conversation_history=recent_messages
)
```

## Performance Characteristics

### Classification Performance
- **Latency**: < 10ms per message
- **Throughput**: 100+ messages/second
- **Accuracy**: > 85% for clear patterns

### Retrieval Performance
- **Latency**: < 100ms for context retrieval
- **Throughput**: 50+ queries/second
- **Accuracy**: > 90% relevant context

### Memory Efficiency
- **Storage**: Compressed embeddings (1536 dimensions)
- **Indexing**: IVFFLAT indexes for fast search
- **Cleanup**: Automatic cleanup of old data

## Monitoring and Observability

### Key Metrics

1. **Classification Metrics**
   - Classification accuracy by type
   - Confidence score distribution
   - Processing latency

2. **Promotion Metrics**
   - Promotion rate (facts promoted vs extracted)
   - Rejection reasons
   - Consistency check results

3. **Retrieval Metrics**
   - Retrieval latency
   - Context relevance score
   - Memory tier distribution

4. **System Health**
   - Database performance
   - Index health
   - Background task success rate

### Logging

```python
# Example logging
logger.info(f"Classified message as {classification.type} "
           f"with confidence {classification.confidence}")
logger.info(f"Promoted {promoted_count} facts from conversation {conv_id}")
logger.info(f"Retrieved {len(context)} context items for query")
```

## Configuration

### Environment Variables

```bash
# Memory system configuration
MEMORY_CONFIDENCE_THRESHOLD=0.8
MEMORY_CONSISTENCY_THRESHOLD=0.7
MEMORY_MAX_FACT_LENGTH=500
MEMORY_MIN_FACT_LENGTH=10

# Background task intervals
SUMMARIZATION_INTERVAL=3600  # 1 hour
PROMOTION_INTERVAL=14400     # 4 hours
CLEANUP_INTERVAL=86400       # 24 hours
```

### Database Configuration

```sql
-- Required indexes for performance
CREATE INDEX memory_items_user_category_idx ON memory_items(user_id, category);
CREATE INDEX memory_items_confidence_idx ON memory_items(confidence);
CREATE INDEX memory_items_embedding_idx ON memory_items USING ivfflat (fact_embedding vector_cosine_ops);
```

## Testing

### Test Coverage

1. **Unit Tests**
   - Message classification accuracy
   - Fact extraction logic
   - Promotion rule validation
   - Retrieval prioritization

2. **Integration Tests**
   - End-to-end pipeline testing
   - Database integration
   - Background task execution
   - Performance benchmarks

3. **Load Tests**
   - High message volume handling
   - Concurrent retrieval requests
   - Memory usage under load

### Test Commands

```bash
# Run unit tests
pytest api/tests/test_memory_stratification.py -v

# Run integration tests
pytest api/tests/test_memory_integration.py -v

# Run performance tests
pytest api/tests/test_memory_performance.py -v
```

## Troubleshooting

### Common Issues

1. **Low Classification Accuracy**
   - Check pattern matching rules
   - Verify message preprocessing
   - Review confidence thresholds

2. **Poor Retrieval Quality**
   - Check embedding quality
   - Verify scoring weights
   - Review priority system

3. **Performance Issues**
   - Monitor database indexes
   - Check background task load
   - Review memory usage

4. **Memory Inconsistencies**
   - Review contradiction detection
   - Check consistency scoring
   - Verify promotion rules

### Debug Commands

```python
# Debug classification
classification = classifier.classify_message("Test message", "user")
print(f"Type: {classification.message_type}, Confidence: {classification.confidence}")

# Debug retrieval
context = await retrieval_service.retrieve_context(
    query="Test query", 
    user_id="test_user"
)
print(f"Retrieved {len(context)} items")

# Debug promotion
summary = await memory_promotion_service.get_memory_summary("test_user")
print(f"Total facts: {summary['total_facts']}")
```

## Future Enhancements

### Planned Features

1. **Advanced NLP Integration**
   - Named entity recognition for facts
   - Sentiment analysis for preferences
   - Intent classification for tasks

2. **Machine Learning**
   - Adaptive classification thresholds
   - Personalized promotion rules
   - Predictive memory organization

3. **Memory Optimization**
   - Automatic memory consolidation
   - Smart forgetting for outdated facts
   - Memory compression techniques

4. **User Interface**
   - Memory management dashboard
   - Fact confirmation workflows
   - Memory usage analytics

### Research Areas

- **Memory Forgetting Models**: Implementing intelligent forgetting
- **Contextual Memory**: Memory that adapts to context
- **Multi-User Memory**: Shared memory across users
- **Temporal Memory**: Time-aware memory organization

## Security Considerations

### Data Privacy

- **User Isolation**: Strict separation of user data
- **Access Control**: Role-based access to memory data
- **Audit Logging**: Complete audit trail for memory operations

### Data Protection

- **Encryption**: Encrypt sensitive memory data
- **Backup**: Regular backups with encryption
- **Retention**: Configurable data retention policies

### Compliance

- **GDPR**: Right to be forgotten implementation
- **CCPA**: California privacy compliance
- **Industry Standards**: Follow security best practices

## Conclusion

The memory stratification system transforms the Goblin Assistant from a chatbot that remembers everything into an intelligent assistant that remembers correctly. By implementing selective remembrance, intentional forgetting, and promotion rules, the system ensures that only valuable, stable information becomes part of the assistant's persistent knowledge.

This architecture provides:

- **Better Performance**: Focused retrieval on relevant information
- **Improved Accuracy**: High-confidence, consistent memory
- **Enhanced User Experience**: Assistant that remembers what matters
- **Scalable Architecture**: Efficient storage and retrieval
- **Maintainable Code**: Clear separation of concerns

The system is designed to be conservative initially, preferring to miss some valid facts rather than store incorrect information. As the system matures, the promotion rules can be refined based on usage patterns and feedback.