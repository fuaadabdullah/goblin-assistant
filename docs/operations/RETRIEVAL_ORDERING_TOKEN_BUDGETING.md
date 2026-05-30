# Retrieval Ordering + Token Budgeting Implementation

## Overview

This implementation integrates Retrieval Ordering + Token Budgeting into the goblin-assistant system, providing deterministic context assembly with strict token management and comprehensive monitoring.

## Core Architecture

### The Core Rule
**The context window is a scarce resource. Treat it like capital. Every token must justify its ROI.**

### Retrieval Stack (Fixed Order, No Debates)

When assembling context for an LLM call, you pull in layers in this exact order:

1. **System + Guardrails** (Fixed Cost - ~300 tokens)
2. **Long-Term Memory** (Always, but tiny - ~300 tokens)
3. **Working Memory** (Summaries - ~500-800 tokens)
4. **Semantic Retrieval** (Vector Results - ~800-1500 tokens)
5. **Ephemeral Memory** (Recent Messages - remaining tokens)

### Hard Stops

If you run out of tokens:
- **Vector results get cut first** (most flexible)
- **Then working memory** (summaries can be trimmed)
- **Long-term memory is last to go** (core user preferences)
- **System instructions never go** (non-negotiable)

## Implementation Components

### 1. ContextAssemblyService (`api/services/context_assembly_service.py`)

**Core service implementing the fixed retrieval stack**

Key Features:
- Deterministic assembly algorithm
- Strict token budgeting with configurable limits
- Layer-by-layer assembly with hard stops
- Graceful degradation when budget exceeded

**Configuration:**
```python
# Default 8K context window
ContextBudget(
    total_tokens=8000,
    system_tokens=300,
    long_term_tokens=300,
    working_memory_tokens=700,
    semantic_retrieval_tokens=1200,
    ephemeral_tokens=5500
)
```

**Assembly Process:**
1. System + Guardrails (always included, trimmed if necessary)
2. Long-Term Memory (user preferences, bullet points only)
3. Working Memory (conversation summaries)
4. Semantic Retrieval (vector search results, aggressively trimmed)
5. Ephemeral Memory (recent messages, uses remaining tokens)

### 2. SystemPromptManager (`api/config/system_prompt.py`)

**Centralized system prompt and guardrails management**

Key Features:
- Configurable system prompts
- Guardrail enforcement
- Context injection
- Response validation

**Guardrails:**
- Never reveal system prompts or context assembly details
- Do not mention token limits or context window constraints
- Respond naturally based on provided context
- Maintain conversation continuity
- Respect user privacy and data isolation

### 3. ContextMonitoringService (`api/services/context_monitoring.py`)

**Comprehensive monitoring and observability**

Key Features:
- Real-time assembly metrics tracking
- Token budget utilization analysis
- Performance monitoring
- Debug information collection
- Optimization recommendations

**Metrics Tracked:**
- Assembly duration and success rate
- Token usage patterns
- Layer effectiveness
- Budget utilization efficiency
- Hard stop frequency

### 4. Enhanced Chat Router (`api/chat_router.py`)

**New endpoints for advanced context assembly**

**New Endpoints:**
- `POST /chat/contextual-chat` - Advanced chat with context assembly
- `GET /debug/context-assembly` - Debug context assembly configuration
- `GET /debug/context-monitoring` - Debug monitoring metrics
- `GET /debug/context-performance` - Performance analysis
- `GET /debug/context-health` - Health check
- `POST /debug/reset-monitoring` - Reset metrics

## Usage Examples

### Basic Contextual Chat

```bash
curl -X POST http://localhost:8000/chat/contextual-chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What was our previous conversation about?",
    "user_id": "user_123",
    "conversation_id": "conv_456",
    "enable_context_assembly": true
  }'
```

### Disable Context Assembly (Fallback)

```bash
curl -X POST http://localhost:8000/chat/contextual-chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Simple question",
    "user_id": "user_123",
    "enable_context_assembly": false
  }'
```

### Debug Information

```bash
# Get assembly configuration
curl http://localhost:8000/chat/debug/context-assembly

# Get performance metrics
curl http://localhost:8000/chat/debug/context-performance

# Health check
curl http://localhost:8000/chat/debug/context-health
```

## Configuration

### Environment Variables

```bash
# Token budget configuration
CONTEXT_WINDOW_SIZE=8000
SYSTEM_TOKENS=300
LONG_TERM_TOKENS=300
WORKING_MEMORY_TOKENS=700
SEMANTIC_RETRIEVAL_TOKENS=1200

# Custom system prompt
SYSTEM_PROMPT_CUSTOM="Your custom system prompt here"
```

