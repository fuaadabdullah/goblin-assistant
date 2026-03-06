# Deployment

## Deployment Overview

GoblinOS Assistant supports multiple deployment strategies optimized for different environments and use cases. The system is designed for easy deployment to cloud platforms while maintaining development workflow efficiency.

## Production Deployment

### Fly.io Backend Deployment

The backend API is deployed to Fly.io for global distribution and automatic scaling.

#### Prerequisites

- Fly.io account and CLI installed
- Docker for container builds
- Environment secrets configured

#### Backend Deployment Steps

1. **Install Fly.io CLI**:

   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. **Authenticate and setup**:

   ```bash
   fly auth login
   fly launch --name goblin-assistant-backend
   ```

3. **Configure secrets**:

   ```bash
   # Set production secrets
   fly secrets set DATABASE_URL="postgresql://..."
   fly secrets set JWT_SECRET_KEY="$(openssl rand -hex 32)"
   fly secrets set OPENAI_API_KEY="sk-..."
   fly secrets set ANTHROPIC_API_KEY="sk-ant-..."
   ```

4. **Deploy**:

   ```bash
   fly deploy
   ```

5. **Scale globally**:

   ```bash
   fly regions add iad ord
   fly scale count 3
   ```

#### Production Configuration

- **Regions**: Deployed to multiple regions for low latency
- **Scaling**: Automatic scaling based on CPU/memory usage
- **Health Checks**: Built-in health monitoring and auto-healing
- **Logs**: Centralized logging with `fly logs`

### Vercel Frontend Deployment

The Next.js frontend is deployed to Vercel for optimal performance and CDN distribution.

#### Frontend Deployment Steps

1. **Connect repository**:

   ```bash
   # Vercel will auto-detect Next.js
   vercel --prod
   ```

2. **Configure environment variables**:

   ```bash
   vercel env add VITE_API_BASE_URL
   vercel env add VITE_SENTRY_DSN
   ```

3. **Deploy**:

   ```bash
   vercel --prod
   ```

#### Vercel Optimizations

- **Edge Functions**: API routes deployed at edge locations
- **Image Optimization**: Automatic image compression and WebP conversion
- **Incremental Static Regeneration**: Dynamic content caching
- **Analytics**: Built-in performance monitoring

### Cloudflare Infrastructure

#### Workers & Edge Computing

```javascript
// Example Cloudflare Worker for API routing
export default {
  async fetch(request, env) {
    // Intelligent routing logic
    const response = await fetch('https://goblin-assistant-backend.onrender.com', request);
    return response;
  }
};
```

#### KV Storage Setup

```bash
# Create KV namespace
npx wrangler kv:namespace create "GOBLIN_SESSIONS"

# Bind to Worker
wrangler.toml:
kv_namespaces = [
  { binding = "SESSIONS", id = "9e1c27d3eda84c759383cb2ac0b15e4c" }
]
```

#### D1 Database

```sql
-- Create tables in D1
CREATE TABLE user_preferences (
  user_id TEXT PRIMARY KEY,
  preferences TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### R2 Object Storage

```bash
# Setup R2 buckets
npx wrangler r2 bucket create goblin-audio
npx wrangler r2 bucket create goblin-logs
npx wrangler r2 bucket create goblin-uploads
```

## Development Deployment

### Local Development Setup

#### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///./goblin_assistant.db
    volumes:
      - ./backend:/app

  frontend:
    build: ./app
    ports:
      - "3000:3000"
    environment:
      - VITE_API_BASE_URL=http://localhost:8000
```

#### Local Deployment

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Development Tools

#### Hot Reload Setup

```bash
# Backend hot reload
cd backend
uvicorn main:app --reload --host 0.0.0.0

# Frontend hot reload
cd app
npm run dev
```

#### Database Migrations

```bash
# Development database
alembic upgrade head

# Reset development database
rm goblin_assistant.db
alembic upgrade head
```

## Infrastructure as Code

### Terraform Configuration

```hcl
# main.tf
terraform {
  required_providers {
    fly = {
      source = "fly-apps/fly"
    }
    vercel = {
      source = "vercel/vercel"
    }
  }
}

# Fly.io app
resource "fly_app" "goblin_assistant" {
  name = "goblin-assistant"
  org  = "goblin-os"
}

# Vercel project
resource "vercel_project" "goblin_assistant_frontend" {
  name = "goblin-assistant"
  framework = "nextjs"
}
```

### Cloudflare Configuration

```toml
# wrangler.toml
name = "goblin-assistant-edge"
main = "src/index.js"
compatibility_date = "2024-01-01"

[vars]
ENVIRONMENT = "production"

[[kv_namespaces]]
binding = "SESSIONS"
id = "9e1c27d3eda84c759383cb2ac0b15e4c"

[[d1_databases]]
binding = "DB"
database_name = "goblin-assistant-db"
database_id = "goblin-assistant-db"

[[r2_buckets]]
binding = "AUDIO"
bucket_name = "goblin-audio"
```

