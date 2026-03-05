# Privacy Implementation Integration Guide

## Quick Start

### 1. Install Dependencies

```bash
cd apps/goblin-assistant/api
pip install chromadb sentence-transformers datadog
```

### 2. Apply Database Migration

```bash
# Using Supabase CLI
cd apps/goblin-assistant
supabase migration up

# Or manually via Supabase dashboard
# Copy contents of supabase/migrations/20260110_privacy_schema_with_rls.sql
# and execute in SQL Editor
```

### 3. Integrate Sanitization in Chat Router

Update `api/chat_router.py`:

```python
from api.services.sanitization import (
    sanitize_input_for_model,
    check_jailbreak_attempt
)
from api.services.telemetry import log_inference_metrics, log_conversation_event, EventType

@router.post("/chat")
async def chat(request: ChatRequest, user_id: str = Depends(get_current_user)):
    """Chat endpoint with privacy protection."""
    
    # Check for jailbreak attempts
    is_jailbreak, reason = check_jailbreak_attempt(request.message)
    if is_jailbreak:
        raise HTTPException(status_code=400, detail=f"Invalid prompt: {reason}")
    
    # Sanitize user input
    clean_message, pii_detected = sanitize_input_for_model(request.message)
    
    if pii_detected:
        logger.warning(f"PII detected in user message: {pii_detected}")
        # Optionally: notify user that PII was removed
    
    # Log conversation event (NO raw message)
    log_conversation_event(
        event_type=EventType.CONVERSATION_MESSAGE,
        user_id=user_id,
        session_id=request.session_id
    )
    
    # Call LLM with sanitized input
    start_time = time.time()
    response = await llm_provider.generate(clean_message)
    latency_ms = int((time.time() - start_time) * 1000)
    
    # Log inference metrics (NO raw message)
    log_inference_metrics(
        provider=llm_provider.name,
        model=request.model,
        latency_ms=latency_ms,
        token_count=response.token_count,
        cost_usd=response.cost,
        status_code=200,
        user_id=user_id
    )
    
    return {"response": response.text}
```

### 4. Integrate SafeVectorStore for RAG

Update your RAG service:

```python
from api.services.safe_vector_store import SafeVectorStore

# Initialize store
vector_store = SafeVectorStore(
    collection_name="goblin_rag",
    persist_directory="./chroma_db",
    default_ttl_hours=24
)

async def add_to_rag(
    user_id: str,
    document: str,
    metadata: dict,
    consent_given: bool
):
    """Add document to RAG with privacy checks."""
    
    result = await vector_store.add_document(
        doc_id=f"doc_{user_id}_{int(time.time())}",
        content=document,
        metadata=metadata,
        user_id=user_id,
        consent_given=consent_given,
        ttl_hours=24
    )
    
    if not result["success"]:
        logger.error(f"Failed to add to RAG: {result['error']}")
        return {"error": result["error"]}
    
    return result

async def query_rag(user_id: str, query: str):
    """Query RAG with user isolation."""
    
    results = await vector_store.query_documents(
        query_text=query,
        user_id=user_id,
        n_results=5,
        include_expired=False
    )
    
    return results
```

### 5. Register Privacy Router

Update `api/main.py`:

```python
from api.privacy_router import router as privacy_router

app = FastAPI()

# Register privacy routes
app.include_router(privacy_router)
```

### 6. Set Up Scheduled TTL Cleanup

**Option A: Using Supabase pg_cron (Recommended)**

```sql
-- Enable pg_cron extension
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Schedule hourly cleanup
SELECT cron.schedule(
    'cleanup-conversations',
    '0 * * * *',
    'SELECT cleanup_expired_conversations()'
);
```

**Option B: Using Python Background Tasks**

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from api.services.safe_vector_store import SafeVectorStore

scheduler = AsyncIOScheduler()

async def cleanup_expired_data():
    """Clean up expired data from vector store."""
    vector_store = SafeVectorStore()
    result = await vector_store.cleanup_expired()
    logger.info(f"Cleanup: deleted {result['deleted_count']} expired docs")

