# Fly.io Deployment Guide for Goblin Assistant Backend

This guide will help you successfully deploy the Goblin Assistant backend to Fly.io and resolve the "Machines Restarting a Lot" issue.

## 🚨 Critical Issues Fixed

### 1. **Missing Dependencies** ✅
- **Problem**: `structlog` module missing causing immediate crashes
- **Solution**: Merged API requirements.txt with main requirements.txt
- **Result**: All dependencies now available during Docker build

### 2. **Missing Environment Variables** ✅
- **Problem**: No DATABASE_URL, REDIS_URL, or other critical environment variables
- **Solution**: Created comprehensive secret setup script
- **Result**: All required configuration can be set as Fly.io secrets

### 3. **Application Resilience** ✅
- **Problem**: App crashed on first missing dependency or database failure
- **Solution**: Enhanced startup sequence with graceful error handling
- **Result**: App continues running even if non-critical services fail

## 📋 Pre-Deployment Checklist

### Required Services (Choose One Option)

#### Option A: Managed Services (Recommended)
- **PostgreSQL Database**: Supabase, Neon, AWS RDS, or similar
- **Redis Instance**: Redis Cloud, Upstash, AWS ElastiCache, or similar

#### Option B: Local Development
- **PostgreSQL**: Can use SQLite fallback (limited functionality)
- **Redis**: Can be disabled (caching won't work)

### Environment Variables Required

#### Critical (Must Set)
```bash
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
REDIS_URL=redis://user:pass@host:6379/0
```

#### Optional (Recommended)
```bash
VAULT_TOKEN=your-vault-token
NEXT_PUBLIC_SUPABASE_URL=your-supabase-url
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
```

## 🚀 Deployment Steps

### Step 1: Set Up Fly.io App
```bash
# Install flyctl if not already installed
curl -L https://fly.io/install.sh | sh

# Login to Fly.io
flyctl auth login

# Create the app (if not already created)
flyctl apps create goblin-backend
```

### Step 2: Configure Secrets
```bash
# Run the automated secret setup script
cd /Users/fuaadabdullah/ForgeMonorepo/apps/goblin-assistant
./set-fly-secrets.sh

# Or set secrets manually:
flyctl secrets set \
    DEBUG=false \
    ENVIRONMENT=production \
    DATABASE_URL=your_postgres_url \
    REDIS_URL=your_redis_url \
    ALLOWED_ORIGINS=https://your-domain.com
```

### Step 3: Deploy
```bash
# Navigate to the app directory
cd /Users/fuaadabdullah/ForgeMonorepo/apps/goblin-assistant

# Deploy with monitoring
flyctl deploy --verbose

# Monitor the deployment
flyctl logs -a goblin-backend -f
```

### Step 4: Verify Deployment
```bash
# Check machine status
flyctl status -a goblin-backend

# Test health endpoints
curl https://goblin-backend.fly.dev/health
curl https://goblin-backend.fly.dev/health/live
curl https://goblin-backend.fly.dev/health/ready

# Check logs for any errors
flyctl logs -a goblin-backend
```

## 🔧 Configuration Options

### Database Configuration

#### Supabase (Recommended)
1. Create project at [supabase.com](https://supabase.com)
2. Create database and get connection string
3. Set secret:
```bash
flyctl secrets set DATABASE_URL="postgresql+asyncpg://postgres:your_password@db.your_project.supabase.co:5432/postgres"
```

#### Neon (Recommended)
1. Create project at [neon.tech](https://neon.tech)
2. Create branch and get connection string
3. Set secret:
```bash
flyctl secrets set DATABASE_URL="postgresql+asyncpg://user:pass@ep-xxx.us-east-1.aws.neon.tech/neondb"
```

### Redis Configuration

#### Upstash (Recommended)
1. Create project at [upstash.com](https://upstash.com)
2. Get Redis connection string
3. Set secret:
```bash
flyctl secrets set REDIS_URL="redis://default:your_token@redis-12345.upstash.io:6379"
```

#### Redis Cloud
1. Create project at [redis.com](https://redis.com)
2. Get connection string
3. Set secret:
```bash
flyctl secrets set REDIS_URL="redis://username:password@redis-12345.c123.us-east-1-4.ec2.cloud.redislabs.com:12345"
```

## 🆘 Troubleshooting

### Machine Restarts After Deployment
**Symptoms**: Machines keep restarting, deployment fails
**Causes**:
1. Missing DATABASE_URL or REDIS_URL
2. Invalid database/Redis connection strings
3. Missing dependencies (should be fixed now)

**Solutions**:
```bash
# Check logs for specific errors
flyctl logs -a goblin-backend

# Verify secrets are set
flyctl secrets list -a goblin-backend

# Test database connection manually
psql $DATABASE_URL

# Check machine status
flyctl machines list -a goblin-backend
```

### Database Connection Errors
**Error**: `Tenant or user not found`
**Solution**: Verify your DATABASE_URL is correct and database is accessible from Fly.io

**Error**: `Connection refused`
**Solution**: Check if your database allows connections from Fly.io IP ranges

### Redis Connection Errors
**Error**: `Error 111 connecting to localhost:6379`
**Solution**: Set REDIS_URL secret with your Redis instance URL

### Dependency Errors
**Error**: `ModuleNotFoundError: No module named 'structlog'`
**Solution**: Rebuild with updated requirements.txt (should be fixed)

## 📊 Monitoring and Health Checks

### Health Endpoints
- `/health` - Full system health check
- `/health/live` - Liveness probe (should always return 200)
- `/health/ready` - Readiness probe (returns 200 when ready to serve traffic)
- `/health/all` - Detailed health check for all subsystems

### Sentry Error Tracking
The application is configured with Sentry for error monitoring:
- **Dashboard**: https://sentry.io
- **Environment**: production
- **Project**: goblin-assistant

### Logs and Metrics
```bash
# View real-time logs
flyctl logs -a goblin-backend -f

# Check machine metrics
flyctl vm status <machine-id> -a goblin-backend

# Check app status
flyctl status -a goblin-backend
```

## 🎯 Post-Deployment Verification

### 1. Health Check Verification
```bash
# All should return 200 OK
curl -I https://goblin-backend.fly.dev/health
curl -I https://goblin-backend.fly.dev/health/live
curl -I https://goblin-backend.fly.dev/health/ready
```

### 2. Application Functionality
```bash
# Test API endpoints
curl https://goblin-backend.fly.dev/docs  # Should show API docs
curl https://goblin-backend.fly.dev/      # Should show root endpoint
```

### 3. Machine Stability
```bash
# Check machine uptime
flyctl status -a goblin-backend

# Verify no restart loops
flyctl machines list -a goblin-backend
```

## 🔄 Rollback Plan

If deployment fails:
```bash
# List releases
flyctl releases -a goblin-backend

# Rollback to previous version
flyctl releases rollback <release-id> -a goblin-backend
```

## 📞 Support

### Emergency Contacts
- **DevOps Team**: [devops@yourcompany.com](mailto:devops@yourcompany.com)
- **Backend Team**: [backend@yourcompany.com](mailto:backend@yourcompany.com)

### External Support
- **Fly.io Support**: https://fly.io/docs/support/
- **Sentry Support**: https://sentry.io/support/

### Emergency Escalation
1. Check Sentry for error patterns
2. Review Fly.io logs for system-level issues
3. Contact Fly.io support for infrastructure issues
4. Escalate to on-call engineer if needed

---

**✅ With these fixes, your application should now deploy successfully without the "Machines Restarting a Lot" issue. The enhanced error handling and proper dependency management will ensure stable operation.**
