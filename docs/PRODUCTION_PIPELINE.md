# Goblin Assistant - Production Pipeline

## Overview

This is the **villain-level production pipeline** that makes solo developers look like they have a Fortune 500 engineering department. It combines Bitwarden CLI, CircleCI, and Fly.io into a seamless, secure, cloud-ready deployment system.

**The Ritual**: Commit to `main` → CircleCI wakes up → Pulls secrets from Bitwarden → Deploys to Fly.io → Production is live.

---

## 🏗️ Pipeline Architecture

```text
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Git Push  │ -> │  CircleCI   │ -> │ Bitwarden   │ -> │   Fly.io    │
│   (main)    │    │   Goblin    │    │   Vault     │    │ Production  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                        │                    │                    │
                        ▼                    ▼                    ▼
                   Automated CI         Secure Secrets       Live App
```

### Components

- **Bitwarden CLI**: The vault containing all production secrets
- **CircleCI**: The automation goblin that orchestrates deployment
- **Fly.io**: The cloud dragon hosting your production app
- **You**: The sorcerer commanding the entire ritual

---

## 📦 Phase 1: Bitwarden Vault Setup

### Required Production Secrets

Store these in your Bitwarden "Infra Vault" folder:

| Secret             | Bitwarden Item Name          | Purpose                        |
| ------------------ | ---------------------------- | ------------------------------ |
| FastAPI SECRET_KEY | `goblin-prod-fastapi-secret` | App secret key                 |
| Database URL       | `goblin-prod-db-url`         | Production database connection |
| Cloudflare Token   | `goblin-prod-cloudflare`     | CDN/API token                  |
| OpenAI API Key     | `goblin-prod-openai`         | LLM provider key               |
| JWT Secret         | `goblin-prod-jwt`            | Token signing secret           |
| Fly.io Token       | `goblin-prod-fly-token`      | Deployment authentication      |
| SSH Private Key    | `goblin-ssh-private-key`     | Deployment SSH access          |

### SSH Key Setup

For enhanced security and deployment flexibility, store your SSH private key in Bitwarden:

```bash

# Run the setup script
./scripts/setup_ssh_key.sh
```

This will guide you through:

1. **Creating a Secure Note** in Bitwarden named `goblin-ssh-private-key`
2. **Storing your SSH private key** securely in the vault
3. **Adding the public key** to your GitHub account

**CircleCI will automatically**:

- Retrieve the private key from Bitwarden during deployment
- Set up SSH access for secure operations
- Use SSH for git operations when needed

### Development Secrets (for local parity)

| Secret             | Bitwarden Item Name         | Purpose              |
| ------------------ | --------------------------- | -------------------- |
| FastAPI SECRET_KEY | `goblin-dev-fastapi-secret` | Dev app secret       |
| Database URL       | `goblin-dev-db-url`         | Development database |
| OpenAI API Key     | `goblin-dev-openai`         | Dev LLM key          |

---

## 🔄 Phase 2: CircleCI Configuration

### Setup Steps

1. **Create CircleCI Account**: Connect your GitHub repo to CircleCI

2. **Add Environment Variables** in CircleCI project settings:

   ```
   BW_CLIENTID=your_bitwarden_client_id
   BW_CLIENTSECRET=your_bitwarden_client_secret
   BW_PASSWORD=your_bitwarden_master_password
   ```

3. **Get Bitwarden API Credentials**:
   - Go to Bitwarden web vault → Settings → API Key
   - Generate Organization API key (not personal)

4. **The `.circleci/config.yml`** handles everything else automatically

### What CircleCI Does

1. **Installs Bitwarden CLI** on the build machine
2. **Authenticates** using API key (headless)
3. **Fetches secrets** from vault using `./.circleci/fetch_secrets.sh`
4. **Installs Fly.io CLI**
5. **Deploys** to production
6. **Runs health checks**

---

## ☁️ Phase 3: Fly.io Configuration

### App Setup

1. **Install Fly.io CLI**:

   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. **Login to Fly.io**:

   ```bash

   flyctl auth login
   ```

3. **Create app** (one-time):

   ```bash
   flyctl apps create goblin-assistant
   ```

4. **Deploy initially**:

   ```bash

   flyctl deploy
   ```

### The `fly.toml` Configuration

The provided `fly.toml` is optimized for FastAPI:

- **Paketo buildpacks** for Python
- **Uvicorn** as the ASGI server
- **Health checks** on port 8000
- **HTTP/HTTPS** on ports 80/443

---

## 🚀 Phase 4: Deployment Workflows

### Automatic CI/CD (Recommended)

**Trigger**: Push to `main` branch
**Result**: Automatic production deployment

```yaml
# .circleci/config.yml workflows section
workflows:
  deploy_on_main:
    jobs:
      - deploy:
          filters:
            branches:
              only: main
```

### Manual Deployment

For testing or emergency deploys:

```bash

# From project root
./deploy-fly.sh
```

This script:

- Unlocks Bitwarden vault
- Loads production secrets
- Deploys to Fly.io
- Cleans up secrets

---

## 🔧 Phase 5: Local Development

### Environment Parity

Use the same secrets source for local development:

```bash
# Load development secrets
source scripts/load_env.sh

# Start development server
uvicorn backend.main:app --reload
```

### Secret Management

- **Development**: `goblin-dev-*` secrets
- **Production**: `goblin-prod-*` secrets
- **Same source**: Bitwarden vault
- **Same scripts**: Just different environment prefixes

---

## 🔒 Phase 6: Security Best Practices

### Secret Rotation

```bash

# Rotate production secrets quarterly
bw generate  # Generate new values

# Update items in Bitwarden

# Commit to trigger deployment
```

### Access Control

- **Bitwarden Organizations**: Team access management
- **CircleCI Contexts**: Environment variable scoping
- **Fly.io Teams**: Deployment permissions

### Audit Trail

- **Bitwarden**: Tracks all secret access
- **CircleCI**: Complete deployment logs
- **Fly.io**: Infrastructure change history

---

## 🧪 Phase 7: Testing the Pipeline

### Local Testing

```bash
# Test vault connectivity
./scripts/test_vault.sh

# Test manual deployment (staging)
./deploy-fly.sh
```

### CI/CD Testing

1. **Create feature branch**
2. **Push changes**
3. **Check CircleCI logs**
4. **Verify deployment**
5. **Merge to main** for production

---

## 📊 Phase 8: Monitoring & Observability

### Fly.io Metrics

```bash

# Check app status
flyctl status

# View logs
flyctl logs

# Monitor metrics
flyctl metrics
```

### Health Checks

The pipeline includes post-deployment health checks:

```bash
# CircleCI runs this after deployment
curl -f https://goblin-assistant.fly.dev/health
```

### Alerts

Set up alerts for:

- Deployment failures
- Health check failures
- Resource usage spikes

---

## 🆙 Phase 9: Scaling & Advanced Features

### Blue-Green Deployments

```yaml
# In CircleCI config

- run:
    name: Blue-Green Deploy
    command: |
      flyctl deploy --strategy blue-green
```

### Multi-Environment

```yaml
# Staging deployment
workflows:
  deploy_staging:
    jobs:
      - deploy:
          filters:
            branches:
              only: develop
```

### Rollback Strategy

```bash

# Emergency rollback
flyctl releases
flyctl releases rollback <release-id>
```

---

## 🎯 What This Gives You

### ✅ Zero Secrets in Code

- No plaintext credentials committed
- No `.env` files in repository
- Secrets pulled dynamically at deploy time

### ✅ Enterprise Security

- Bitwarden encryption and access controls
- Audit trails for all secret access
- Secure CI/CD with API key authentication

### ✅ Automated Operations

- Push-to-deploy workflow
- No manual deployment steps
- Consistent dev/prod environments

### ✅ Cost Effective

- Free tier covers most needs
- No enterprise licensing required
- Pay only for actual cloud resources

### ✅ Developer Experience

- Same secrets for local and production
- Fast iteration with automated deploys
- Clear error messages and logging

---

## 🚨 Emergency Procedures

### Failed Deployment

```bash
# Check CircleCI logs
open https://circleci.com/gh/your-org/forgemono

# Check Fly.io status
flyctl status

# Manual deploy if needed
./deploy-fly.sh
```

### Secret Compromise

1. **Rotate affected secrets** in Bitwarden
2. **Generate new values**
3. **Update items immediately**
4. **Trigger deployment** to use new secrets

### Rollback

```bash

# Get release history
flyctl releases

# Rollback to previous version
flyctl releases rollback <previous-release-id>
```

---

## 📚 File Reference

| File                         | Purpose                      |
| ---------------------------- | ---------------------------- |
| `.circleci/config.yml`       | CI/CD pipeline configuration |
| `.circleci/fetch_secrets.sh` | Secret retrieval script      |
| `fly.toml`                   | Fly.io app configuration     |
| `deploy-fly.sh`              | Manual deployment script     |
| `scripts/load_env.sh`        | Local development secrets    |
| `scripts/setup_bitwarden.sh` | Vault initialization         |
| `scripts/setup_ssh_key.sh`   | SSH key vault setup          |
| `scripts/test_vault.sh`      | Vault connectivity testing   |

---

## 🎭 The Sorcerer's Workflow

1. **Code locally** with `source scripts/load_env.sh`
2. **Commit changes** to feature branch
3. **Push to main** → CircleCI deploys automatically
4. **Monitor** via Fly.io dashboard
5. **Scale** as needed

You now have a production pipeline that rivals big tech companies. The "quiet flex" is real - you look like a solo dev with an engineering department in the basement.

**Welcome to the villain arc.** 🧙‍♂️⚔️

---

**Owner**: GoblinOS Security Team
**Last Updated**: December 3, 2025
**Status**: Production Ready