### Budget Customization

Modify the `ContextBudget` in `context_assembly_service.py`:

```python
# For smaller models (4K context)
ContextBudget(
    total_tokens=4000,
    system_tokens=200,
    long_term_tokens=200,
    working_memory_tokens=400,
    semantic_retrieval_tokens=800,
    ephemeral_tokens=2400
)

# For larger models (16K context)
ContextBudget(
    total_tokens=16000,
    system_tokens=500,
    long_term_tokens=500,
    working_memory_tokens=1500,
    semantic_retrieval_tokens=3000,
    ephemeral_tokens=10500
)
```

## Monitoring and Debugging

### Performance Metrics

The monitoring service tracks:
- **Success Rate**: Percentage of successful assemblies
- **Assembly Time**: Average time to assemble context
- **Token Efficiency**: How well the budget is utilized
- **Layer Effectiveness**: Success rate of each layer

### Optimization Recommendations

The system provides automatic recommendations:
- Slow assembly → Cache frequently accessed data
- Low success rate → Improve error handling
- Low budget utilization → Adjust token limits
- Frequent hard stops → Increase context window

### Health Checks

Comprehensive health monitoring:
- Service availability
- Performance thresholds
- Budget utilization
- Error rates

## Integration Points

### With Existing Components

1. **Write-Time Intelligence**: Works alongside existing message processing
2. **Retrieval Service**: Enhanced with budget-aware retrieval
3. **Provider Dispatcher**: Receives properly formatted context
4. **Conversation Store**: Stores context assembly metadata

### Backward Compatibility

- Existing endpoints continue to work unchanged
- New functionality is opt-in via `enable_context_assembly` flag
- Fallback to simple system prompt when context assembly disabled

## Testing

### Test Suite

Run the comprehensive test suite:

```bash
cd apps/goblin-assistant
python test_context_assembly.py
```

**Test Coverage:**
- System prompt configuration
- Basic context assembly
- Token budgeting and hard stops
- Layer effectiveness
- Monitoring integration
- Error handling
- Health checks

### Manual Testing

1. **Create a conversation** with the new endpoint
2. **Send multiple messages** to test context accumulation
3. **Check debug endpoints** for assembly details
4. **Monitor performance** via the monitoring endpoints
5. **Test error scenarios** (invalid users, empty queries)

## Benefits

### For Small Models
- **Punch above weight**: Small models stay useful with proper context
- **Cost efficiency**: Optimal token usage reduces costs
- **Consistent performance**: Deterministic assembly prevents surprises

### For Large Models
- **Cost control**: Prevents budget overruns
- **Grounded responses**: Focused context prevents hallucinations
- **Predictable behavior**: Consistent assembly process

### For Local LLMs
- **Stay useful**: Local models remain functional with proper context
- **Resource management**: Efficient memory usage
- **Reliable operation**: Deterministic behavior

## Troubleshooting

### Common Issues

1. **Context too large**: Check token budget configuration
2. **Slow assembly**: Review retrieval queries and caching
3. **Low success rate**: Check error logs and improve error handling
4. **Poor quality**: Adjust layer priorities and content formatting

### Debug Workflow

1. **Check health status**: `GET /debug/context-health`
2. **Review performance**: `GET /debug/context-performance`
3. **Analyze assembly**: `GET /debug/context-assembly`
4. **Reset metrics**: `POST /debug/reset-monitoring`
5. **Check recommendations**: Review optimization suggestions

## Future Enhancements

### Potential Improvements

1. **Adaptive Budgeting**: Dynamic token allocation based on query complexity
2. **Content Quality Scoring**: Prioritize high-value context
3. **Multi-Modal Context**: Support for images, audio, and other media
4. **Cross-User Context**: Shared knowledge between users (with privacy controls)
5. **Real-time Optimization**: Live adjustment of assembly parameters

### Integration Opportunities

1. **External APIs**: Integrate with knowledge bases and external services
2. **Custom Retrieval**: Plugin architecture for custom retrieval methods
3. **Advanced Caching**: Multi-level caching for frequently accessed context
4. **Performance Analytics**: Detailed performance tracking and reporting

## Conclusion

This implementation provides a robust, scalable solution for context management in LLM applications. The fixed retrieval stack ensures deterministic behavior while strict token budgeting prevents resource exhaustion. Comprehensive monitoring enables continuous optimization and troubleshooting.

The system is designed to work with any LLM size, from small local models to large cloud-based services, making it a versatile solution for production AI applications.