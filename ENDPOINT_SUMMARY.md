This document has moved into the canonical backend documentation folder:

- apps/goblin-assistant/backend/docs/ENDPOINT_SUMMARY.md

Please update any references or links to point to the new location.

# Endpoint Audit Summary - December 2, 2025

## ✅ Status: Production Ready

All endpoint mismatches have been fixed and the build passes. The frontend API client is now fully compatible with the backend routes.

---

## Key Changes

### 1. Settings Endpoints (30+ fixes)

- Fixed provider update to use name (not ID)
- Fixed test-connection to use query params
- Fixed priority endpoint method (POST, not PATCH)
- Fixed reorder body structure
- Added backward-compatible wrappers for legacy hooks

### 2. Search Endpoints

- Replaced non-existent endpoints with correct `/search/query` path
- Added collection document retrieval
- Made methods accept both ID and name for backward compatibility

### 3. API Keys

- Changed from ID-based to provider-based access
- All CRUD operations now use provider name

### 4. Orchestration

- Fixed paths from `/api/orchestrate/*` to `/execute/*`
- Added missing execution status endpoint

### 5. Health Endpoints (Previously Fixed)

- All enhanced monitoring endpoints corrected (`/health/*/status`)

---

## Production Deployment Checklist

### Critical (Before Deploy)

- [ ] **CORS**: Update `main.py` to restrict origins to production domains
- [ ] **API Keys**: Verify all provider keys in backend `.env`
- [ ] **Database**: Run migrations and seed provider configs
- [ ] **Environment**: Set `VITE_FASTAPI_URL` to production backend URL

### Important (First Week)

- [ ] Add rate limiting middleware
- [ ] Configure structured JSON logging
- [ ] Set up monitoring/alerting (Sentry)
- [ ] Load test chat and health endpoints

### Recommended

- [ ] Set backend timeout to 60s for LLM calls
- [ ] Enable request/response logging for debugging
- [ ] Set up automated health checks
- [ ] Configure backup/restore for database

---

## Files Changed

1. **`src/api/client-axios.ts`** - Fixed 30+ endpoint mismatches, added backward-compatible methods
2. **`ENDPOINT_AUDIT.md`** - Comprehensive audit documentation with all backend routes
3. **`ENDPOINT_SUMMARY.md`** - This quick reference (you are here)

---

## Quick Verification

### Backend Health

```bash
curl http://localhost:8001/health/all | jq
```

### Frontend Build

```bash

cd apps/goblin-assistant
npm run build
```

Expected: ✓ built in ~6s

### Integration Test

```bash
# Start backend
cd apps/goblin-assistant/backend
uvicorn main:app --host 0.0.0.0 --port 8001 --env-file .env

# Start frontend
cd apps/goblin-assistant
npm run dev

# Open browser
open http://localhost:3000
```

---

## Backend Routes Summary

| Router   | Prefix      | Key Endpoints                           |
| -------- | ----------- | --------------------------------------- |
| Auth     | `/auth`     | register, login, google, passkey        |
| Health   | `/health`   | all, chroma, mcp, raptor, sandbox, cost |
| Chat     | `/chat`     | completions, models, routing-info       |
| Settings | `/settings` | providers, models, test-connection      |
| Routing  | `/routing`  | providers, capabilities, route          |
| Execute  | `/execute`  | orchestrate, parse, status              |
| Sandbox  | `/sandbox`  | jobs, logs, artifacts                   |
| Search   | `/search`   | query, collections, documents           |
| API      | `/api`      | goblins, history, stats, route_task     |
| Raptor   | `/raptor`   | start, stop, status, logs               |
| Stream   | `/stream`   | SSE streaming                           |
| API Keys | `/api-keys` | get, set, delete (by provider)          |

---

## Known Issues & Workarounds

### Issue: AI Providers Unreachable

**Symptom**: Health check shows "degraded", chat returns "No providers available"
**Cause**: API keys invalid or network connectivity issues
**Fix**: Verify keys in `backend/.env` and test with `curl https://api.openai.com`

### Issue: testProviderConnection uses ID

**Symptom**: UI passes provider ID but backend expects name
**Fix**: Added wrapper method that accepts both ID and name

### Issue: createCollection not implemented

**Symptom**: Hook calls non-existent endpoint
**Fix**: Method now throws clear error; update UI to remove create collection feature

---

## Next Actions

1. ✅ Endpoint audit complete
2. ✅ Build passing
3. ✅ Backward compatibility ensured
4. ⏭️ Update CORS for production
5. ⏭️ Configure provider database
6. ⏭️ Deploy to staging
7. ⏭️ Load test critical paths

---

**Audit Date**: December 2, 2025
**Build Status**: ✓ PASSING
**Production Ready**: YES (with checklist items)
**Next Review**: Post-deployment (1 week)
