# Goblin Assistant Production Deployment Guide

This guide covers deploying the Goblin Assistant application to production using Fly.io (backend) and Vercel (frontend).

## 🚀 Quick Start

1. **Prerequisites**
   - Node.js 18+ and npm
   - Python 3.11+
   - Accounts: Fly.io, Vercel, Supabase
   - API keys for AI providers (Anthropic, DeepSeek, Google Gemini, xAI Grok)

2. **Environment Setup**

   ```bash
   cd apps/goblin-assistant
   cp .env.production.example .env.production
   # Edit .env.production with your real values
   ```

3. **Deploy Backend**

   ```bash

   ./deploy-backend.sh fly
   ```

4. **Deploy Frontend**

   ```bash
   ./deploy.sh vercel
   ```

## 📋 Detailed Deployment Steps

### Step 1: Environment Configuration

Create `.env.production` from the template:

```bash

cp .env.production.example .env.production
```

**Required Variables:**

- `ANTHROPIC_API_KEY` - Claude API access
- `DEEPSEEK_API_KEY` - DeepSeek API access
- `GEMINI_API_KEY` - Google Gemini API access
- `GROK_API_KEY` - xAI Grok API access
- `JWT_SECRET_KEY` - Random string for authentication
- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_ANON_KEY` - Supabase anonymous key
- `VITE_FASTAPI_URL` - Backend deployment URL (set after backend deploy)

### Step 2: Database Setup (Supabase)

1. Create a new Supabase project at <https://supabase.com>
2. Run the database migrations:

   ```sql
   -- Execute in Supabase SQL Editor
   -- Schema will be created automatically by the application
   ```

3. Note your project URL and anon key for `.env.production`

### Step 3: Backend Deployment

#### Option A: Fly.io (Recommended)

```bash

./deploy-backend.sh fly
```

**Manual Setup (if CLI fails):**

1. Go to <https://fly.io>
2. Connect your GitHub repo: `fuaadabdullah/ForgeMonorepo`
3. Create Web Service:
   - **Name**: goblin-assistant-backend
   - **Root Directory**: apps/goblin-assistant
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `python backend/start_server.py`
4. Set environment variables from `.env.production`
5. Deploy

#### Option B: Fly.io

```bash
./deploy-backend.sh fly
```

**Manual Setup:**

1. Install Fly CLI: `curl -L https://fly.io/install.sh | sh`
2. Login: `fly auth login`
3. Launch: `fly launch` (use defaults)
4. Set secrets: `fly secrets set KEY=value` for each env var
5. Deploy: `fly deploy`

### Step 4: Frontend Deployment (Vercel)

```bash

./deploy-vercel.sh
```

**Manual Setup:**

1. Install Vercel CLI: `npm install -g vercel`
2. Login: `vercel login`
3. Link or initialize project: `vercel link` (or use dashboard)
4. Set environment variables in Vercel dashboard or via CLI:

   ```bash
   vercel env add VITE_FASTAPI_URL production
   vercel env add VITE_APP_ENV production
   ```

5. Build and deploy: `vercel --prod`

### Step 5: Post-Deployment Configuration

1. **Update Frontend Environment**
   - Set `VITE_FASTAPI_URL` to your backend deployment URL
   - Redeploy frontend if needed

2. **Test the Application**

   ```bash

   # Test health endpoint
   curl <https://your-backend-url/health>

   # Test frontend
   open <https://your-frontend-url>
   ```

3. **Set up Monitoring (Optional)**
   - Set up error tracking with Sentry
   - Enable analytics with PostHog

## 🔧 Troubleshooting

### Backend Issues

**Port Configuration:**

- Fly.io automatically assigns ports
- Application uses `PORT` environment variable

**Database Connection:**

```bash
# Test database connection
curl https://your-backend-url/api/health/db
```

**API Keys:**

- Ensure all AI provider keys are valid
- Check API rate limits and quotas

### Frontend Issues

**CORS Errors:**

- Backend must allow frontend domain in CORS settings
- Check `VITE_FASTAPI_URL` is correct

**Build Failures:**

```bash

# Clear cache and rebuild
rm -rf node_modules/.vite
npm run build
```

**Environment Variables:**

- Only `VITE_` prefixed variables are available in frontend
- Restart deployment after changing env vars

## 📊 Monitoring & Maintenance

### Health Checks

- `/health` - Overall application health
- `/api/health/db` - Database connectivity
- `/api/health/models` - AI model availability

### Logs

- **Fly.io**: View in dashboard or use CLI: `fly logs`
- **Fly.io**: `fly logs`
- **Vercel**: View in dashboard or use CLI: `vercel logs`

### Scaling

- **Fly.io**: Configure scaling via `flyctl scale` or fly.toml settings
- **Fly.io**: Configure in `fly.toml`
- **Vercel**: Automatic for static frontend

## 🔒 Security Considerations

- **API Keys**: Never commit to version control
- **Environment Variables**: Use platform secret management
- **Database**: Enable Row Level Security in Supabase
- **HTTPS**: All platforms provide SSL certificates
- **CORS**: Configure allowed origins in production

## 🚀 CI/CD (Optional)

Set up automatic deployments on push to main branch:

- **Fly.io**: Configure auto-deploy with `flyctl`/CI (recommended) or dashboard
- **Vercel**: Enable in project settings
- **Fly.io**: Use GitHub Actions with flyctl

## 📞 Support

If you encounter issues:

1. Check deployment logs
2. Verify environment variables
3. Test locally with production config
4. Check platform-specific documentation

---

**Last Updated**: November 2025
**Platforms**: Fly.io (Backend), Vercel (Frontend)
**Database**: Supabase PostgreSQL
