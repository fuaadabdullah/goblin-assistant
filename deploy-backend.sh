#!/bin/bash

# Goblin Assistant Backend Production Deployment Script
# Supports Fly.io deployment platform

set -e

echo "🚀 Deploying Goblin Assistant Backend to Production (Fly.io)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Fly.io deployment
deploy_to_fly() {
    print_step "Setting up Fly.io deployment..."

    # Check if Fly CLI is available
    if ! command -v fly &> /dev/null; then
        print_warning "Fly CLI not found. Please install it:"
        print_status "curl -L https://fly.io/install.sh | sh"
        manual_fly_instructions
        return
    fi

    print_status "Creating fly.toml..."
    cat > fly.toml << EOF
app = "goblin-backend"
primary_region = "iad"

[env]
LOG_LEVEL = "info"
PORT = "8001"
ENV = "production"

[build]
dockerfile = "Dockerfile"

[processes]
app = "uvicorn api.main:app --host 0.0.0.0 --port 8001"
worker = "python start_rq_worker.py"

[[services]]
internal_port = 8001
processes = ["app"]
protocol = "tcp"

[[services.ports]]
port = 80
handlers = ["http"]
[[services.ports]]
port = 443
handlers = ["tls", "http"]

[[services.http_checks]]
path = "/health"
interval = "15s"
timeout = "5s"
grace_period = "5s"

[[mounts]]
source = "data"
destination = "/app/data"

[[mounts]]
source = "redis_data"
destination = "/data/redis"
EOF

    print_status "Deploying to Fly.io..."
    fly deploy

    print_status "Fly.io deployment completed ✓"
}

# Manual instructions for Fly.io
manual_fly_instructions() {
    echo ""
    print_status "Manual Fly.io Deployment Instructions:"
    echo "1. Go to https://fly.io"
    echo "2. Install Fly CLI: curl -L https://fly.io/install.sh | sh"
    echo "3. Login: fly auth login"
    echo "4. Create app: fly launch --name goblin-assistant --region iad --no-deploy"
    echo "5. Create volume: fly volumes create chroma-db --region iad --size 3"
    echo "6. Set secrets: fly secrets set <KEY>=<VALUE> for each env var"
    echo "7. Deploy: fly deploy"
    echo ""
}

# Get deployment URL
get_deployment_url() {
    print_step "Getting deployment URL..."

    FLY_URL=$(fly status --json | jq -r '.Hostname')
    if [ -n "$FLY_URL" ]; then
        print_status "Backend deployed at: https://$FLY_URL"
    fi
}

# Platform selection
PLATFORM=${1:-"fly"}

case $PLATFORM in
    "fly")
        print_status "Deploying to Fly.io"
        deploy_to_fly
        ;;
    *)
        print_error "Invalid platform. Use: fly"
        exit 1
        ;;
esac

# Main deployment function
main() {
    echo "Goblin Assistant Backend Production Deployment"
    echo "=============================================="
    echo "Platform: $PLATFORM"
    echo ""

    # Validate environment
    if [ ! -f ".env.production" ]; then
        print_error ".env.production file not found!"
        print_status "Please create .env.production with your production environment variables"
        exit 1
    fi

    # Deploy based on platform
    case $PLATFORM in
        "fly")
            deploy_to_fly
            ;;
    esac

    get_deployment_url

    echo ""
    print_status "🎉 Backend deployment initiated!"
    echo ""
    print_status "Next steps:"
    echo "1. Wait for deployment to complete"
    echo "2. Note the backend URL for frontend configuration"
    echo "3. Deploy frontend: ./deploy-vercel.sh"
    echo "4. Test the complete application"
}

# Show usage if no arguments
if [ $# -eq 0 ]; then
    echo "Usage: $0 <platform>"
    echo "Platforms: fly"
    echo ""
    echo "Examples:"
    echo "  $0 fly       # Deploy to Fly.io"
    echo ""
    exit 1
fi

# Run main function
main "$@"