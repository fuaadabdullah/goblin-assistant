# Privacy Implementation - Deployment Checklist

**Date**: January 10, 2026  
**Target**: Staging → Production  
**Est. Time**: 2-4 hours

## Pre-Deployment

### 1. Code Review (30 min)
- [ ] Review `api/services/sanitization.py`
- [ ] Review `api/services/safe_vector_store.py`
- [ ] Review `api/services/telemetry.py`
- [ ] Review `api/privacy_router.py`
- [ ] Review migration SQL file
- [ ] Check for any hardcoded secrets or test data

### 2. Testing (30 min)
- [ ] Run privacy tests: `pytest api/tests/test_privacy.py -v`
- [ ] Manual sanitization test (see below)
- [ ] Manual jailbreak detection test
- [ ] Verify no PII in test outputs

### 3. Documentation Review (15 min)
- [ ] Read `docs/PRIVACY_IMPLEMENTATION.md`
- [ ] Read `docs/PRIVACY_INTEGRATION_GUIDE.md`
- [ ] Read `PRIVACY_IMPLEMENTATION_SUMMARY.md`
- [ ] Understand rollback plan

## Staging Deployment

### 4. Database Migration (15 min)
```bash
# Backup current database
pg_dump goblin_assistant > backup_$(date +%Y%m%d).sql

# Apply migration
cd apps/goblin-assistant
supabase migration up

# Or manually via Supabase dashboard:
# - Copy supabase/migrations/20260110_privacy_schema_with_rls.sql
# - Execute in SQL Editor
```

- [ ] Migration applied successfully
- [ ] Verify tables created: `\dt` in psql
- [ ] Run RLS audit: `bash tools/supabase_rls_check.sh supabase/`
- [ ] Check RLS is enabled on all tables

### 5. Backend Integration (30 min)
```bash
# Install dependencies
pip install chromadb sentence-transformers datadog
```

- [ ] Dependencies installed
- [ ] Privacy router registered in `api/main.py`
- [ ] Sanitization integrated in chat endpoints
- [ ] SafeVectorStore integrated for RAG (if applicable)
- [ ] Environment variables configured

### 6. Restart Services (10 min)
```bash
# Restart backend
./start-backend.sh

# Check health
curl http://localhost:8004/health
```

- [ ] Backend started successfully
- [ ] Health check passes
- [ ] No errors in logs

### 7. Smoke Tests (30 min)
```bash
# Test privacy endpoints
curl -X GET http://localhost:8004/api/privacy/data-summary \
  -H "Authorization: Bearer <staging-token>"

curl -X POST http://localhost:8004/api/privacy/export \
  -H "Authorization: Bearer <staging-token>"
```

- [ ] `/api/privacy/data-summary` returns 200
- [ ] `/api/privacy/export` returns user data
- [ ] Chat endpoint sanitizes PII
- [ ] Jailbreak attempts are blocked
- [ ] No PII in logs

### 8. Monitor Staging (2-4 hours)
- [ ] Check logs for errors
- [ ] Verify sanitization is working
- [ ] Check database for RLS violations
- [ ] Monitor performance impact (<15ms added latency)
- [ ] Test with real user scenarios

## Production Deployment

### 9. Pre-Production Checklist
- [ ] Staging tests passed for 4+ hours
- [ ] No critical issues found
- [ ] Team sign-off obtained
- [ ] Rollback plan reviewed
- [ ] Incident response plan ready

### 10. Production Database (15 min)
```bash
# Backup production database
pg_dump goblin_assistant_prod > backup_prod_$(date +%Y%m%d).sql

# Apply migration to production
supabase migration up --environment production
```

- [ ] Production backup created
- [ ] Migration applied
- [ ] RLS audit passed
- [ ] Tables verified

### 11. Production Backend (30 min)
- [ ] Dependencies installed
- [ ] Environment variables configured
- [ ] Privacy router registered
- [ ] Services restarted
- [ ] Health checks pass

### 12. Production Smoke Tests (15 min)
```bash
# Test production privacy endpoints
curl -X GET https://goblin-assistant-backend.onrender.com/api/privacy/data-summary \
  -H "Authorization: Bearer <prod-token>"
```

- [ ] All privacy endpoints working
- [ ] Sanitization active
- [ ] Jailbreak detection active
- [ ] No PII in logs

### 13. Monitoring Setup (30 min)
- [ ] Datadog configured (if enabled)
- [ ] Set up PII detection alerts
- [ ] Set up privacy request monitoring
- [ ] Set up TTL cleanup monitoring
- [ ] Configure error alerts

### 14. Schedule TTL Cleanup (15 min)
```sql
-- Enable pg_cron
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Schedule hourly cleanup
SELECT cron.schedule(
    'cleanup-conversations',
    '0 * * * *',
    'SELECT cleanup_expired_conversations()'
);

-- Verify job scheduled
SELECT * FROM cron.job;
```

- [ ] pg_cron enabled
- [ ] Cleanup job scheduled
- [ ] Job runs successfully

## Post-Deployment

### 15. Verification (1 hour)
- [ ] Monitor logs for 1 hour
- [ ] Verify no errors or warnings
- [ ] Check sanitization metrics
- [ ] Verify RLS is working
- [ ] Test privacy endpoints with real users

### 16. Documentation Updates (30 min)
- [ ] Update team documentation
- [ ] Update privacy policy (if needed)
- [ ] Update API documentation
- [ ] Notify team of new endpoints

### 17. Team Training (1 hour)
- [ ] Present implementation to team
- [ ] Demo privacy features
- [ ] Review best practices
- [ ] Q&A session

### 18. Final Checks (15 min)
- [ ] All checklist items complete
- [ ] No critical issues
- [ ] Monitoring active
- [ ] Team trained
- [ ] Documentation complete

## Rollback Plan (If Needed)

### Immediate Rollback
```bash
# 1. Disable privacy router in api/main.py
# Comment out: app.include_router(privacy_router)

# 2. Restart services
./start-backend.sh

# 3. Monitor for stabilization
```

### Database Rollback (If Necessary)
```sql
-- Drop new tables
DROP TABLE IF EXISTS privacy_audit_log;
DROP TABLE IF EXISTS user_preferences;
DROP TABLE IF EXISTS inference_logs;
DROP TABLE IF EXISTS conversations;

-- Restore from backup
psql goblin_assistant < backup_20260110.sql
```

## Success Criteria

- ✅ All tests passing
- ✅ No PII in logs or telemetry
- ✅ Privacy endpoints working
- ✅ RLS enforced
- ✅ TTL cleanup running
- ✅ Performance impact <15ms
- ✅ No critical errors
- ✅ Team trained

## Monitoring Metrics

### Key Metrics to Track
1. PII detection rate (expect 1-5%)
2. Privacy request volume (exports, deletes)
3. TTL cleanup efficiency (expired docs)
4. Performance impact (latency)
5. Error rates (should not increase)

### Alerts to Set Up
- High PII detection rate (>10 in 5min)
- Privacy deletion failures
- Consent violations
- TTL cleanup failures
- RLS policy violations

## Contact & Support

**Deployment Lead**: [Your Name]  
**On-Call Engineer**: [Engineer Name]  
**Documentation**: `docs/PRIVACY_IMPLEMENTATION.md`  
**Incident Response**: [Incident Response Plan]

---

**Status**: [ ] Not Started | [ ] In Progress | [ ] Complete  
**Deployed By**: _________________  
**Date/Time**: _________________  
**Sign-off**: _________________
