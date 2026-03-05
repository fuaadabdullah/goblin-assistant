# Fly.io Troubleshooting Guide for Goblin Assistant Backend

This guide helps you diagnose and fix the "Machines Restarting a Lot" issue and other Fly.io deployment problems.

## 🚨 Immediate Actions for Machine Restarts

### 1. Check Logs for Startup Errors
```bash
# Check recent logs for your application
flyctl logs -a goblin-assistant

# Look specifically for startup errors
flyctl logs -a goblin-assistant | grep -i "error\|exception\|critical"
```

### 2. Check Machine Status
```bash
# List all machines
flyctl machines list -a goblin-assistant

# Check specific machine details
flyctl machine status <machine-id> -a goblin-assistant
```

### 3. Check Health Checks
```bash
# Test health endpoints
curl https://goblin-assistant.fly.dev/health
curl https://goblin-assistant.fly.dev/health/live
curl https://goblin-assistant.fly.dev/health/ready
```

## 🔍 Common Causes and Solutions

### 1. Missing Environment Variables (Most Common)
**Symptoms**: Application crashes on startup, unable to connect to database/Redis
**Solution**: Set required environment variables

```bash
# Set basic configuration
flyctl secrets set DEBUG=false ENVIRONMENT=production RELEASE_VERSION=1.0.0

# Set database URL (replace with your actual database)
flyctl secrets set DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db

# Set Redis URL (replace with your actual Redis)
flyctl secrets set REDIS_URL=redis://user:pass@host:6379/0

# Set secrets management (replace with your Vault config)
flyctl secrets set VAULT_URL=https://your-vault-server:8200 VAULT_TOKEN=your-token

# Set Supabase configuration
flyctl secrets set NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
flyctl secrets set NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
flyctl secrets set SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

### 2. Database Connection Issues
**Symptoms**: Application starts but crashes when trying to connect to database
**Solutions**:
- Verify your database URL is correct
- Check if your database allows connections from Fly.io
- Ensure database credentials are valid
- Check database connection limits

### 3. Redis Connection Issues
**Symptoms**: Application starts but caching doesn't work, potential timeouts
**Solutions**:
- Verify Redis URL format: `redis://username:password@hostname:port/database`
- Check if Redis allows connections from Fly.io
- Ensure Redis credentials are valid

### 4. Memory Issues
**Symptoms**: Application crashes with memory errors, restarts under load
**Solutions**:
```bash
# Check memory usage
flyctl status -a goblin-assistant

# Increase memory if needed (edit fly.toml)
# [[vm]]
#   memory = "2048mb"  # Increase from 1024mb
```

### 5. Health Check Failures
**Symptoms**: Fly.io marks machine as unhealthy and restarts it
**Solutions**:
- Ensure `/health/live` returns 200
- Ensure `/health/ready` returns 200 when app is ready
- Check health check configuration in `fly.toml`

## 📊 Monitoring and Debugging

### 1. Application Monitoring
```bash
# View real-time logs
flyctl logs -a goblin-assistant -f

# Check machine metrics
flyctl vm status <machine-id> -a goblin-assistant

# Check app status
flyctl status -a goblin-assistant
```

### 2. Sentry Error Tracking
The application is configured with Sentry for error monitoring:
- **Dashboard**: https://sentry.io (login with your credentials)
- **Environment**: production
- **Project**: goblin-assistant

### 3. Health Check Endpoints
Monitor these endpoints:
- `/health` - Full health check
- `/health/live` - Liveness probe (should always return 200)
- `/health/ready` - Readiness probe (returns 200 when ready to serve traffic)
- `/health/all` - Detailed health check for all subsystems

### 4. Performance Monitoring
```bash
# Check response times
curl -w "@curl-format.txt" -o /dev/null -s https://goblin-assistant.fly.dev/health

# Check for memory leaks
flyctl vm status <machine-id> -a goblin-assistant --metrics
```

## 🔧 Configuration Files

### Environment Variables (.env.production)
Copy `api/.env.production` and set your actual values:
```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db

# Redis
REDIS_URL=redis://user:pass@host:6379/0

# Vault
VAULT_URL=https://your-vault-server:8200
VAULT_TOKEN=your-vault-token

# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# AI Providers (optional)
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
```

### Fly.io Configuration (fly.toml)
Key settings for stability:
```toml
[http_service]
  internal_port = 8001
  force_https = true
  auto_start_machines = true
  auto_stop_machines = true
  min_machines_running = 1

  [[http_service.checks]]
    interval = 10000
    timeout = 2000
    grace_period = 5000
    method = "GET"
    path = "/health/live"
    protocol = "http"
    retries = 3
```

## 🚀 Deployment Checklist

### Before Deployment
- [ ] Set all required environment variables as Fly.io secrets
- [ ] Verify database and Redis are accessible from Fly.io
- [ ] Configure Sentry project and set DSN
- [ ] Set up custom domains (if needed)
- [ ] Configure SSL certificates

### During Deployment
```bash
# Deploy with monitoring
flyctl deploy --verbose

# Check deployment status
flyctl status -a goblin-assistant

# Monitor logs during deployment
flyctl logs -a goblin-assistant -f
```

### After Deployment
- [ ] Verify health endpoints return 200
- [ ] Check application logs for errors
- [ ] Monitor memory and CPU usage
- [ ] Test API endpoints
- [ ] Verify Sentry is receiving events

## 🆘 Emergency Procedures

### 1. Application Won't Start
```bash
# Check recent deployments
flyctl releases -a goblin-assistant

# Rollback to previous version
flyctl releases rollback <release-id> -a goblin-assistant
```

### 2. High Restart Rate
```bash
# Scale to multiple machines
flyctl scale count 2 -a goblin-assistant

# Increase memory
flyctl scale memory 2048 -a goblin-assistant

# Check for resource exhaustion
flyctl vm status <machine-id> -a goblin-assistant --metrics
```

### 3. Database Connection Issues
```bash
# Check database connections
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity;"

# Restart database if needed
# (Contact your database provider)
```

### 4. Redis Connection Issues
```bash
# Test Redis connection
redis-cli -u $REDIS_URL ping

# Check Redis memory usage
redis-cli -u $REDIS_URL info memory
```

## 📞 Support Contacts

### Internal Support
- **DevOps Team**: [devops@yourcompany.com](mailto:devops@yourcompany.com)
- **Backend Team**: [backend@yourcompany.com](mailto:backend@yourcompany.com)

### External Support
- **Fly.io Support**: https://fly.io/docs/support/
- **Sentry Support**: https://sentry.io/support/
- **Database Provider Support**: [Contact your provider]

### Emergency Escalation
1. Check Sentry for error patterns
2. Review Fly.io logs for system-level issues
3. Contact Fly.io support for infrastructure issues
4. Escalate to on-call engineer if needed

## 📝 Additional Resources

- [Fly.io Documentation](https://fly.io/docs/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Sentry Documentation](https://docs.sentry.io/)
- [PostgreSQL Connection Guide](https://wiki.postgresql.org/wiki/First_steps)
- [Redis Configuration Guide](https://redis.io/topics/config)

---

**Remember**: Always test changes in a staging environment before deploying to production!
