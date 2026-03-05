#!/bin/bash

# Fly.io Secrets Setup Script for Goblin Assistant Backend
# This script sets up all required environment variables as Fly.io secrets

set -e

echo "🚀 Setting up Fly.io secrets for Goblin Assistant Backend..."

# Check if flyctl is installed
if ! command -v flyctl &> /dev/null; then
    echo "❌ flyctl is not installed. Please install it first:"
    echo "   curl -L https://fly.io/install.sh | sh"
    exit 1
fi

# Configuration
APP_NAME="goblin-backend"

# Check if app exists
if ! flyctl apps list | grep -q "$APP_NAME"; then
    echo "❌ App $APP_NAME not found. Please create it first:"
    echo "   flyctl apps create $APP_NAME"
    exit 1
fi

echo "📋 Setting secrets for app: $APP_NAME"

# Basic configuration
echo "🔧 Setting basic configuration..."
flyctl secrets set \
    DEBUG=false \
    ENVIRONMENT=production \
    RELEASE_VERSION=goblin-assistant@1.0.0 \
    PORT=8001 \
    ALLOWED_ORIGINS=https://your-domain.com,https://www.your-domain.com

# Database configuration (CRITICAL - Replace with your actual database URL)
echo "🗄️  Setting database configuration..."
echo "⚠️  IMPORTANT: You must replace the DATABASE_URL with your actual PostgreSQL connection string"
echo "   Example: postgresql+asyncpg://username:password@hostname:5432/database_name"
echo "   Common providers:"
echo "   - Supabase: postgresql+asyncpg://postgres:your_password@db.your_project.supabase.co:5432/postgres"
echo "   - Neon: postgresql+asyncpg://user:pass@ep-xxx.us-east-1.aws.neon.tech/neondb"
echo "   - AWS RDS: postgresql+asyncpg://username:password@your-rds-host:5432/database_name"

read -p "❓ Do you have a PostgreSQL database ready? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    read -p "🔗 Enter your DATABASE_URL: " DATABASE_URL
    if [ -n "$DATABASE_URL" ]; then
        flyctl secrets set DATABASE_URL="$DATABASE_URL"
        echo "✅ Database URL set"
    else
        echo "⚠️  Skipping DATABASE_URL - you must set this manually"
    fi
else
    echo "⚠️  Please set up a PostgreSQL database and run:"
    echo "   flyctl secrets set DATABASE_URL=your_database_url"
fi

# Redis configuration (CRITICAL - Replace with your actual Redis URL)
echo "📦 Setting Redis configuration..."
echo "⚠️  IMPORTANT: You must replace the REDIS_URL with your actual Redis connection string"
echo "   Example: redis://username:password@hostname:6379/0"
echo "   Common providers:"
echo "   - Redis Cloud: redis://username:password@redis-12345.c123.us-east-1-4.ec2.cloud.redislabs.com:12345"
echo "   - Upstash: redis://default:your_token@redis-12345.upstash.io:6379"
echo "   - AWS ElastiCache: redis://username:password@your-elasticache-host:6379/0"

read -p "❓ Do you have a Redis instance ready? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    read -p "🔗 Enter your REDIS_URL: " REDIS_URL
    if [ -n "$REDIS_URL" ]; then
        flyctl secrets set REDIS_URL="$REDIS_URL"
        echo "✅ Redis URL set"
    else
        echo "⚠️  Skipping REDIS_URL - you must set this manually"
    fi
else
    echo "⚠️  Please set up a Redis instance and run:"
    echo "   flyctl secrets set REDIS_URL=your_redis_url"
fi