## Monitoring & Observability

### Health Checks

#### Application Health

```bash
# Check backend health
curl https://goblin-assistant-backend.onrender.com/health

# Check frontend health
curl https://goblin-assistant.vercel.app/api/health
```

#### Infrastructure Health

```bash
# Fly.io app status
fly status

# Vercel deployment status
vercel ls

# Cloudflare Worker status
npx wrangler tail
```

### Logging

#### Centralized Logging

```bash
# Fly.io logs
fly logs

# Vercel logs
vercel logs

# Cloudflare logs
npx wrangler tail --format=pretty
```

#### Log Aggregation

```yaml
# docker-compose.logging.yml
version: '3.8'
services:
  logstash:
    image: docker.elastic.co/logstash/logstash:8.5.0
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf
```

### Metrics & Monitoring

#### Application Metrics

- **Response Times**: P50, P95, P99 latency tracking
- **Error Rates**: 4xx/5xx error monitoring
- **Throughput**: Requests per second
- **Resource Usage**: CPU, memory, disk I/O

#### Infrastructure Metrics

- **Uptime**: Service availability monitoring
- **Scaling Events**: Auto-scaling triggers
- **Cost Tracking**: API usage and infrastructure costs

## Security Hardening

### Production Security Checklist

- [ ] **Secrets Management**: All secrets in dedicated vaults
- [ ] **Network Security**: VPC isolation and security groups
- [ ] **Access Control**: Least privilege IAM roles
- [ ] **Encryption**: TLS 1.3 and data encryption at rest
- [ ] **Monitoring**: Security event logging and alerting
- [ ] **Updates**: Regular dependency and infrastructure updates

### SSL/TLS Configuration

```nginx
# Example nginx configuration
server {
    listen 443 ssl http2;
    server_name api.goblin-assistant.vercel.app;

    ssl_certificate /etc/ssl/certs/goblin-assistant.vercel.app.crt;
    ssl_certificate_key /etc/ssl/private/goblin-assistant.vercel.app.key;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
}
```

## Backup & Recovery

### Database Backups

```bash
# PostgreSQL backup
pg_dump goblin_assistant > backup_$(date +%Y%m%d).sql

# Restore from backup
psql goblin_assistant < backup_20241201.sql
```

### Application Backups

```bash
# Configuration backup
tar -czf config_backup.tar.gz .env* wrangler.toml fly.toml

# Restore configuration
tar -xzf config_backup.tar.gz
```

### Disaster Recovery

1. **Data Recovery**: Restore from latest database backup
2. **Application Recovery**: Redeploy from last stable commit
3. **Infrastructure Recovery**: Use Terraform to recreate resources
4. **Testing**: Validate recovery procedures regularly

## Cost Optimization

### Cloud Cost Management

#### Fly.io Costs

- **App Hours**: ~$0.02/hour for basic instances
- **Bandwidth**: First 100GB free, then $0.02/GB
- **Persistent Storage**: $0.15/GB/month

#### Vercel Costs

- **Hobby Plan**: $0/month (perfect for development)
- **Pro Plan**: $20/month for production features
- **Enterprise**: Custom pricing for large scale

#### Cloudflare Costs

- **Workers**: First 100,000 requests free, then $0.15/million
- **KV Storage**: $0.50/GB/month
- **D1 Database**: $0.001/GB/row read
- **R2 Storage**: $0.015/GB/month

### Optimization Strategies

1. **Caching**: Implement aggressive caching to reduce API calls
2. **Compression**: Enable gzip/brotli compression
3. **CDN**: Use Cloudflare for static asset delivery
4. **Scaling**: Auto-scale based on actual usage patterns
5. **Monitoring**: Track costs and optimize resource usage

## Troubleshooting Deployment

### Common Issues

#### Fly.io Deployment Failures

```bash
# Check deployment status
fly status

# View deployment logs
fly logs --instance <instance-id>

# Restart failed instance
fly restart <instance-id>
```

#### Vercel Build Failures

```bash
# Check build logs
vercel logs --follow

# Clear build cache
vercel rm --yes
```

#### Cloudflare Issues

```bash
# Check Worker status
npx wrangler tail

# Deploy Worker
npx wrangler deploy
```

### Performance Issues

#### Slow Response Times

1. Check database query performance
2. Verify caching is working
3. Monitor resource utilization
4. Scale instances if needed

#### High Error Rates

1. Review application logs
2. Check health endpoints
3. Monitor external service dependencies
4. Implement circuit breakers

### Rollback Procedures

#### Emergency Rollback

```bash
# Fly.io rollback
fly releases
fly rollback <release-version>

# Vercel rollback
vercel rollback

# Git rollback
git reset --hard HEAD~1
git push --force
```

This deployment guide ensures reliable, scalable, and cost-effective operation of GoblinOS Assistant across all environments.
