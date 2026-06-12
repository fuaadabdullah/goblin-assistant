# Bitwarden Infra Vault Setup

## Overview

This guide establishes a secure "Infra Vault" in Bitwarden for managing all Goblin Assistant secrets. This replaces scattered environment files and provides enterprise-grade secret management without enterprise pricing.

## Quick Start Setup

### Automated Setup (Recommended)

1. **Install Bitwarden CLI**:

   ```bash
   npm install -g @bitwarden/cli
   ```

2. **Run the setup script**:

   ```bash

   cd apps/goblin-assistant
   ./scripts/setup_bitwarden.sh
   ```

3. **Test the setup**:

   ```bash
   ./scripts/test_vault.sh
   ```

4. **Load secrets for development**:

   ```bash

   source scripts/load_env.sh
   ```

### Manual Setup

If you prefer manual setup, follow the detailed steps below.

## 1. Create the Infra Vault Structure

### Vault Organization

Create a dedicated "Infra Vault" folder in Bitwarden with the following structure:

```text
Infra Vault/
├── goblin-dev-fastapi-secret
├── goblin-dev-db-url
├── goblin-dev-jwt-secret
├── goblin-dev-cloudflare-api
├── goblin-dev-openai-key
├── goblin-dev-cloudinary-key
├── goblin-dev-groq-key
├── goblin-dev-anthropic-key
├── goblin-prod-fastapi-secret
├── goblin-prod-db-url
├── goblin-prod-jwt-secret
├── goblin-prod-cloudflare-api
├── goblin-prod-openai-key
├── goblin-prod-cloudinary-key
├── goblin-prod-groq-key
├── goblin-prod-anthropic-key
└── goblin-ssh-private-key
```

### Naming Convention

- **Format**: `{project}-{environment}-{service}-{type}`
- **Project**: `goblin` (main project), `rizzk` (future projects)
- **Environment**: `dev`, `staging`, `prod`
- **Service**: `fastapi`, `db`, `jwt`, `cloudflare`, `openai`, etc.
- **Type**: `secret`, `key`, `url`, `api`, `token`

### Secret Types to Store

- **FastAPI Secrets**: Application secret keys
- **JWT Signing Keys**: Token signing secrets
- **Database URLs**: Full connection strings with credentials
- **Cloudflare API Tokens**: Zone and API tokens
- **LLM Provider Keys**: OpenAI, Groq, Anthropic, etc.
- **Internal Tokens**: Goblin-agent service tokens
- **SSH Keys**: Private keys for deployments (optional, high-risk)

## 2. Bitwarden CLI Setup (Headless)

### One-Time Login

```bash

# Login to Bitwarden CLI
bw login YOUR_EMAIL

# Unlock and capture session token
bw unlock --raw
```

### Export Session Token

```bash
# Export session token to environment
export BW_SESSION="YOUR_SESSION_TOKEN_HERE"
```

**Security Note**: Never commit `BW_SESSION` to code. This token expires and should be refreshed regularly.

## 3. Pull Secrets into Application Pipeline

### Single Secret Retrieval

```bash

# Get a password field
bw get password goblin-prod-fastapi-secret

# Get custom field from item
bw get item goblin-prod-cloudflare-api | jq -r '.fields[] | select(.name=="API_KEY") | .value'
```

### Load into Environment Variables

```bash
# Load secrets for local development
export FASTAPI_SECRET=$(bw get password goblin-dev-fastapi-secret)
export DB_URL=$(bw get password goblin-dev-db-url)
export CLOUDFLARE_API=$(bw get item goblin-dev-cloudflare-api | jq -r '.fields[] | select(.name=="API_KEY") | .value')
export OPENAI_KEY=$(bw get password goblin-dev-openai-key)
```

### Automated Loading Script

Use the provided `scripts/load_env.sh`:

```bash

# Load all development secrets
source scripts/load_env.sh
```

## 4. Deployment Integration

### CI/CD Pipeline Setup

Instead of hard-coded secrets in CI platforms:

```bash
# During deployment
export BW_SESSION=$(bw unlock --raw)
export FASTAPI_SECRET=$(bw get password goblin-prod-fastapi-secret)
export DB_URL=$(bw get password goblin-prod-db-url)
export CLOUDFLARE_API=$(bw get password goblin-prod-cloudflare-api)

# Deploy to your platform
vercel deploy --prod
# or
fly deploy
# or
render-cli deploy
```

### Platform-Specific Examples

#### Vercel

```bash

# Set secrets via CLI
vercel env add FASTAPI_SECRET production
vercel env add DB_URL production
```

#### Fly.io

```bash
# Use fly secrets set
fly secrets set FASTAPI_SECRET=$FASTAPI_SECRET
fly secrets set DB_URL=$DB_URL
fly secrets set FASTAPI_SECRET=$FASTAPI_SECRET
```

