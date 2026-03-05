---
title: "DEPLOYMENT ARCHITECTURE"
description: "Deployment Architecture"
---

# Deployment Architecture

## Overview

### Simplified Deployment Strategy (December 2025)

To reduce complexity and maintenance overhead, Goblin Assistant uses a streamlined two-platform deployment:

```
┌─────────────────────────────────────────────────────────────┐
│                    DEPLOYMENT ARCHITECTURE                   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐      ┌──────────────┐      ┌────────────┐ │
│  │   VERCEL    │─────▶│    FLY.IO    │─────▶│  KAMATERA  │ │
│  │  (Frontend) │      │  (Backend)   │      │ (LLM Models)│ │
│  └─────────────┘      └──────────────┘      └────────────┘ │
│                                                               │
│  UI/React App          FastAPI Server       Ollama Server   │
│  Static Assets         PostgreSQL DB        Local Models    │
│  CDN Distribution      Redis Cache                          │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

**Previous Platforms (Archived)**:

- ❌ Render - Config removed, database migrated to Supabase
- ❌ Railway - Config removed
- ❌ Netlify - Config removed
- ❌ Kubernetes + GitOps - Deferred until 100k+ users

### Infrastructure Consolidation (December 2025)

To eliminate infrastructure sprawl, Goblin Assistant has consolidated from 15+ components to a minimal stack:

#### ✅ Simplified Infrastructure Stack

- **Observability**: Sentry + Vercel Analytics + Fly.io Metrics
- **Secrets**: Bitwarden + Vercel Env Vars + Fly.io Secrets
- **IaC**: Terraform (Kamatera VM only)

#### ❌ Removed Complex Components

- **Monitoring**: Prometheus, Grafana, Loki, Tempo, Datadog
- **Secrets**: SOPS, KMS encryption complexity
- **GitOps**: ArgoCD, Helm charts, Kubernetes manifests

#### Cost & Maintenance Savings

- **Components**: 15+ → 6 core components
- **Maintenance**: ~60 hours/month saved
- **Cost**: Free/built-in platform services
- **Complexity**: Dramatically reduced operational overhead

## Components

### 1. Frontend - Vercel

**Service**: Static Site Hosting
**URL**: `<https://goblin-assistant.vercel.app`>

**Why Vercel?**

- ✅ Zero-config deployment for Vite/React apps
- ✅ Global CDN with edge caching
- ✅ Automatic HTTPS and SSL
- ✅ Preview deployments for PRs
- ✅ Excellent performance and uptime
- ✅ Free tier sufficient for development

**Configuration**: `vercel.json`

- Framework: Vite
- Build Command: `npm run build`
- Output Directory: `dist`
- API Proxy: Forwards `/api/*` to Fly.io backend

### 2. Backend - Fly.io

**Service**: Web Service (Python)
**URL**: `<https://goblin-assistant.fly.dev`>

**Why Fly.io?**

- ✅ Native Python support with pip
- ✅ Global edge network with low latency
- ✅ Environment variable management
- ✅ Auto-deploy from Git
- ✅ Health check monitoring
- ✅ Built-in SSL certificates
- ✅ Better for long-running backend processes than serverless

**Configuration**: `fly.toml`

- Runtime: Python 3.11
- Start Command: `python start_server.py`
- Health Check: `/health` endpoint
- Database: Supabase PostgreSQL
- Redis: Upstash (optional, for production caching)

**Environment Variables** (Set in Fly.io):

```bash
# Required
DATABASE_URL=<from Supabase>
LOCAL_LLM_PROXY_URL=http://45.61.60.3:8002
LOCAL_LLM_API_KEY=<your-kamatera-api-key>
JWT_SECRET_KEY=<generated>
FRONTEND_URL=https://goblin-assistant.vercel.app

# AI Providers
OPENAI_API_KEY=<your-key>
ANTHROPIC_API_KEY=<your-key>
DEEPSEEK_API_KEY=<your-key>
GEMINI_API_KEY=<your-key>
GROK_API_KEY=<your-key>

# OAuth
GOOGLE_CLIENT_ID=<your-id>
GOOGLE_CLIENT_SECRET=<your-secret>
GOOGLE_REDIRECT_URI=https://goblin-assistant.vercel.app/auth/google/callback

# Supabase
SUPABASE_URL=<your-url>
SUPABASE_ANON_KEY=<your-key>
SUPABASE_SERVICE_ROLE_KEY=<your-key>
```

