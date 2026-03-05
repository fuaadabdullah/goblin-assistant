# Render Deployment Guide - Goblin Assistant Backend

## Overview
This guide walks you through deploying the Goblin Assistant Backend with **Sentry error tracking** to Render.com.

## Prerequisites
- Render.com account: https://dashboard.render.com
- GitHub repo connected to Render (for auto-deployment)
- Sentry account with DSN ready

## Quick Start

### Step 1: Create Render Service

1. Go to: https://dashboard.render.com/services
2. Click **+ New**
3. Select **Web Service**
4. **Connect GitHub** (or select existing repo)
5. Fill in:
   - **Name**: `goblin-backend`
   - **Runtime**: `Docker`
   - **Region**: `Oregon` (or closest)
   - **Plan**: `Standard` ($7/month+)

### Step 2: Set Environment Variables in Render Dashboard

In the **Environment** section, add these variables:

```
ENVIRONMENT=production
DEBUG=false
PORT=8001
RELEASE_VERSION=goblin-assistant@1.0.0
LOG_LEVEL=info

# Error Tracking - Sentry
SENTRY_DSN=https://c83d4d3b7bb2e74b4620e389a540cce6@o4510137545392128.ingest.us.sentry.io/4510991382347776

# API Configuration
ALLOWED_ORIGINS=https://goblin.fuaad.ai,https://api.goblin.fuaad.ai,https://brain.goblin.fuaad.ai,https://ops.goblin.fuaad.ai
NEXT_PUBLIC_API_BASE_URL=https://api.goblin.fuaad.ai
NEXT_PUBLIC_BACKEND_URL=https://api.goblin.fuaad.ai
NEXT_PUBLIC_FASTAPI_URL=https://api.goblin.fuaad.ai
NEXT_PUBLIC_FRONTEND_URL=https://goblin.fuaad.ai

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# GCP LLM Endpoints
OLLAMA_GCP_URL=http://34.60.255.199:11434
LLAMACPP_GCP_URL=http://34.132.226.143:8000
```

### Step 3: Add Secret Environment Variables

Click **Add Private File/Environment Variable** for each:

```
SENTRY_DSN=https://c83d4d3b7bb2e74b4620e389a540cce6@o4510137545392128.ingest.us.sentry.io/4510991382347776
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
JWT_SECRET_KEY=your-secret-key
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_AI_API_KEY=AIz...
AZURE_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://...
```

### Step 4: Configure Build & Startup

In Render dashboard settings:

- **Build Command**: (leave default or use)
  ```
  pip install --upgrade pip && pip install -r requirements.txt
  ```

- **Start Command**: (leave default: Render auto-detects from Dockerfile)
  ```
  uvicorn api.main:app --host 0.0.0.0 --port $PORT
  ```

- **Dockerfile Path**: `./Dockerfile` (default)

### Step 5: Add Custom Domain (Optional)

1. In Render service settings, go to **Custom Domain**
2. Add: `api.goblin.fuaad.ai`
3. Follow DNS instructions to point domain

## Verification

### Check Startup Logs
1. Go to **Logs** tab in Render dashboard
2. Look for:
   ```
   {"provider": "sentry", "error_monitoring": "enabled", "event": "Sentry SDK initialized"}
   ```

### Test Endpoints

After deployment:

```bash
# Health check
curl https://api.goblin.fuaad.ai/health
# Expected: {"status":"healthy"}

# Sentry test (verify error tracking)
curl https://api.goblin.fuaad.ai/sentry-debug
# Expected: 500 Internal Server Error (error captured by Sentry)
```

### View Errors in Sentry
Visit: https://o4510137545392128.ingest.us.sentry.io/issues/

You should see the test error with:
- Error type: `ZeroDivisionError`
- Endpoint: `GET /sentry-debug`
- Environment: `production`
- Release: `goblin-assistant@1.0.0`

## Auto-Deployment Setup

### GitHub Integration
1. In Render dashboard, go to **Settings**
2. Ensure GitHub is connected
3. Select branch: `main` (or desired)
4. **Deploy on every push** is enabled by default

### Webhook URL (if using alternative git host)
Get from: **Render Dashboard** → **Settings** → **Deploy Hooks**

## Troubleshooting

### Build Fails
```
Error: No module named 'api'
```
**Fix**: Ensure `requirements.txt` has all dependencies, check `PYTHONPATH=.` is set in Dockerfile

### Health Check Fails
```
Health check failed for service
```
**Fix**: 
1. Check `/health` endpoint responds with 200
2. Wait 30-60 seconds (Render has startup delay)
3. Check logs for startup errors

### Sentry Not Initializing
```
❌ SENTRY_DSN not configured
```
**Fix**:
1. Verify `SENTRY_DSN` is set in Environment Variables
2. Restart service (Render dashboard → Manual Deploy)
3. Check logs for initialization message

### Datadog Still Showing
Old code is still running
**Fix**:
1. Force redeploy: **Render Dashboard** → **Trigger Deploy** → **Redeploy latest commit**
2. If still old, rebuild: **Clear build cache** option

## Monitoring & Alerts

### Sentry Configuration
- Visit: https://sentry.io/organizations/goblin-assistant/
- Set up alerts for errors
- Configure sampling rates (adjust `traces_sample_rate` if needed)

### Performance Monitoring
- Visit: **Sentry** → **Performance** tab
- View transaction times, database queries, external requests

## Cost & Scaling

| Component | Cost | Notes |
|-----------|------|-------|
| Render Web | $7/month | Cheapest tier, 0.5 CPU, 512MB RAM |
| Render Redis (optional) | $6/month | For caching |
| Render PostgreSQL (optional) | $15/month | For database (using Supabase instead) |
| Sentry Free | $0 | 5,000 events/month free tier |

**To scale**: Upgrade Render plan in dashboard

## Next Steps

1. ✅ Create Render service (connect GitHub)
2. ✅ Set all environment variables
3. ✅ Trigger initial deployment
4. ✅ Verify logs show "Sentry SDK initialized"
5. ✅ Test `/health` endpoint
6. ✅ Test `/sentry-debug` endpoint
7. ✅ Check Sentry dashboard for captured error
8. ✅ Optional: Remove `/sentry-debug` endpoint after verification

## Support

- **Render Docs**: https://render.com/docs
- **Sentry Docs**: https://docs.sentry.io/platforms/python/
- **Dockerfile Issues**: Check `./Dockerfile` for correct base image and dependencies