# Secrets management (Optional - Replace with your actual Vault configuration)
echo "🔐 Setting secrets management configuration..."
read -p "❓ Do you have HashiCorp Vault configured? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    read -p "🔗 Enter your VAULT_URL: " VAULT_URL
    read -p "🔑 Enter your VAULT_TOKEN: " VAULT_TOKEN
    if [ -n "$VAULT_URL" ] && [ -n "$VAULT_TOKEN" ]; then
        flyctl secrets set VAULT_URL="$VAULT_URL" VAULT_TOKEN="$VAULT_TOKEN"
        echo "✅ Vault configuration set"
    else
        echo "⚠️  Skipping Vault configuration"
    fi
else
    echo "⚠️  Vault not configured - secrets management will be limited"
fi

# Supabase configuration (Optional - Replace with your actual keys)
echo "🌐 Setting Supabase configuration..."
read -p "❓ Do you have Supabase configured? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    read -p "🔗 Enter your NEXT_PUBLIC_SUPABASE_URL: " SUPABASE_URL
    read -p "🔑 Enter your NEXT_PUBLIC_SUPABASE_ANON_KEY: " SUPABASE_ANON_KEY
    read -p "🔑 Enter your SUPABASE_SERVICE_ROLE_KEY: " SUPABASE_SERVICE_ROLE_KEY
    if [ -n "$SUPABASE_URL" ] && [ -n "$SUPABASE_ANON_KEY" ] && [ -n "$SUPABASE_SERVICE_ROLE_KEY" ]; then
        flyctl secrets set \
            NEXT_PUBLIC_SUPABASE_URL="$SUPABASE_URL" \
            NEXT_PUBLIC_SUPABASE_ANON_KEY="$SUPABASE_ANON_KEY" \
            SUPABASE_SERVICE_ROLE_KEY="$SUPABASE_SERVICE_ROLE_KEY"
        echo "✅ Supabase configuration set"
    else
        echo "⚠️  Skipping Supabase configuration"
    fi
else
    echo "⚠️  Supabase not configured - authentication features will be limited"
fi

# AI Provider keys (Optional)
echo "🤖 Setting AI provider configuration..."
read -p "❓ Do you have OpenAI API key? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    read -p "🔑 Enter your OPENAI_API_KEY: " OPENAI_API_KEY
    if [ -n "$OPENAI_API_KEY" ]; then
        flyctl secrets set OPENAI_API_KEY="$OPENAI_API_KEY"
        echo "✅ OpenAI API key set"
    fi
fi

read -p "❓ Do you have Anthropic API key? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    read -p "🔑 Enter your ANTHROPIC_API_KEY: " ANTHROPIC_API_KEY
    if [ -n "$ANTHROPIC_API_KEY" ]; then
        flyctl secrets set ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY"
        echo "✅ Anthropic API key set"
    fi
fi

# Security configuration
echo "🔒 Setting security configuration..."
flyctl secrets set \
    RATE_LIMIT_ENABLED=true \
    RATE_LIMIT_REQUESTS=100 \
    RATE_LIMIT_WINDOW=60

# Monitoring configuration
echo "📊 Setting monitoring configuration..."
flyctl secrets set \
    DD_SERVICE=goblin-assistant \
    DD_ENV=production \
    DD_VERSION=1.0.0 \
    LOG_LEVEL=INFO

# Verify secrets were set
echo ""
echo "✅ Secrets setup complete!"
echo ""
echo "📋 Current secrets for $APP_NAME:"
flyctl secrets list -a $APP_NAME

echo ""
echo "🎯 Next steps:"
echo "1. Verify all critical secrets are set (DATABASE_URL, REDIS_URL)"
echo "2. Deploy your application:"
echo "   flyctl deploy -a $APP_NAME"
echo "3. Monitor the deployment:"
echo "   flyctl logs -a $APP_NAME -f"
echo "4. Test health endpoints:"
echo "   curl https://$APP_NAME.fly.dev/health"
echo ""
echo "🆘 If you encounter issues:"
echo "   - Check logs: flyctl logs -a $APP_NAME"
echo "   - Check machine status: flyctl machines list -a $APP_NAME"
echo "   - Check health: curl https://$APP_NAME.fly.dev/health"