## 5. Local Development Workflow

### Quick Environment Loading

```bash

# Navigate to project root
cd apps/goblin-assistant

# Load environment
source scripts/load_env.sh

# Start development server
npm run dev

# or
python -m uvicorn backend.main:app --reload
```

### Environment File Templates

Update `.env.example` to reference Bitwarden:

```bash
# .env.example
# Load secrets from Bitwarden vault using: source scripts/load_env.sh

FASTAPI_SECRET=goblin-dev-fastapi-secret
DB_URL=goblin-dev-db-url
OPENAI_API_KEY=goblin-dev-openai-key
CLOUDFLARE_API_TOKEN=goblin-dev-cloudflare-api
```

## 6. Goblin-Agent Runtime Integration (Advanced)

### Runtime Secret Fetching (Use with Caution)

For dynamic secret loading at runtime:

```python

import subprocess
import os
from functools import lru_cache

@lru_cache(maxsize=1)
def get_bw_session():
    """Cache BW session for performance"""
    result = subprocess.run(['bw', 'unlock', '--raw'],
                          capture_output=True, text=True)
    return result.stdout.strip()

def get_secret(secret_name: str) -> str:
    """Fetch secret from Bitwarden at runtime"""
    session = get_bw_session()
    result = subprocess.run(['bw', 'get', 'password', secret_name],
                          env={**os.environ, 'BW_SESSION': session},
                          capture_output=True, text=True)
    return result.stdout.strip()

# Usage in FastAPI
from fastapi import Depends
from app.dependencies import get_secret

@app.get("/api/secure")
async def secure_endpoint(secret: str = Depends(lambda: get_secret("goblin-prod-api-key"))):
    # Use secret here
    pass
```

**⚠️ Warning**: Runtime secret fetching increases attack surface. Prefer CI-level loading for production.

## 7. Security Best Practices

### Secret Lifecycle

```bash
# After deployment, clean up
unset BW_SESSION

# Rotate secrets regularly
bw generate  # Generate new password
bw edit item goblin-prod-fastapi-secret  # Update item
```

### Key Rotation Schedule

- **Development**: Rotate every 6 months
- **Production**: Rotate every 90 days
- **Compromised Keys**: Rotate immediately

### Access Control

- Use Bitwarden organizations for team access
- Implement principle of least privilege
- Regular access audits

### Emergency Procedures

- **Lost Access**: Contact team lead for vault recovery
- **Compromised Secrets**: Rotate all affected secrets immediately
- **Backup**: Export encrypted vault backup quarterly

## 8. Migration from Existing Secrets

### From .env Files

1. Move secrets to Bitwarden vault
2. Update `.env` files to reference vault items
3. Add loading script to development workflow
4. Remove plaintext secrets from repository

### Migration Complete

Bitwarden is now the primary secrets management solution for all environments.

## 9. Troubleshooting

### "Vault is locked"

```bash

# Re-unlock vault
export BW_SESSION=$(bw unlock --raw)
```

### "Item not found"

```bash
# List available items
bw list items --search "goblin"

# Check item name spelling
bw get item "exact-item-name"
```

### "Session expired"

```bash

# Refresh session
export BW_SESSION=$(bw unlock --raw)
```

## 10. Integration with Existing Tools

### With Docker

```dockerfile
# Dockerfile
FROM python:3.11

# Copy load script
COPY scripts/load_env.sh /app/

# Load secrets during build (not recommended for production)
RUN source /app/load_env.sh && echo "Secrets loaded"
```

### With Kubernetes

```yaml
# Use Bitwarden CLI in init container
apiVersion: v1
kind: Pod
spec:
  initContainers:
    - name: load-secrets
      image: bitwarden/cli:latest
      command: ['sh', '-c']
      args:
        - |
          export BW_SESSION=$(bw unlock --raw)
          bw get password goblin-prod-db-url > /secrets/db-url
      volumeMounts:
        - name: secrets
          mountPath: /secrets
  containers:
    - name: app
      env:
        - name: DB_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
```

## Benefits

✅ **Zero secrets in repository** - No plaintext credentials committed
✅ **Centralized management** - All secrets in one secure vault
✅ **Automated loading** - Scripts handle environment setup
✅ **Team collaboration** - Shared vault with access controls
✅ **Audit trail** - Bitwarden tracks all access
✅ **Cost effective** - Free tier covers most needs
✅ **Platform agnostic** - Works with any deployment target

## Next Steps

1. Create Bitwarden account and vault
2. Set up CLI access on development machine
3. Migrate existing secrets from `.env` files
4. Update deployment pipelines
5. Train team on vault usage
6. Establish rotation schedule

---

**Owner**: GoblinOS Security Team
**Last Updated**: December 3, 2025
**Status**: Active
