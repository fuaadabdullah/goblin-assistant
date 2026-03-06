# Privacy Implementation - Quickstart

## 5-Minute Setup Guide

### Step 1: Test Current Implementation (30 seconds)

```bash
cd apps/goblin-assistant/api
python3 scripts/validate_privacy_integration.py
```

**Expected**: ✅ All core tests pass

---

### Step 2: Configure Environment (1 minute)

```bash
# Copy example config
cp .env.privacy.example .env.local

# Edit required values
# - REDIS_URL=redis://localhost:6379
# - DATADOG_API_KEY=your_key_here
# - SUPABASE_URL=your_supabase_url
# - SUPABASE_ANON_KEY=your_anon_key
```

---

### Step 3: Deploy Database Migration (1 minute)

```bash
cd apps/goblin-assistant/api
supabase db push

# Verify RLS
scripts/ops/supabase_rls_check.sh
```

---

### Step 4: Test Locally (2 minutes)

```bash
# Start backend
cd apps/goblin-assistant/api
uvicorn main:app --reload --port 8000

# In another terminal, test sanitization
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "My email is test@example.com"}'

# Should see [REDACTED]_EMAIL in response
```

---

### Step 5: Deploy to Production (1 minute)

```bash
cd apps/goblin-assistant
fly deploy

# Verify
curl https://goblin-assistant-backend.onrender.com/health
```

---

## 🎉 Done! Privacy Features Active

### What Just Happened?

- ✅ PII detection active (email, phone, keys, etc.)
- ✅ Rate limiting enabled (100/min, 1000/hour)
- ✅ GDPR endpoints available (/api/privacy/export, /api/privacy/delete)
- ✅ Database RLS protecting user data
- ✅ Telemetry redacting sensitive data

### Test Your Privacy Endpoints

```bash
# Export user data (GDPR Article 20)
curl -X GET https://goblin-assistant-backend.onrender.com/api/privacy/export \
  -H "Authorization: Bearer <your_token>"

# Delete user data (GDPR Article 17)
curl -X DELETE https://goblin-assistant-backend.onrender.com/api/privacy/delete \
  -H "Authorization: Bearer <your_token>"
```

---

## 📚 Full Documentation

- **Executive Summary**: `PRIVACY_EXECUTIVE_SUMMARY.md`
- **Complete Features**: `PRIVACY_IMPLEMENTATION_SUCCESS.md`
- **Technical Guide**: `docs/PRIVACY_IMPLEMENTATION.md`
- **Integration Steps**: `docs/PRIVACY_INTEGRATION_GUIDE.md`

---

## 🆘 Troubleshooting

### "Import Error: services.sanitization"
```bash
cd apps/goblin-assistant/api
python3 -c "from services.sanitization import sanitize_input_for_model; print('✅ OK')"
```

### "Redis Connection Failed"
```bash
# macOS
brew services start redis

# Linux
sudo systemctl start redis

# Test
redis-cli ping  # Should return: PONG
```

### "Privacy Router Not Found"
```bash
cd apps/goblin-assistant/api
python3 -c "from routes.privacy import router; print('✅ OK')"
```

---

*Setup time: ~5 minutes*
*Ready for production deployment*