### 3. LLM Models - Kamatera VPS

**Service**: Self-hosted Ollama Server
**URL**: `http://45.61.60.3:8002`

**Why Kamatera?**

- ✅ Cost-effective for running local LLM models
- ✅ Full control over model deployment
- ✅ No per-token pricing (fixed monthly cost)
- ✅ GPU support for faster inference
- ✅ Can run multiple models simultaneously
- ✅ Private network for sensitive data

**Configuration**:

- Server: Ubuntu VPS with GPU
- Software: Ollama + Custom API Proxy
- Models: gemma:2b, phi3:3.8b, qwen2.5:3b, mistral:7b
- API: Custom FastAPI proxy with authentication
- Port: 8002 (with firewall rules)

**Models Available**:

```
gemma:2b        - Safety verification (1.7GB)
phi3:3.8b       - Confidence scoring (2.2GB)
qwen2.5:3b      - Advanced reasoning (1.9GB)
mistral:7b      - Top-tier responses (4.4GB)
deepseek-coder  - Code generation (776MB)
```

## Data Flow

### 1. User Request Flow

```text

User Browser
    ↓
Vercel (Static UI)
    ↓
Fly.io Backend (/api/chat/completions)
    ↓
Kamatera LLM Server (http://45.61.60.3:8002)
    ↓
Ollama Model Inference
    ↓
← Response flows back up the chain
```

### 2. Authentication Flow

```text
User → Vercel UI → Google OAuth
                      ↓
                   Fly.io Backend (validates token)
                      ↓
                   Supabase PostgreSQL (stores session)
                      ↓
                   ← JWT returned to client
```

## Deployment Instructions

### Deploy Frontend to Vercel

1. **Install Vercel CLI** (if not already installed):

   ```bash

   npm install -g vercel
   ```

2. **Login to Vercel**:

   ```bash
   vercel login
   ```

3. **Deploy from project root**:

   ```bash

   cd apps/goblin-assistant
   vercel --prod
   ```

4. **Configure Environment Variables** in Vercel Dashboard:
   - Go to Project Settings → Environment Variables
   - Add variables from `.env.production`
   - Or import from `.env.production` file

5. **Set Custom Domain** (optional):
   - Go to Project Settings → Domains
   - Add `goblin-assistant.vercel.app` or custom domain

### Deploy Backend to Fly.io

1. **Install Fly CLI**:

   ```bash
   curl -L https://fly.io/install.sh | sh
   fly auth login
   ```

2. **Create Fly App**:

   ```bash

   cd apps/goblin-assistant
   fly launch --name goblin-assistant-backend
   ```

3. **Configure Database**:
   - Use Supabase for PostgreSQL (already configured)
   - Set `DATABASE_URL` environment variable

4. **Set Environment Variables**:

   ```bash
   fly secrets set DATABASE_URL="your-supabase-url"
   fly secrets set JWT_SECRET_KEY="$(openssl rand -hex 32)"
   # Add other secrets as needed
   ```

5. **Deploy**:

   ```bash

   fly deploy
   ```

6. **Configure Health Check**:
   - Already configured in `fly.toml`
   - Path: `/health`

7. **Deploy**:
   - Click "Manual Deploy" → "Deploy latest commit"
   - Or enable auto-deploy on push to main

### Configure Kamatera LLM Server

1. **SSH into VPS**:

   ```bash
   ssh root@45.61.60.3
   ```

2. **Install Ollama**:

   ```bash

   curl <https://ollama.ai/install.sh> | sh
   ```

3. **Pull Required Models**:

   ```bash
   ollama pull gemma:2b
   ollama pull phi3:3.8b
   ollama pull qwen2.5:3b
   ollama pull mistral:7b
   ```

4. **Start Ollama Service**:

   ```bash

   systemctl start ollama
   systemctl enable ollama
   ```

5. **Configure API Proxy** (if using custom proxy):

   ```bash
   cd /opt/llm-proxy
   python3 local_llm_proxy.py
   ```

6. **Configure Firewall**:

   ```bash

   ufw allow 8002/tcp
   ufw enable
   ```

7. **Test Connection**:

   ```bash
   curl http://45.61.60.3:8002/health
   ```

## Monitoring & Maintenance

### Vercel

- Monitor deployments: https://vercel.com/dashboard
- View build logs for errors
- Check analytics for traffic patterns
- Set up uptime monitoring (optional)

### Fly.io

