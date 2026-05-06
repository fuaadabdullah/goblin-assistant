# Hybrid CI/CD Pipeline Documentation

## 📋 Overview

This document describes the complete hybrid CI/CD pipeline for Goblin Assistant, combining GitHub Actions, CircleCI, and Terraform for a professional-grade deployment system.

**Key Features:**
- ✅ Automated testing on every pull request
- ✅ Infrastructure-as-Code management with Terraform
- ✅ Auto-deployment to staging on main branch
- ✅ Manual approval gate for production
- ✅ Health checks and automatic rollback
- ✅ Comprehensive security scanning

---

## 🏗️ Architecture Overview

### Pipeline Flow

```
┌─────────────────────────────────────────────────────────────┐
│                      Developer Workflow                      │
│                                                               │
│  1. Create feature branch  →  2. Push commits               │
│                                                               │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ↓
        ┌──────────────────────────────────────┐
        │  GitHub Actions (Fast Feedback)     │
        │  - Lint & Type Check               │
        │  - Quick tests (2-5 min)           │
        │  - Runs on: Every commit           │
        └──────────────────────┬───────────────┘
                               │
                    ✅ (PR approved & merged)
                               │
                               ↓
        ┌──────────────────────────────────────┐
        │  CircleCI (Comprehensive)           │
        │  - Full test suite (10-15 min)      │
        │  - Docker build & scan             │
        │  - Security checks                 │
        │  - Runs on: main branch push       │
        └──────────────────────┬───────────────┘
                               │
                    ✅ (All checks pass)
                               │
                               ↓
        ┌──────────────────────────────────────┐
        │  Terraform Plan (Infrastructure)    │
        │  - Validates IaC                    │
        │  - Shows infrastructure changes     │
        └──────────────────────┬───────────────┘
                               │
                    ✅ (Plan reviewed)
                               │
                               ↓
        ┌──────────────────────────────────────┐
        │  Auto-Deploy to Staging            │
        │  - Run Terraform apply             │
        │  - Deploy Docker image             │
        │  - Health checks                   │
        └──────────────────────┬───────────────┘
                               │
                    ✅ (Staging healthy)
                               │
                               ↓
        ┌──────────────────────────────────────┐
        │  Manual Approval Gate               │
        │  - Review staging                   │
        │  - Approve for production           │
        └──────────────────────┬───────────────┘
                               │
                      (Manual trigger)
                               │
                               ↓
        ┌──────────────────────────────────────┐
        │  Deploy to Production               │
        │  - Terraform apply (prod)           │
        │  - Blue-green deployment            │
        │  - Health checks                    │
        │  - Auto-rollback on failure         │
        └──────────────────────────────────────┘
```

### Tools & Platforms

| Tool | Purpose | Used In |
|------|---------|---------|
| **GitHub Actions** | Fast feedback on PRs, validation | Pull requests, main branch |
| **CircleCI** | Comprehensive testing & building | main branch pushes |
| **Terraform** | Infrastructure as Code | Render, Database, Redis |
| **Render** | Backend hosting | Staging & Production |
| **Vercel** | Frontend hosting | Production (native integration) |
| **Docker** | Containerization | Build & deploy |

---

## 🔧 Setup Instructions

### Phase 1: Prerequisites

1. **Verify GitHub repository access**
   ```bash
   git remote -v
   # Should show: origin https://github.com/fuaadabdullah/goblin-assistant.git
   ```

2. **Get required API keys**
   - Render API Key: https://dashboard.render.com/account/api-tokens
   - GitHub Personal Token: https://github.com/settings/tokens (scopes: repo, write:packages)

3. **Set up GitHub Secrets**
   ```
   GitHub → Settings → Secrets and variables → Actions
   ```

   Required secrets:
   ```
   RENDER_API_KEY              # From Render dashboard
   RENDER_SERVICE_ID_STAGING   # Render service ID for staging
   RENDER_SERVICE_ID_PROD      # Render service ID for production
   GITHUB_TOKEN                # Your GitHub personal token
   ```

### Phase 2: Terraform Configuration

1. **Create terraform.tfvars**
   ```bash
   cd terraform
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your actual values
   ```

2. **Initialize Terraform**
   ```bash
   cd terraform
   terraform init
   # Choose backend: local (development) or GitHub/Terraform Cloud (production)
   ```

3. **Validate configuration**
   ```bash
   terraform validate
   terraform fmt -recursive
   ```

### Phase 3: CircleCI Setup

1. **Enable CircleCI**
   - Visit https://app.circleci.com
   - Connect your GitHub repository
   - Enable project

2. **Add CircleCI secrets**
   ```
   Project Settings → Environment Variables
   ```

   ```
   RENDER_API_KEY              # From Render dashboard
   DOCKER_LOGIN                # Docker username (for registry auth)
   DOCKER_PASSWORD             # Docker password/token
   GITHUB_USER                 # GitHub username
   GITHUB_TOKEN                # GitHub personal token
   SNYK_TOKEN                  # (Optional) Snyk security scanning
   ```

### Phase 4: GitHub Actions Setup

