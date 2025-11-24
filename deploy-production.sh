#!/bin/bash
# Production Deployment Script for Goblin Assistant
# This script deploys the FastAPI backend with Datadog monitoring

set -e

echo "🚀 Deploying Goblin Assistant to Production..."

# Load environment variables
if [ -f ".env.production" ]; then
    export $(cat .env.production | xargs)
    echo "✅ Loaded production environment variables"
else
    echo "❌ .env.production file not found!"
    echo "Please create .env.production with your production configuration"
    exit 1
fi

# Check required environment variables
REQUIRED_VARS=("DD_API_KEY" "DD_APP_KEY" "SUPABASE_URL" "ANTHROPIC_API_KEY")
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Required environment variable $var is not set"
        exit 1
    fi
done

echo "✅ All required environment variables are set"

# Install system dependencies
echo "📦 Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y curl apt-transport-https

# Install Datadog Agent
echo "🐕 Installing Datadog Agent..."
DD_AGENT_MAJOR_VERSION=7 DD_API_KEY=$DD_API_KEY DD_SITE=$DD_SITE bash -c "$(curl -L https://s3.amazonaws.com/dd-agent/scripts/install_script.sh)"

# Configure Datadog Agent
echo "⚙️ Configuring Datadog Agent..."
sudo systemctl enable datadog-agent
sudo systemctl start datadog-agent

# Verify agent is running
echo "🔍 Verifying Datadog Agent..."
sudo datadog-agent status

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r api/fastapi/requirements.txt

# Install ddtrace and datadog packages
pip install ddtrace datadog

# Run database migrations (if applicable)
echo "🗄️ Running database migrations..."
# Add your migration commands here
# python manage.py migrate

# Build and start the application
echo "🏗️ Building and starting application..."
cd api/fastapi

# Set production environment variables for the app
export PYTHONPATH=/app/api/fastapi
export DD_TAGS="env:prod,service:goblin-assistant-api"

# Start with gunicorn for production
gunicorn app:app \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --access-logfile /app/logs/access.log \
    --error-logfile /app/logs/error.log \
    --capture-output \
    --enable-stdio-inheritance \
    --daemon

echo "✅ Application deployed successfully!"
echo ""
echo "🔍 Monitoring URLs:"
echo "• Datadog Dashboard: https://app.datadoghq.com/dashboard/lists"
echo "• Application Health: https://your-domain.com/health"
echo "• API Documentation: https://your-domain.com/docs"
echo ""
echo "📊 Check Datadog for metrics and traces"
echo "🚨 Monitors will alert on issues automatically"
