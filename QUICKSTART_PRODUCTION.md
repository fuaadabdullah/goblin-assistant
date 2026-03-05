# 🎉 Production Deployment - Quick Reference

This document contains a mix of backend and frontend quickstart notes. Please update any references or links to point to canonical locations:

## Status: ✅ ALL COMPLETE

### What Was Done Today (December 1, 2025)

|------|--------|---------------|
| 1. API Keys Setup | ✅ Complete | `.env.production` |
| 2. Real Task Execution | ✅ Complete | `services/goblin_executor.py` |
| 3. WebAuthn Passkeys | ✅ Complete | `auth/PRODUCTION_READINESS.md` |
| 4. Raptor Integration | ✅ Complete | `raptor_router.py` |
| 5. PostgreSQL Migration | ✅ Complete | `POSTGRESQL_MIGRATION.md` |

---

## 🚀 Deploy in 3 Steps

### 1. Database Setup (5 min)

```bash
# Go to Supabase Dashboard
# Copy PostgreSQL connection string
# Add to .env.production:
DATABASE_URL=postgresql://postgres.dhxoowakvmobjxsffpst:[PASSWORD]@...

# Run migrations
cd apps/goblin-assistant/backend
source venv/bin/activate
alembic upgrade head
```

### 2. Redis Setup (5 min)

```bash

# Sign up at upstash.com

# Create Redis database

# Add to .env.production:
USE_REDIS_CHALLENGES=true
REDIS_HOST=your-host.upstash.io
REDIS_PASSWORD=your-password
REDIS_SSL=true
```

### 3. Deploy (20 min)

```bash
# Backend
cd apps/goblin-assistant
./deploy-backend.sh render  # or fly

# Frontend
./deploy-vercel.sh

# Update FRONTEND_URL in backend env vars
FRONTEND_URL=https://your-production-domain.com

## 🎯 Frontend Security (Production)

Before publishing the frontend:

- [ ] Ensure session tokens are stored in HttpOnly, Secure cookies instead of `localStorage`.
- [ ] Verify no `VITE_` env contains secrets — only public non-secret config belongs in `VITE_`.
- [ ] Authenticate SSE/EventSource using cookies or short-lived signed stream tokens — do not pass secrets in URLs.
- [ ] Add CSP (Content Security Policy) headers and sanitize model outputs if you render HTML from LLM responses.
- [ ] Verify CORS and allowed origins match the production frontend domain.

```

---

## 📋 Pre-Flight Checklist

Before deploying, verify:

- [ ] `.env.production` has all API keys
- [ ] PostgreSQL connection string updated
- [ ] Redis configured (USE_REDIS_CHALLENGES=true)
- [ ] FRONTEND_URL set to production domain
- [ ] ALLOWED_ORIGINS updated for CORS
- [ ] All dependencies installed (`pip install -r requirements.txt`)

---

## 🧪 Test Production

```bash

# Health check
curl <https://your-backend/health>

# Database
curl <https://your-backend/api/health/db>

# Test task execution
curl -X POST <https://your-backend/execute> \
  -H "Content-Type: application/json" \
  -d '{"goblin": "test-goblin", "task": "test", "dry_run": true}'

# Raptor status
curl <https://your-backend/raptor/status>
```

---

## 🔥 If Something Breaks

### Database Connection Failed

```bash
# Check connection string format
DATABASE_URL=postgresql://user:pass@host:5432/database

# Test connection
python3 -c "from database import engine; engine.connect()"
```

### Redis Connection Failed

```bash

# Verify Redis config
redis-cli -h <host> -p 6379 -a <password> PING

# Should return: PONG
```

### Task Execution Failed

```bash
# Check GoblinOS path
ls -la /Users/fuaadabdullah/ForgeMonorepo/GoblinOS/goblin-cli.sh

# Test goblin-cli
bash GoblinOS/goblin-cli.sh list
```

### Migration Failed

```bash

# Check current version
alembic current

# Reset and retry
alembic downgrade base
alembic upgrade head
```

---

## 📞 Quick Links

- **Supabase Dashboard**: <https://supabase.com/dashboard>
- **Upstash Console**: <https://console.upstash.com>
- **Render Dashboard**: <https://dashboard.render.com>
- **Vercel Dashboard**: <https://vercel.com/dashboard>

---

## 📚 Full Documentation

| Topic                | File                                |
| -------------------- | ----------------------------------- |
| Complete Summary     | `PRODUCTION_DEPLOYMENT_COMPLETE.md` |
| PostgreSQL Migration | `POSTGRESQL_MIGRATION.md`           |
| WebAuthn Production  | `auth/PRODUCTION_READINESS.md`      |
| Original Deployment  | `PRODUCTION_DEPLOYMENT.md`          |

---

**🎯 You're Ready!** Everything is implemented and tested. Just need to:

1. Set up external services (PostgreSQL, Redis)
2. Deploy to hosting
3. Test production endpoints

**Estimated Total Time**: 30-60 minutes
