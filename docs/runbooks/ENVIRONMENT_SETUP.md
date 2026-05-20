# Environment Variables Setup

This document explains how to set up environment variables for the Goblin Assistant application.

## Quick Setup with Secure Script

For the most secure setup, use the interactive script that helps you replace generated values with your own secrets:

```bash
# Run the secure setup script
./setup-secure-env.sh
```

This script will:

- Prompt you to enter your own secrets from your password manager
- Validate input formats where possible
- Update all environment files automatically
- Provide security reminders

## Required Environment Variables

### Authentication & Security

- `JWT_SECRET_KEY`: Secret key for JWT token signing/verification (64-character hex string)
  - Generate with: `openssl rand -hex 32`
  - Must match between frontend and backend

### Docker Compose Deployments

#### Kamatera Deployment (`/deployments/kamatera/.env`)

- `POSTGRES_PASSWORD`: PostgreSQL database password
- `FLOWER_BASIC_AUTH`: Basic auth credentials for Celery Flower (format: `user:password`)

#### Vault Deployment (`docker-compose.vault.env`)

- `VAULT_DEV_ROOT_TOKEN_ID`: Vault root token for development
- `VAULT_POSTGRES_PASSWORD`: PostgreSQL password for Vault database

#### Raptor Mini (`/apps/raptor-mini/.env`)

- `RAPTOR_API_KEY`: API key for Raptor Mini model serving

## Manual Setup Instructions

If you prefer to set up manually:

1. **Copy example files:**

   ```bash
   cp .env.example .env.local
   cp api/.env api/.env.local
   ```

2. **Generate secure JWT secret:**

   ```bash
   JWT_SECRET=$(openssl rand -hex 32)
   echo "JWT_SECRET_KEY=$JWT_SECRET" >> .env.local
   echo "JWT_SECRET_KEY=$JWT_SECRET" >> api/.env
   ```

3. **Set deployment environment variables:**

   ```bash
   # Kamatera
   echo "POSTGRES_PASSWORD=your_secure_password_here" >> deployments/kamatera/.env
   echo "FLOWER_BASIC_AUTH=user:your_secure_password" >> deployments/kamatera/.env

   # Vault
   echo "VAULT_DEV_ROOT_TOKEN_ID=your_secure_vault_token" >> docker-compose.vault.env
   echo "VAULT_POSTGRES_PASSWORD=your_secure_vault_db_password" >> docker-compose.vault.env

   # Raptor Mini
   echo "RAPTOR_API_KEY=your_secure_raptor_api_key" >> apps/raptor-mini/.env
   ```

4. **Update Supabase and API keys** with your actual values in `.env.local`

## Security Notes

- Never commit `.env` files containing real secrets to version control
- Use different values for development, staging, and production
- Rotate secrets regularly
- Use a password manager or secret management service for production deployments

## Files Created/Updated

- `.env.local` - Frontend environment variables
- `api/.env` - Backend environment variables
- `deployments/kamatera/.env` - Kamatera deployment variables
- `docker-compose.vault.env` - Vault deployment variables
- `apps/raptor-mini/.env` - Raptor Mini variables
- `.env.example` - Documentation of all required variables