# Schedule to run hourly
scheduler.add_job(cleanup_expired_data, 'cron', hour='*')
scheduler.start()
```

### 7. Configure Datadog (Optional)

Update `.env.production`:

```bash
ENABLE_DATADOG=true
DATADOG_AGENT_HOST=localhost
DATADOG_AGENT_PORT=8125
```

Install Datadog agent:

```bash
# See apps/goblin-assistant/docs/PRODUCTION_MONITORING.md
```

### 8. Test Privacy Features

```bash
# Run privacy tests
cd apps/goblin-assistant/api
pytest tests/test_privacy.py -v

# Test sanitization
python3 -c "
from api.services.sanitization import sanitize_input_for_model
text = 'My email is test@example.com'
clean, pii = sanitize_input_for_model(text)
print(f'Clean: {clean}')
print(f'PII detected: {pii}')
"

# Test privacy endpoints
curl -X POST http://localhost:8004/api/privacy/data-summary \
  -H "Authorization: Bearer <token>"
```

## Environment Variables

Add to `.env.local`:

```bash
# Privacy settings
ENVIRONMENT=development
ENABLE_DATADOG=false

# Vector store
CHROMA_PERSIST_DIRECTORY=./chroma_db
DEFAULT_TTL_HOURS=24

# Supabase (for RLS)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<service-role-key>
```

## Deployment Checklist

- [ ] Database migration applied (`20260110_privacy_schema_with_rls.sql`)
- [ ] RLS audit passed (`bash tools/supabase_rls_check.sh supabase/`)
- [ ] Privacy tests passing (`pytest tests/test_privacy.py`)
- [ ] Privacy router registered in `main.py`
- [ ] Sanitization integrated in chat endpoints
- [ ] SafeVectorStore integrated for RAG
- [ ] TTL cleanup scheduled (pg_cron or APScheduler)
- [ ] Datadog configured (production only)
- [ ] Privacy policy updated with new data handling procedures
- [ ] Team trained on privacy best practices

## Monitoring

### Key Metrics to Track

1. **PII Detection Rate**:
   ```sql
   SELECT COUNT(*) as pii_detections
   FROM inference_logs
   WHERE metadata->>'pii_detected' = 'true'
   AND created_at > NOW() - INTERVAL '24 hours';
   ```

2. **Privacy Requests**:
   ```sql
   SELECT action, COUNT(*) as count
   FROM privacy_audit_log
   WHERE created_at > NOW() - INTERVAL '7 days'
   GROUP BY action;
   ```

3. **TTL Cleanup Effectiveness**:
   ```sql
   SELECT COUNT(*) as expired_conversations
   FROM conversations
   WHERE expires_at < NOW();
   ```

## Troubleshooting

### Issue: PII Still Appears in Logs

**Solution**: Ensure all logging uses `redact_for_logging()`:

```python
from api.services.sanitization import redact_for_logging

# Instead of:
# logger.info(f"User message: {message}")

# Do:
log_data = redact_for_logging(message)
logger.info(f"Message: hash={log_data['message_hash']}, len={log_data['length']}")
```

### Issue: RAG Storage Failing

**Check**:
1. User has given consent: `user.rag_consent_given == True`
2. No PII in document: `is_sensitive_content(document) == False`
3. ChromaDB is running and accessible

### Issue: RLS Policies Not Working

**Check**:
1. RLS is enabled: `ALTER TABLE ... ENABLE ROW LEVEL SECURITY;`
2. Policies are created: `\dp <table>` in psql
3. Using `auth.uid()` in queries (not raw user_id)

### Issue: TTL Cleanup Not Running

**Check**:
1. pg_cron extension is installed: `SELECT * FROM pg_extension WHERE extname = 'pg_cron';`
2. Job is scheduled: `SELECT * FROM cron.job;`
3. Job is running: `SELECT * FROM cron.job_run_details ORDER BY start_time DESC LIMIT 10;`

## Next Steps

1. Review [PRIVACY_IMPLEMENTATION.md](./PRIVACY_IMPLEMENTATION.md) for full details
2. Update privacy policy to reflect new data handling
3. Train team on privacy best practices
4. Set up monitoring alerts in Datadog
5. Schedule quarterly privacy audits

## Support

For questions or issues:
- **Documentation**: `apps/goblin-assistant/docs/PRIVACY_IMPLEMENTATION.md`
- **Tests**: `apps/goblin-assistant/api/tests/test_privacy.py`
- **Team**: Engineering team

---

**Last Updated**: 2026-01-10
