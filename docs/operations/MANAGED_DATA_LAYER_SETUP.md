# Managed Data Layer Setup

This document describes how to set up the managed data layer (Supabase + Upstash Redis) for goblin-assistant on a Mac mini.

## Status Overview

| Component | Status | Notes |
|-----------|--------|-------|
| Supabase Project | ✅ Created | Project: `dhxoowakvmobjxsffpst.supabase.co` |
| pgvector Extension | ✅ Applied | Migration `20260601` marked as applied |
| Upstash Redis | ⚠️ Manual Setup Required | See instructions below |

## Supabase Configuration

### Already Configured
- **Project URL:** `https://dhxoowakvmobjxsffpst.supabase.co`
- **API Keys:** Already in `.env` (SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY)

### Database Connection
The `DATABASE_URL` in `.env` uses the service role key as the password, which works with Supabase's connection string format:

```
postgresql+asyncpg://postgres:{SUPABASE_SERVICE_ROLE_KEY}@db.{PROJECT_REF}.supabase.co:5432/postgres
```

This is handled automatically by `apps/api/src/api/supabase_integration.py` when `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are set.

### pgvector Extension
- The migration `supabase/migrations/20260601_activate_pgvector.sql` has been applied
- This enables vector similarity search for embeddings

## Upstash Redis Setup (Required)

### Step-by-Step Instructions

1. **Create Upstash Account**
   - Go to https://console.upstash.com
   - Sign up or log in with your preferred provider (GitHub, Google, etc.)

2. **Create Redis Database**
   - Click "Create Database"
   - Select:
     - **Type:** Redis
     - **Region:** Choose closest to your deployment (e.g., US East for Vercel)
     - **Plan:** Free tier (up to 10K requests/day, 256MB storage)
   - Click "Create"

3. **Get Connection String**
   - In your database settings page, find the "REST" section
   - Copy the connection string that starts with `redis://`

4. **Update .env**
   Add your Redis URL to `.env`:
   ```bash
   REDIS_URL=redis://default:<your-password>@<your-cluster>.upstash.io:6379
   ```

### Alternative: Render Internal Redis

If you prefer not to use Upstash, the existing Render Redis instance can be used:
- **Connection:** `redis://red-d8h6p242m8qs73aon26g:6379`
- This requires the Render deployment to be active

## Verification

### Test Supabase Connection
```bash
# Run the Supabase connectivity check
SUPABASE_URL=https://dhxoowakvmobjxsffpst.supabase.co \
SUPABASE_ANON_KEY=sb_publishable_mLCx0Q79lcDq85xnJJztOw_mktNxZ6R \
npx tsx scripts/check-supabase.ts
```

### Test Database Connection
```bash
# Test with the backend server
cd apps/api
DATABASE_URL="postgresql+asyncpg://postgres:${SUPABASE_PASSWORD}@db.dhxoowakvmobjxsffpst.supabase.co:5432/postgres" \
python3 -c "
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def test():
    engine = create_async_engine('postgresql+asyncpg://postgres:${SUPABASE_PASSWORD}@db.dhxoowakvmobjxsffpst.supabase.co:5432/postgres')
    async with engine.connect() as conn:
        result = await conn.execute(text('SELECT version()'))
        print('PostgreSQL version:', result.scalar())
        await engine.dispose()

asyncio.run(test())
"
```

### Test Redis Connection
```bash
# If using Upstash Redis
redis-cli -h <your-cluster>.upstash.io -p 6379 ping

# Should return: PONG
```

## Environment Variables Summary

| Variable | Value | Description |
|----------|-------|-------------|
| DATABASE_URL | `postgresql+asyncpg://...` | Supabase Postgres connection |
| REDIS_URL | `redis://...` | Upstash Redis connection |
| SUPABASE_URL | `https://dhxoowakvmobjxsffpst.supabase.co` | Supabase project URL |
| SUPABASE_SERVICE_ROLE_KEY | `sb_secret_...` | Service role key for DB writes |
| SUPABASE_ANON_KEY | `sb_publishable_...` | Public anon key for client |

## Notes

- The Mac mini should use these managed services instead of local Docker containers for lighter resource usage
- All API keys and secrets are stored in `.env` (never commit to git)
- For production, consider using Bitwarden CLI integration via `scripts/setup-supabase-from-bw.sh`
- See [Phase Gates](./PHASE_GATES.md) for the recommended baseline sequence that starts with Supabase + Upstash.