1. **Workflows are already configured:**
   - `.github/workflows/ci.yml` - Lint & quick tests
   - `.github/workflows/terraform-plan.yml` - Terraform validation
   - `.github/workflows/deploy-staging.yml` - Auto deploy staging
   - `.github/workflows/deploy-prod.yml` - Manual production deploy

2. **No additional setup needed** - Workflows use GitHub secrets automatically

---

## 📊 Workflow Details

### GitHub Actions Workflows

#### 1. CI Workflow (`.github/workflows/ci.yml`)
**Trigger:** Push to any branch, Pull request  
**Duration:** ~3-5 minutes

**Jobs:**
- Lint & Type Check (ESLint, TypeScript, Prettier)
- Backend Tests (pytest with coverage)
- Frontend Tests (Jest with coverage)
- Build & Bundle Analysis

```bash
# View logs
https://github.com/fuaadabdullah/goblin-assistant/actions?query=workflow:CI
```

#### 2. Terraform Plan Workflow (`.github/workflows/terraform-plan.yml`)
**Trigger:** Changes to `terraform/**` or pull request  
**Duration:** ~2-3 minutes

**Jobs:**
- Terraform format check
- Terraform validation
- Security scan (tfsec)
- Terraform plan (on PRs)
- Policy check (Checkov)
- Secrets validation

**Comments PR with plan output** - Review before merging

#### 3. Deploy Staging Workflow (`.github/workflows/deploy-staging.yml`)
**Trigger:** Push to main branch  
**Duration:** ~15 minutes

**Jobs:**
- Run tests
- Build Docker image
- Terraform plan
- Deploy to Render staging
- Health checks
- Smoke tests

**Auto-deploys** on successful completion

#### 4. Deploy Production Workflow (`.github/workflows/deploy-prod.yml`)
**Trigger:** Manual (`workflow_dispatch`)  
**Duration:** ~20 minutes

**Jobs:**
- Pre-deployment checks
- Terraform plan (production)
- Manual approval gate
- Terraform apply
- Deploy to production
- Health checks & rollback
- Post-deployment verification

**Requires manual approval** - Access via Actions tab

---

### CircleCI Pipeline

**Trigger:** Push to main/develop, tags  
**Duration:** ~15-20 minutes per job

**Jobs:**
1. **Lint** - ESLint check (parallel)
2. **Type Check** - TypeScript validation (parallel)
3. **Backend Test** - pytest with coverage (requires lint + type-check)
4. **Frontend Test** - Jest with coverage (requires lint + type-check)
5. **Build** - Next.js production build (requires tests)
6. **Build Docker** - Docker image build & push (main branch only)
7. **Terraform Validate** - Terraform validation
8. **Deploy Staging** - Auto-deploy to staging (main branch only)

**Scheduled Workflows:**
- Nightly tests at 2 AM UTC (lint, test, build-docker)

```bash
# View CircleCI pipeline
https://app.circleci.com/pipelines/github/fuaadabdullah/goblin-assistant
```

---

## 🚀 Deployment Process

### Staging Deployment (Automatic)

**Trigger:** Successful main branch push  

**Process:**
```
CircleCI passes → Terraform plan → Docker build → Deploy to Render staging → Health checks
```

**Verify:**
```bash
curl https://goblin-assistant-staging.onrender.com/health
```

### Production Deployment (Manual)

**Trigger:** Manual approval + workflow_dispatch  

**Process:**
```
Manual trigger → Pre-checks → Terraform plan → Approval → Terraform apply → 
Deploy to Render prod → Health checks → Rollback on failure → Verify
```

**Step 1: Trigger production deployment**
```
GitHub → Actions → "Deploy to Production" → Run workflow → Select environment
```

**Step 2: Review Terraform plan**
- Changes are shown in workflow output
- Verify infrastructure changes

**Step 3: Approve deployment**
- Click "Approve" button in workflow
- Deployment proceeds

**Step 4: Monitor deployment**
```
GitHub → Actions → Deploy to Production run → View logs
```

**Step 5: Verify production**
```bash
curl https://goblin-assistant-backend.onrender.com/health
curl https://goblin-assistant-backend.onrender.com/api/status
```

---

## 🔄 CI/CD Variables & Secrets

### GitHub Secrets (Required)

| Secret | Source | Usage |
|--------|--------|-------|
| `RENDER_API_KEY` | Render dashboard → Account → API Tokens | Deploy to Render |
| `RENDER_SERVICE_ID_STAGING` | Render dashboard → Service → Settings | Deploy to staging |
| `RENDER_SERVICE_ID_PROD` | Render dashboard → Service → Settings | Deploy to prod |
| `GITHUB_TOKEN` | GitHub → Settings → Tokens | Terraform, workflows |

### GitHub Variables (Optional)

| Variable | Value | Usage |
|----------|-------|-------|
| `VERCEL_ORG_ID` | Vercel dashboard | Frontend deployment |
| `VERCEL_PROJECT_ID` | Vercel dashboard | Frontend deployment |

### Environment Variables (Terraform)

