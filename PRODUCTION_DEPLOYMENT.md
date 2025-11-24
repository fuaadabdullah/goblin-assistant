# Goblin Assistant Production Deployment Guide

## Prerequisites

1. **Datadog Account**: API and Application keys
2. **HashiCorp Vault**: For secure secrets management (optional but recommended)
3. **Production Server**: Ubuntu 20.04+ or Docker host
4. **Domain**: SSL certificate for HTTPS
5. **Database**: Supabase or PostgreSQL instance
6. **Redis**: For queue management (optional)

## Quick Deploy with Docker

### 1. Setup Environment
```bash
# Clone repository
git clone <repository-url>
cd goblin-assistant

# Copy and configure production environment
cp .env.production.example .env.production
# Edit .env.production with your actual values
```

### 2. Deploy with Docker Compose
```bash
# Deploy all services
docker-compose -f docker-compose.prod.yml up -d

# Check logs
docker-compose -f docker-compose.prod.yml logs -f goblin-assistant
```

### 3. Verify Deployment
```bash
# Check application health
curl https://your-domain.com/health

# Check Datadog agent
docker-compose -f docker-compose.prod.yml logs datadog-agent
```

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
