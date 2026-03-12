# 🔒 Privacy & Security Quick Reference

## Quick Commands

```bash
# Test sanitization
cd apps/goblin-assistant/api
python3 -c "from services.sanitization import sanitize_input_for_model; print(sanitize_input_for_model('test@example.com'))"

# Run all privacy tests
pytest tests/test_privacy_integration.py -v

# Deploy checks
bash scripts/deploy_privacy_features.sh

# Start Redis
redis-server

# RLS audit
bash scripts/ops/supabase_rls_check.sh
```

## API Endpoints

```bash
# Health check
GET /health

# Chat (with sanitization)
POST /api/chat
Body: {"message": "your message"}

# Export user data (GDPR Article 20)
POST /api/privacy/export
Headers: Authorization: Bearer {token}

# Delete user data (GDPR Article 17)
DELETE /api/privacy/delete
Headers: Authorization: Bearer {token}
```

## Code Examples

### Sanitize Input

```python
from services.sanitization import sanitize_input_for_model, is_sensitive_content

# Before sending to LLM
user_input = "Contact me at john@example.com"
clean_text, pii_found = sanitize_input_for_model(user_input)
# clean_text = "Contact me at [REDACTED]_EMAIL"
# pii_found = ['email']

# Check if sensitive
if is_sensitive_content(user_input):
    return {"error": "Sensitive content detected"}
```

### Log Metrics (Not Messages)

```python
from services.telemetry import log_inference_metrics

# ✅ DO THIS - log metrics only
log_inference_metrics(
    provider="openai",
    model="gpt-4",
    latency_ms=150,
    token_count=50,
    cost_usd=0.002,
    status_code=200
)

# ❌ DON'T DO THIS - never log raw messages
# logger.info(f"User said: {user_message}")  # WRONG!
```

### Add to Vector Store

```python
from services.safe_vector_store import SafeVectorStore

vector_store = SafeVectorStore()

# With consent and TTL
result = await vector_store.add_document(
    doc_id="doc_123",
    content="How to use Python",
    metadata={"source": "web"},
    user_id="user_456",
    consent_given=True,  # Required!
    ttl_hours=24
)
```

### Rate Limiting

```python
# Add to main.py
from middleware.rate_limiter import RateLimiter

app = FastAPI()
rate_limiter = RateLimiter(
    redis_url="redis://localhost:6379",
    requests_per_minute=100,
    requests_per_hour=1000
)
app.middleware("http")(rate_limiter)
```

## Environment Variables

```bash
# Required
REDIS_URL=redis://localhost:6379
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-key  # Store in Bitwarden!

# Privacy settings
ENABLE_PII_DETECTION=true
ENABLE_SANITIZATION=true
CONVERSATION_TTL_HOURS=1
```

## Deployment Checklist

- [ ] Copy `.env.privacy.example` to `.env`
- [ ] Install: `pip install -r requirements.txt`
- [ ] Start Redis: `redis-server`
- [ ] Run tests: `pytest tests/test_privacy_integration.py`
- [ ] RLS audit: `bash scripts/ops/supabase_rls_check.sh`
- [ ] Deploy migrations: `supabase db push`
- [ ] Deploy worker: `wrangler deploy`
- [ ] Deploy backend: `fly deploy`
- [ ] Test endpoints
- [ ] Monitor Datadog

## Key Principles

1. **Never log raw messages** - Only metrics
2. **Always sanitize** - Before LLM or storage
3. **Enforce TTL** - 1h for conversations, 24h for RAG
4. **Enable RLS** - On all user tables
5. **Require consent** - Before adding to vector store
6. **Hash user IDs** - In telemetry
7. **Rate limit** - All public endpoints
8. **Redact exports** - Mask sensitive fields

## Testing

```bash
# Unit tests
python3 -c "from services.sanitization import *; ..."

# Integration tests (requires Redis)
pytest tests/test_privacy_integration.py -v

# Manual API tests
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "test@example.com"}'
# Should reject or redact PII
```

## Monitoring

### Datadog Metrics
- `goblin.inference.latency` - Response time
- `goblin.inference.requests` - Request count
- `goblin.inference.errors` - Error rate
- `goblin.inference.cost` - Cost per request

### Alerts
- Rate limit exceeded
- PII detection rate spike
- TTL cleanup failures
- Consent rejection rate

## Troubleshooting

### Redis not connecting
```bash
# Check if running
redis-cli ping
# Should return PONG

# Start if not running
redis-server
```

### RLS blocking queries
```sql
-- Check policies
SELECT * FROM pg_policies WHERE tablename = 'conversations';

-- Test as user
SET ROLE authenticated;
SET request.jwt.claim.sub = 'user-id-here';
SELECT * FROM conversations;
```

### PII not detected
```python
# Test patterns
from services.sanitization import PII_PATTERNS
import re

text = "test@example.com"
for pattern_name, pattern in PII_PATTERNS.items():
    if re.search(pattern, text):
        print(f"Matched: {pattern_name}")
```

## Support

- Documentation: `docs/PRIVACY_IMPLEMENTATION.md`
- Full guide: `docs/PRIVACY_INTEGRATION_GUIDE.md`
- Deployment script: `scripts/deploy_privacy_features.sh`
- Tests: `tests/test_privacy_integration.py`

---

**Last Updated**: January 10, 2026
**Status**: ✅ Production Ready
