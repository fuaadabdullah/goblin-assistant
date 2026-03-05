#!/bin/bash

# Fly.io Deployment Script for Goblin Assistant Backend
# This script sets up the necessary environment variables and deploys the application

set -e

echo "🚀 Deploying Goblin Assistant Backend to Fly.io..."

# Check if flyctl is installed
if ! command -v flyctl &> /dev/null; then
    echo "❌ flyctl is not installed. Please install it first:"
    echo "   curl -L https://fly.io/install.sh | sh"
    exit 1
fi

# Configuration
APP_NAME="goblin-assistant"
REGION="sfo"  # Change to your preferred region

echo "📋 Application Configuration:"
echo "   App Name: $APP_NAME"
echo "   Region: $REGION"
echo ""

# Check if app exists, create if not
if ! flyctl apps list | grep -q "$APP_NAME"; then
    echo "🏗️  Creating Fly.io app: $APP_NAME"
    flyctl apps create $APP_NAME --region $REGION
else
    echo "✅ App $APP_NAME already exists"
fi

# Set environment variables
echo "🔐 Setting environment variables..."

# Basic configuration
flyctl secrets set \
    DEBUG=false \
    ENVIRONMENT=production \
    RELEASE_VERSION=goblin-assistant@1.0.0 \
    PORT=8001 \
    ALLOWED_ORIGINS=https://goblin.fuaad.ai,https://api.goblin.fuaad.ai,https://brain.goblin.fuaad.ai,https://ops.goblin.fuaad.ai \
    NEXT_PUBLIC_API_BASE_URL=https://api.goblin.fuaad.ai \
    NEXT_PUBLIC_BACKEND_URL=https://api.goblin.fuaad.ai \
    NEXT_PUBLIC_FASTAPI_URL=https://api.goblin.fuaad.ai \
    NEXT_PUBLIC_FRONTEND_URL=https://goblin.fuaad.ai

# Database configuration (replace with your actual database URL)
echo "🗄️  Please set your database URL:"
echo "   flyctl secrets set DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db"

# Redis configuration (replace with your actual Redis URL)
echo "📦 Please set your Redis URL:"
echo "   flyctl secrets set REDIS_URL=redis://user:pass@host:6379/0"

# Secrets management (replace with your actual Vault configuration)
echo "🔐 Please set your Vault configuration:"
echo "   flyctl secrets set VAULT_URL=https://your-vault-server:8200 VAULT_TOKEN=your-vault-token"

# Supabase configuration (replace with your actual keys)
echo "🌐 Please set your Supabase configuration:"
echo "   flyctl secrets set NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co"
echo "   flyctl secrets set NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key"
echo "   flyctl secrets set SUPABASE_SERVICE_ROLE_KEY=your-service-role-key"

# AI Provider keys (set as needed)
echo "🤖 Please set your AI provider keys (optional):"
echo "   flyctl secrets set OPENAI_API_KEY=your-openai-key"
echo "   flyctl secrets set ANTHROPIC_API_KEY=your-anthropic-key"

# Security configuration
flyctl secrets set \
    RATE_LIMIT_ENABLED=true \
    RATE_LIMIT_REQUESTS=100 \
    RATE_LIMIT_WINDOW=60

# Monitoring configuration
flyctl secrets set \
    DD_SERVICE=goblin-assistant \
    DD_ENV=production \
    DD_VERSION=1.0.0 \
    LOG_LEVEL=INFO

# Deploy
echo ""
echo "🚀 Deploying application..."
flyctl deploy --remote-only

# Check deployment status
echo ""
echo "📊 Checking deployment status..."
sleep 5
flyctl status

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🔗 Application URL: https://$APP_NAME.fly.dev"
echo "📊 Monitoring: https://fly.io/apps/$APP_NAME"
echo "📋 Logs: flyctl logs -a $APP_NAME"
echo ""
echo "⚠️  Next steps:"
echo "   1. Set up your database and Redis URLs"
echo "   2. Configure your Vault/Supabase credentials"
echo "   3. Set up your AI provider API keys"
echo "   4. Configure health checks and monitoring"
echo "   5. Set up custom domains if needed"
