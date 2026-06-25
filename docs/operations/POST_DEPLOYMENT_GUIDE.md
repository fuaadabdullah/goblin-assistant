# Production Deployment - Post-Deployment Guide

## Current Status: Deployment In Progress ⏳

**Time Elapsed:** ~2-3 minutes  
**Expected Completion:** 5-10 minutes total  
**Components Status:**
- Backend (Render): Building...
- Frontend (Vercel): Building...

---

## 📊 Monitoring Dashboards

Open these in your browser and keep them visible:

### 1. Render Backend Dashboard
**URL:** https://dashboard.render.com/services/goblin-backend

**What to look for:**
- Status indicator: Should change from "Building" → "Live"
- Logs tab: Watch for `[INFO] Application startup complete`
- No errors like "Database connection failed" or "Redis timeout"

### 2. Vercel Frontend Dashboard
**URL:** https://vercel.com/dashboard/projects/goblin-assistant

**What to look for:**
- Deployments tab: Latest deployment should show green checkmark
- Build logs: `> Generated static files...` indicates success
- Preview link becomes active and accessible

### 3. Error Tracking (Sentry)
**URL:** https://sentry.io/organizations/goblin/

**What to look for:**
- No new critical errors appearing
- Health checks: Both frontend and backend projects reporting
- Version indicator: Should show `goblin-assistant@0.2.0`

---

## ⏱️ Deployment Timeline

```
NOW (T=0m)
│
├─ T=0m: ✅ Code pushed to GitHub
│
├─ T=0-1m: Webhooks trigger → Render & Vercel receive notification
│
├─ T=1-2m: Render starts building Docker image
│         Vercel starts building Next.js
│
├─ T=3-4m: Render container deploys
│         Vercel deployment completes
│
├─ T=4-5m: Services become "Live" ← You are here
│
├─ T=5-8m: ⏳ E2E tests can start
│
└─ T=8-10m: ✅ Production verification complete
```

---

## ✅ Verification Sequence

### Phase 1: Wait for Services (Now - 5 min from now)

**Do:**
- Monitor dashboards above
- Watch for status changes to "Live"
- Check Sentry for errors

**Don't:**
- Panic if it takes full 5 minutes (normal)
- Try accessing endpoints yet (will fail while building)

### Phase 2: Quick Health Check (T=5-6 min)

Once **both** show Live:

```bash
# Test backend
curl https://goblin-assistant-backend.onrender.com/health

# Test frontend loads
curl -I https://goblin-assistant.vercel.app

# Quick status
bash scripts/quick-verify-deployment.sh
```

### Phase 3: Full E2E Testing (T=6-10 min)

```bash
# Run comprehensive E2E test suite
bash scripts/e2e-production-test.sh
```

This tests:
- ✅ Authentication flow
- ✅ Chat functionality
- ✅ Mobile drawer UX
- ✅ Critical user paths

### Phase 4: Production Readiness Verification (T=10+ min)

**Checklist:**
- [ ] Backend health endpoint returns 200
- [ ] Frontend homepage loads without console errors
- [ ] Can access /chat endpoint
- [ ] Sentry shows no critical errors
- [ ] E2E tests all pass
- [ ] API responses are sub-1s latency
- [ ] No 5xx errors in backend

---

## 🔧 Troubleshooting During Deployment

### Symptom: Backend shows "Build failed"

**Action:**
1. Click "Logs" tab in Render dashboard
2. Scroll to red error messages
3. Common causes:
   - Docker build error (missing dependencies)
   - PORT not set in environment
   - Database connection string missing

**Solution:**
- Check Render Environment settings have all required vars:
  - `DATABASE_URL`
  - `REDIS_URL`
  - `SENTRY_DSN`
  - `ALLOWED_ORIGINS`

### Symptom: Frontend shows "Build failed"

**Action:**
1. Click failing deployment in Vercel
2. Check "Build" tab for error
3. Common causes:
   - TypeScript compilation error
   - Missing environment variable
   - Dependency resolution issue

**Solution:**
- Run locally: `npm run build` to reproduce
- Check `.env.production` is configured

### Symptom: Services Live but 503 errors

**Action:**
1. Check service logs
2. May indicate startup issues

**Solutions:**
- Backend: Check database connectivity
- Frontend: Check API URL configuration

---

## 📋 What Happens Next

### Automated Checks (If CI/CD enabled)

GitHub Actions will automatically:
- ✅ Run lint checks
- ✅ Run type checks
- ✅ Run unit tests
- ✅ Build artifacts
- ✅ Deploy to staging (if configured)

### Manual Verification You Should Do

1. **Now:** Monitor dashboards (link above)
2. **T=5m:** Quick health check (`bash scripts/quick-verify-deployment.sh`)
3. **T=6m:** Full E2E testing (`bash scripts/e2e-production-test.sh`)
4. **T=10m:** Check Sentry for errors
5. **T=15m:** Production deployment complete! 🎉

---

## 🆘 If Something Goes Wrong

### Quick Recovery

```bash
# Option 1: Re-trigger manual deployment (Render)
# Visit: https://dashboard.render.com/services/goblin-backend
# Click "Manual Deploy" button

# Option 2: Re-trigger manual deployment (Vercel)
# Visit: https://vercel.com/dashboard/projects/goblin-assistant
# Click deployment and select "Redeploy"

# Option 3: Rollback (if previous version exists)
# Select previous deployment from dashboard and click "Promote to Production"
```

### Debug Commands

```bash
# Check backend logs in real-time
tail -f render-backend.log

# Test API endpoint
curl -v https://goblin-assistant-backend.onrender.com/health | jq

# Test frontend
npx playwright test e2e/ --debug
```

---

## 📞 Support

| Issue | Resource |
|-------|----------|
| Render deployment | https://render.com/docs/deploy-docker |
| Vercel deployment | https://vercel.com/docs/deployments |
| Environment vars | Check service dashboards Settings tab |
| Build failures | View logs tab in service dashboard |
| Runtime errors | https://sentry.io for error tracking |

---

## 🎯 Success Criteria

**Deployment is successful when:**

- [ ] Backend service shows "Live" on Render
- [ ] Frontend deployment shows green checkmark on Vercel
- [ ] `curl https://goblin-assistant-backend.onrender.com/health` returns 200
- [ ] `https://goblin-assistant.vercel.app` loads without errors
- [ ] All E2E tests pass
- [ ] No critical errors in Sentry
- [ ] Users can complete auth → chat flow
- [ ] Mobile drawer functions correctly

---

## 📝 Important Notes

### About Environment Variables

Both services need specific env vars to function:

**Render Backend:**
- DATABASE_URL (PostgreSQL connection)
- REDIS_URL (Redis connection)
- SENTRY_DSN (Error tracking)
- ALLOWED_ORIGINS (CORS)
- API keys for LLM providers

**Vercel Frontend:**
- NEXT_PUBLIC_API_BASE_URL (Backend URL)
- NEXT_PUBLIC_GA_MEASUREMENT_ID (Analytics)
- Any other public env vars

### About Deployment Time

- First deployment: 5-15 minutes (includes Docker build)
- Subsequent: 2-5 minutes (uses cache)
- This deployment: ~5 minutes expected

### About Rollback

If critical issues found:
1. Render: Select previous "Deploy" from history
2. Vercel: Select previous deployment → click "Promote"
3. Takes 1-2 minutes to roll back

---

**Generated:** 2024-05-08 05:05 UTC  
**Version:** v0.2.0  
**Status:** Deployment in progress
