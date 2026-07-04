#!/usr/bin/env bash
# Setup Upstash Redis for goblin-assistant
# This script creates a free Upstash Redis database and configures the connection

set -euo pipefail

echo "=== Upstash Redis Setup for goblin-assistant ==="
echo ""
echo "Step 1: Sign up / log in at https://console.upstash.com"
echo "Step 2: Create a Redis database (free tier available)"
echo "Step 3: Copy the connection string (format: redis://default:<password>@<cluster>.upstash.io:6379)"
echo ""

read -p "Enter your Upstash Redis connection URL: " REDIS_URL

if [ -z "$REDIS_URL" ] || [[ ! "$REDIS_URL" =~ ^redis:// ]]; then
    echo "Invalid Redis URL. Please ensure it starts with 'redis://'"
    exit 1
fi

# Update .env file with Redis URL
if grep -q "^REDIS_URL=" .env; then
    sed -i.bak "s|^REDIS_URL=.*|REDIS_URL=$REDIS_URL|" .env
    echo "Updated REDIS_URL in .env"
else
    echo "" >> .env
    echo "REDIS_URL=$REDIS_URL" >> .env
    echo "Added REDIS_URL to .env"
fi

echo ""
echo "✅ Redis URL saved to .env"
echo "Testing Redis connection..."

# Test the connection (optional, requires redis-cli)
if command -v redis-cli &> /dev/null; then
    # Extract host and port from URL for testing
    REDIS_HOST=$(echo "$REDIS_URL" | sed -E 's|redis://[^@]*@([^:]+):.*|\1|')
    REDIS_PORT=$(echo "$REDIS_URL" | sed -E 's|redis://[^@]*@[^:]+:(.*)|\1|')
    
    if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping 2>&1 | grep -q "PONG"; then
        echo "✅ Redis connection successful!"
    else
        echo "⚠️  Could not ping Redis (may be network/firewall related)"
    fi
else
    echo "redis-cli not available, skipping connection test"
fi

echo ""
echo "Done! Your .env now contains REDIS_URL pointing to your Upstash database."