# Observability Cultural Rules

## The Prime Directive

**If a decision affects memory, retrieval, routing, or context, it must be inspectable. No black boxes. No "the model decided."**

This is our core principle that guides all observability decisions. Every system component must be transparent about its decision-making process.

## Observability Philosophy

### 1. **Transparency Over Convenience**
- Always prefer explicit logging over implicit behavior
- Every decision point must have a corresponding observability event
- No silent failures or hidden state changes
- If you can't explain it, you shouldn't implement it

### 2. **Actionable Insights**
- Observability data must enable concrete debugging actions
- Every log entry should answer "What happened?" and "Why?"
- Metrics should highlight system health issues before they become critical
- Debug endpoints must provide complete context for investigation

### 3. **No Black Boxes**
- Every LLM call must be traced with full context
- Memory promotion decisions must be auditable
- Retrieval results must be inspectable
- Context assembly must be reproducible

### 4. **Human-Readable First**
- Debug output should be understandable without specialized tools
- Use clear, descriptive field names
- Include sufficient context for standalone analysis
- Avoid cryptic abbreviations or internal jargon

## Decision Logging Standards

### Write-Time Decisions
Every message processed must log:
- **What**: Message content (redacted for privacy)
- **Why**: Classification reasoning and decision rules applied
- **How**: Actions taken (embed, summarize, cache, discard)
- **Confidence**: Model confidence in classification
- **Context**: User ID, conversation ID, timestamp

### Memory Promotion
Every memory promotion attempt must log:
- **Candidate**: Content being evaluated
- **Source**: Where the content originated
- **Gates**: Which promotion gates passed/failed
- **Reason**: Specific reasons for acceptance/rejection
- **Confidence**: Confidence score for the decision

### Retrieval Tracing
Every retrieval operation must log:
- **Query**: What was being searched for
- **Results**: What was found, with scores and metadata
- **Budget**: Token usage and allocation decisions
- **Performance**: Timing and efficiency metrics
- **Quality**: Relevance and completeness indicators

## Debug Surface Standards

### Endpoint Naming
- Use clear, descriptive paths: `/debug/write/decisions/{id}`
- Include the affected system in the path
- Use consistent verbs: `get`, `list`, `search`, `trace`
- Support filtering and pagination for large datasets

### Response Format
- Always include metadata about the query and results
- Use consistent field names across all endpoints
- Include timestamps for all events
- Provide both raw data and computed metrics

### Error Handling
- Return meaningful error messages for debugging
- Include request IDs for correlation
- Log errors to observability systems before returning
- Never expose sensitive data in error responses

## Privacy and Security

### Data Redaction
- Always redact sensitive content in logs and debug output
- Use content hashes for identification without exposure
- Implement configurable redaction rules
- Never log full user messages in production

### Access Control
- Debug endpoints require elevated permissions
- Audit all access to observability data
- Implement rate limiting on debug endpoints
- Log all debug access attempts

### Data Retention
- Observability data has shorter retention than operational data
- Implement automatic cleanup of old observability records
- Separate observability storage from user data
- Consider observability data in data deletion requests

## Performance Considerations

### Observability Overhead
- Observability logging should not significantly impact performance
- Use asynchronous logging where possible
- Implement sampling for high-volume events
- Provide observability toggle switches for production

### Debug Endpoint Performance
- Debug endpoints should not impact production performance
- Implement caching for frequently accessed observability data
- Use pagination and filtering to limit response size
- Monitor debug endpoint usage and performance

## Integration Patterns

### Service Integration
- Every service must integrate with the observability system
- Use the global observability service for consistency
- Implement observability in service initialization
- Provide service-specific debug endpoints

### Event Correlation
- Use request IDs to correlate events across services
- Include context information in all observability events
- Implement distributed tracing for complex operations
- Provide tools for cross-service debugging

## Testing and Validation

### Observability Testing
- Test all observability logging paths
- Validate debug endpoint responses
- Verify data redaction works correctly
- Test observability performance impact

### Debug Workflow Testing
- Test complete debugging workflows
- Validate that observability data enables problem resolution
- Test cross-service correlation
- Verify alert accuracy and usefulness

## Alerting Standards

### Alert Quality
- Alerts must be actionable and specific
- Include sufficient context for immediate investigation
- Avoid alert fatigue through careful threshold tuning
- Provide clear resolution steps

### Alert Categories
- **Critical**: System failures requiring immediate attention
- **Warning**: Performance degradation or potential issues
- **Info**: Operational events for awareness

### Alert Channels
- Route critical alerts to immediate response channels
- Use different channels for different alert severities
- Implement alert escalation procedures
- Provide alert history and trends

## Continuous Improvement

### Observability Review
- Regularly review observability effectiveness
- Update logging based on debugging experience
- Refine alert thresholds based on false positive rates
- Add new observability points as system complexity grows

### Documentation Maintenance
- Keep observability documentation current
- Document new debug workflows and patterns
- Share debugging best practices across the team
- Maintain examples of common debugging scenarios

## Examples

### Good Observability Logging
```python
# ✅ Good: Clear, actionable, with context
logger.info(
    "Write-time decision made",
    message_type="task_result",
    actions=["embed", "summarize"],
    confidence=0.95,
    user_id="user_123",
    conversation_id="conv_456"
)

# ❌ Bad: Unclear, missing context
logger.info("Decision made", type="task", actions=["embed"])
```

### Good Debug Endpoint
```python
# ✅ Good: Clear path, filtering, pagination
@router.get("/debug/memory/user/{user_id}")
async def get_user_memory(
    user_id: str,
    limit: int = Query(100, description="Number of items to return")
) -> Dict[str, Any]:
    # Returns structured data with metadata

# ❌ Bad: Unclear purpose, no filtering
@router.get("/debug/{user_id}")
async def debug_user(user_id: str):
    # Returns unstructured data
```

## Implementation Checklist

- [ ] Every decision point has corresponding observability logging
- [ ] All debug endpoints follow naming and response standards
- [ ] Data redaction is implemented for sensitive content
- [ ] Access control is enforced on debug endpoints
- [ ] Performance impact of observability is measured and acceptable
- [ ] Alert thresholds are tuned to minimize false positives
- [ ] Observability documentation is complete and current
- [ ] Debug workflows are tested and validated

## Cultural Adoption

### Team Training
- All team members understand the Prime Directive
- Observability is considered during feature design
- Debugging skills are developed and maintained
- Observability best practices are shared regularly

### Code Review Standards
- Observability logging is reviewed as part of all changes
- Debug endpoints are tested during code review
- Performance impact of observability is considered
- Privacy and security of observability data is verified

### Incident Response
- Observability data is the first place to look during incidents
- Debug endpoints are used to gather investigation data
- Observability gaps are identified and addressed after incidents
- Post-incident reviews include observability effectiveness

By following these cultural rules, we ensure that our system remains debuggable, maintainable, and trustworthy as it grows in complexity.