See `terraform.tfvars.example` for complete list:
- `render_api_key` - Render authentication
- `github_token` - GitHub access
- `database_url` - Database connection
- `redis_url` - Cache connection
- `sentry_dsn` - Error tracking
- API keys (OpenAI, Anthropic, Google, etc.)
- Supabase credentials

---

## 📝 Common Tasks

### Viewing Workflow Logs

**GitHub Actions:**
```
https://github.com/fuaadabdullah/goblin-assistant/actions
```

**CircleCI:**
```
https://app.circleci.com/pipelines/github/fuaadabdullah/goblin-assistant
```

### Checking Deployment Status

```bash
# Staging
curl -v https://goblin-assistant-staging.onrender.com/health

# Production
curl -v https://goblin-assistant-backend.onrender.com/health
```

### Rolling Back Deployment

**If production deployment fails:**

```bash
# Manual rollback via Render
1. https://dashboard.render.com
2. Select production service
3. Click "Rollback" or deploy previous version
```

### Updating Terraform Configuration

```bash
# After changing terraform files:
cd terraform
terraform validate
terraform fmt -recursive
git commit -am "Update infrastructure"
git push origin main

# Workflow automatically validates and deploys to staging
```

### Triggering Production Deployment

```bash
# Option 1: UI (Recommended)
GitHub → Actions → Deploy to Production → Run workflow

# Option 2: CLI (if configured)
gh workflow run deploy-prod.yml
```

---

## 🔒 Security Best Practices

### 1. Secrets Management

✅ **Do:**
- Store all secrets in GitHub Secrets
- Rotate API keys regularly (quarterly)
- Use environment-specific secrets (staging vs production)
- Never commit `.tfvars` files

❌ **Don't:**
- Commit credentials to repository
- Share secrets via chat or email
- Use same credentials for staging and production
- Commit Terraform state files

### 2. Access Control

✅ **Workflows:**
- Production deployments require manual approval
- GitHub branch protection: require status checks
- CircleCI restricted to main/develop branches

❌ **Avoid:**
- Auto-deploying to production
- Direct SSH access to servers
- Shared credentials

### 3. Code Review

✅ **Process:**
- All changes require PR review
- Workflows validate code quality
- Terraform changes reviewed before apply

❌ **Avoid:**
- Merging without review
- Skipping CI checks
- Force-pushing to main

---

## 🐛 Troubleshooting

### Workflow Failure: "Missing Secrets"

**Error:** `RENDER_API_KEY secret not found`

**Fix:**
```
1. GitHub → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Add RENDER_API_KEY and other required secrets
```

### Terraform Plan: "Backend not configured"

**Error:** `Error: Backend initialization required`

**Fix:**
```bash
cd terraform
terraform init
# Choose your backend (local, GitHub, or Terraform Cloud)
```

### Docker Build Failure: "Registry authentication failed"

**Error:** `Authentication failed`

**Fix (CircleCI):**
```
1. Project Settings → Environment Variables
2. Add DOCKER_LOGIN and DOCKER_PASSWORD
3. Re-run workflow
```

### Health Check Timeout

**Error:** Deployment succeeded but health check fails

**Check:**
```bash
# Verify service is responding
curl -v https://goblin-assistant-backend.onrender.com/health

# Check service logs
# Render dashboard → Service → Logs
```

### Staging Deploy Stuck

**Issue:** Deployment in progress for >10 minutes

**Fix:**
```bash
# Check current deployment status
curl https://api.render.com/v1/services/$SERVICE_ID \
  -H "Authorization: Bearer $RENDER_API_KEY" | jq '.lastDeployment'

# Cancel and retry from GitHub Actions
```

---

## 📚 Documentation & References

### Internal Documentation
- [Terraform Configuration](terraform/README.md) - Infrastructure-as-Code details
- [GOBLINOS_STORAGE_README.md](GOBLINOS_STORAGE_README.md) - External storage setup
- [render.yaml](render.yaml) - Render deployment backup

### External Resources
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [CircleCI Documentation](https://circleci.com/docs/)
- [Terraform Documentation](https://www.terraform.io/docs)
- [Render Deployment Guide](https://render.com/docs)
- [Vercel Deployment Guide](https://vercel.com/docs)

---

## 🎯 Next Steps

### Immediate (This Week)
- [ ] Add GitHub Secrets
- [ ] Configure CircleCI
- [ ] Test Terraform plan
- [ ] Verify staging deployment

### Short Term (This Month)
- [ ] Set up Terraform Cloud for state management
- [ ] Configure Slack/email notifications
- [ ] Test production deployment process
- [ ] Document runbook for team

### Long Term (Future)
- [ ] Add canary deployments
- [ ] Implement feature flags
- [ ] Set up comprehensive monitoring
- [ ] Automate database migrations
- [ ] Add E2E testing to pipeline

---

## 💬 Support & Questions

For issues or questions:
1. Check troubleshooting section above
2. Review workflow logs (GitHub Actions or CircleCI)
3. Consult team documentation
4. Open an issue in the repository

---

**Last Updated:** May 6, 2026  
**Version:** 1.0  
**Maintained By:** Goblin Assistant Team
