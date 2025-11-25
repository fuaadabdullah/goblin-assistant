# 🚀 Goblin Assistant - Production Deployment Guide

## Overview

Complete production deployment guide for the Goblin Assistant MCP service with comprehensive Datadog monitoring, ChromaDB integration, and enterprise security features.

## 📋 Prerequisites

- Docker & Docker Compose
- Datadog account with API access
- Domain name (optional, for production)
- SSL certificate (Let's Encrypt recommended)
- PostgreSQL database (managed or self-hosted)

## ⚡ Quick Deploy

### 1. Clone & Setup

```bash
git clone <repository>
cd goblin-assistant
cp .env.example .env
```

### 2. Configure Environment

Edit `.env` with your credentials:

```bash
# Datadog Configuration
DD_API_KEY=your_datadog_api_key_here
DD_APP_KEY=your_datadog_app_key_here
DD_SITE=datadoghq.com
ENV=production

# Database
POSTGRES_PASSWORD=your_secure_postgres_password
DATABASE_URL=postgresql://goblin:${POSTGRES_PASSWORD}@postgres:5432/mcp_db

# ChromaDB (Vector Database)
CHROMA_HOST=localhost
CHROMA_PORT=8000

# Add your AI provider API keys...
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Deploy Services

```bash
# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f goblin-assistant
```

### 4. Setup Monitoring

```bash
# Run Datadog setup script
chmod +x setup-datadog.sh
./setup-datadog.sh
```

## 🛡️ Security Configuration

### Secret Scanning Setup

The system includes comprehensive secret scanning at multiple layers:

1. **Request Validation**: Scans user prompts before processing
2. **Worker Safety**: Double-checks before sending to providers
3. **Document Indexing**: Automatic redaction in ChromaDB

### Security Monitoring

Security events are automatically tracked:

- **Detection Points**: `request_creation`, `worker_processing`, `document_indexing`
- **Metrics**: `goblin.security.secrets_detected` with tags for detection location
- **Audit Logs**: Complete security event trail in database

### Privacy Features

- User IDs are hashed for privacy
- API keys stored securely in system keychain
- Data minimization and retention policies

## 📊 KPI Monitoring Dashboard

After deployment, access these endpoints:

- **Admin Dashboard**: `http://localhost/mcp/v1/admin/dashboard`
- **Datadog Dashboard**: Created automatically via setup script
- **Health Check**: `http://localhost/api/health`

### Monitored KPIs

| KPI | Target | Critical Alert | Warning Alert |
|-----|--------|----------------|---------------|
| P95 Latency | < 1.5s | > 1.5s | > 1.0s |
| Error Rate | < 3% | > 3% | > 1% |
| RAG Hit Rate | > 60% | < 60% | < 70% |
| Fallback Rate | < 5% | > 5% | > 2% |
| Queue Depth | < 50 | > 50 | > 25 |
| Daily Cost | < $50 | > $50 | > $25 |
| Security Violations | < 1/day | > 1/day | > 0/day |
| Secret Detection Rate | Monitor | N/A | N/A |

## 🔧 Configuration Files

### Docker Services

- **goblin-assistant**: Main FastAPI application
- **datadog**: Metrics collection and forwarding
- **postgres**: Database (persistent data)
- **redis**: Queue and caching (ephemeral)

### Environment Variables

**Required:**

- `DD_API_KEY`: Datadog API key
- `DD_APP_KEY`: Datadog application key
- `POSTGRES_PASSWORD`: Database password

**Optional:**

- `DD_SITE`: Datadog site (default: datadoghq.com)
- `ENV`: Environment tag (default: production)
- `DD_VERSION`: Version tag for deployments

## 📈 Monitoring & Alerts

### Automated Monitors Created

1. **Latency Monitor**: P95 response time alerts
2. **Error Rate Monitor**: Application error percentage
3. **RAG Hit Rate Monitor**: Context usage effectiveness
4. **Fallback Rate Monitor**: Provider reliability
5. **Queue Depth Monitor**: System capacity
6. **Cost Monitor**: Daily spending limits

### Dashboard Features

- Real-time KPI visualization
- Historical trend analysis
- Alert threshold indicators
- Provider performance metrics
- Cost tracking and budgeting

## 🔍 Troubleshooting

### Common Issues

**Services won't start:**

```bash
docker-compose logs
# Check for missing environment variables
```

**Metrics not appearing:**

```bash
docker-compose logs datadog
# Verify DD_API_KEY and network connectivity
```

**High latency alerts:**

- Check queue depth via admin dashboard
- Monitor provider response times
- Verify database performance

### Health Checks

```bash
# Check all services
docker-compose ps

# Check application health
curl http://localhost/api/health

# Check admin dashboard
curl http://localhost/mcp/v1/admin/dashboard
```

## 🚀 Scaling & Performance

### Horizontal Scaling

```bash
# Add more application instances
docker-compose up -d --scale goblin-assistant=3
```

### Database Optimization

- Monitor slow queries in PostgreSQL logs
- Consider read replicas for high traffic
- Enable connection pooling

### Caching Strategy

- Redis handles session and temporary data
- Consider Redis Cluster for high availability
- Monitor cache hit rates in Datadog

## 🔐 Security

### Production Checklist

- [ ] SSL/TLS enabled (nginx reverse proxy recommended)
- [ ] Database password rotated regularly
- [ ] API keys encrypted in environment
- [ ] Network segmentation implemented
- [ ] Regular security updates
- [ ] Audit logging enabled

### Backup Strategy

```bash
# Database backup
docker-compose exec postgres pg_dump -U goblin mcp > backup.sql

# Configuration backup
cp .env .env.backup
```

## 📚 Additional Resources

- [Datadog Monitoring Guide](./datadog/README.md)
- [API Documentation](./docs/API.md)
- [Troubleshooting Guide](./docs/troubleshooting.md)

## 🎯 Success Metrics

Your deployment is successful when:

- ✅ All services running without errors
- ✅ Datadog dashboard shows green metrics
- ✅ Admin dashboard loads with current KPIs
- ✅ No critical alerts in first 24 hours
- ✅ Response times within target thresholds

---

**Happy Deploying! 🚀**

*Last Updated: November 24, 2025*

## Manual Server Deployment

### 1. Server Setup
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install python3 python3-pip python3-venv -y

# Install nginx
sudo apt install nginx -y
```

### 2. Deploy Application
```bash
# Run deployment script
chmod +x deploy-production.sh
./deploy-production.sh
```

### 3. Configure Nginx (SSL)
```nginx
# /etc/nginx/sites-available/goblin-assistant
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 4. SSL Certificate (Let's Encrypt)
```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx -y

# Get certificate
sudo certbot --nginx -d your-domain.com
```

## Monitoring & Verification

### Check Datadog Dashboard
1. Go to https://app.datadoghq.com/dashboard/lists
2. Find "GoblinOS — Ops Dashboard"
3. Verify metrics are flowing:
   - API requests/second
   - Error rates
   - LLM costs
   - Infrastructure health

### Verify Monitors
1. Go to https://app.datadoghq.com/monitors/manage
2. Check these monitors are active:
   - Goblin API High Error Rate
   - Goblin Provider High Latency
   - Goblin Queue Depth Growing

### Test Application
```bash
# Health check
curl https://your-domain.com/health

# API test
curl -X POST https://your-domain.com/invoke \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Test", "provider": "openai", "model": "gpt-3.5-turbo"}'
```

## Scaling & Maintenance

### Horizontal Scaling
```bash
# Scale application instances
docker-compose -f docker-compose.prod.yml up -d --scale goblin-assistant=3
```

### Log Rotation
```bash
# Configure logrotate for application logs
echo "/app/logs/*.log {
    daily
    rotate 7
    compress
    missingok
    create 644 www-data www-data
}" > /etc/logrotate.d/goblin-assistant
```

### Backup Strategy
- Database: Daily automated backups via Supabase
- Logs: Centralized in Datadog
- Configuration: Version controlled in git

## Troubleshooting

### Common Issues

**Application won't start:**
```bash
# Check environment variables
docker-compose -f docker-compose.prod.yml exec goblin-assistant env

# Check logs
docker-compose -f docker-compose.prod.yml logs goblin-assistant
```

**Datadog not receiving metrics:**
```bash
# Check agent status
docker-compose -f docker-compose.prod.yml exec datadog-agent datadog-agent status

# Test metrics manually
docker-compose -f docker-compose.prod.yml exec goblin-assistant python3 -c "
import datadog
datadog.statsd.increment('test.metric')
print('Test metric sent')
"
```

**High latency alerts:**
- Check database connection pool
- Review Redis queue depth
- Monitor external API rate limits

## Security Checklist

- [ ] SSL/TLS enabled
- [ ] API keys rotated regularly
- [ ] Database connections encrypted
- [ ] Firewall configured
- [ ] Regular security updates
- [ ] Log monitoring for anomalies
- [ ] Rate limiting enabled

## Security Setup

### HashiCorp Vault Configuration (Recommended)

For production deployments, use HashiCorp Vault to securely manage API keys and sensitive configuration:

```bash
# 1. Install Vault CLI (if not already installed)
brew install vault  # macOS
# OR for Linux:
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com jammy main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install vault

# 2. Configure Vault connection
export VAULT_ADDR="https://your-vault-server.com:8200"
export VAULT_TOKEN="your-vault-token"

# 3. Push secrets to Vault
./tools/vault/push_secrets.sh

# 4. Test Vault connection
./tools/vault/fetch_secrets.sh
```

### Alternative: Environment Variables

If Vault is not available, configure secrets via environment variables in `.env.production`.