- Monitor service health: https://fly.io/dashboard
- Check logs for backend errors: `fly logs`
- Monitor app metrics and scaling
- Set up alerts for downtime
- Review billing and resource usage

### Kamatera

- Monitor VPS resources (CPU, RAM, disk)
- Check Ollama logs: `journalctl -u ollama -f`
- Monitor API proxy logs
- Set up backup for model configurations
- Update models periodically

## Cost Breakdown

### Monthly Costs (Estimated)

| Service               | Plan   | Cost             |
| --------------------- | ------ | ---------------- |
| Vercel (Frontend)     | Hobby  | $0 (free tier)   |
| Fly.io (Backend)      | Free   | $0 (free tier)   |
| Supabase (PostgreSQL) | Free   | $0 (free tier)   |
| Kamatera (VPS)        | Custom | $20-50/month     |
| **Total**             |        | **$20-50/month** |

### Cost Optimization Tips

- Use Vercel and Fly.io free tiers for development
- Upgrade Fly.io only when needed (3GB RAM free tier)
- Kamatera: Use spot instances or reserved pricing
- Supabase: Free tier includes 500MB database

## Security Considerations

### Frontend (Vercel)

- ✅ HTTPS enabled by default
- ✅ Environment variables hidden from client
- ✅ CORS configured for backend API
- ⚠️ Never expose API keys in frontend code

### Backend (Fly.io)

- ✅ Environment variables encrypted at rest
- ✅ SSL/TLS for all connections
- ✅ Database connection encrypted
- ⚠️ Use firewall rules to restrict access
- ⚠️ Rotate JWT secrets regularly

### Kamatera (LLM Server)

- ✅ API key authentication required
- ✅ Firewall configured (UFW)
- ⚠️ Use VPN or private network if possible
- ⚠️ Keep Ollama and system packages updated
- ⚠️ Monitor access logs for suspicious activity

## Troubleshooting

### Frontend Issues

**Problem**: Build fails on Vercel

- Check `package.json` dependencies
- Ensure `vite.config.ts` is correct
- Review build logs in Vercel dashboard

**Problem**: API calls failing

- Verify `VITE_API_URL` in environment variables
- Check CORS configuration in backend
- Inspect network tab in browser DevTools

### Backend Issues

**Problem**: Service won't start on Fly.io

- Check `requirements.txt` for missing dependencies
- Review start command syntax
- Check environment variables are set
- Review build logs: `fly logs`

**Problem**: Database connection fails

- Verify `DATABASE_URL` is set correctly
- Check Supabase service is running
- Review Fly.io app logs: `fly logs`

### LLM Server Issues

**Problem**: Models not responding

- Check Ollama service: `systemctl status ollama`
- Verify models are loaded: `ollama list`
- Check disk space: `df -h`
- Review API proxy logs

**Problem**: Connection timeout from Fly.io

- Verify firewall allows connections from Fly.io IPs
- Check Kamatera server is running
- Test locally: `curl http://45.61.60.3:8002/health`

## Rollback Procedures

### Frontend Rollback (Vercel)

```bash

# Revert to previous deployment
vercel rollback <deployment-url>

# Or via dashboard:

# Deployments → Select working deployment → Promote to Production
```

### Backend Rollback (Fly.io)

```bash
# Revert to previous deployment
fly deploy --image <previous-image-id>

# Or via dashboard:
# Apps → goblin-assistant-backend → Activity → Select working deployment → Scale to 1
```

### Database Migrations

```bash

# Rollback Alembic migration
alembic downgrade -1
```

## Next Steps

1. **Set up CI/CD**:
   - Configure GitHub Actions for automated testing
   - Add deployment workflows

2. **Add Monitoring**:
   - Set up Sentry for error tracking (already configured)
   - Enable Vercel Analytics for frontend metrics (already configured)
   - Monitor Fly.io metrics for backend performance (already configured)

3. **Implement Caching**:
   - Add Redis for session management
   - Cache LLM responses for common queries
   - Use CDN caching for static assets

4. **Scale as Needed**:
   - Upgrade Render plan for more resources
   - Add load balancer for backend
   - Scale Kamatera VPS or add multiple servers

## Support

For deployment issues:

- Vercel: <https://vercel.com/support>
- Fly.io: <https://fly.io/docs/getting-help/>
- Kamatera: support@kamatera.com

For code issues:

- GitHub Issues: <https://github.com/fuaadabdullah/forgemono/issues>
- GoblinOS Docs: `/GoblinOS/docs/`
