#!/bin/bash
# Deploy Goblin Assistant with GCP Chat Integration
# Usage: ./deploy-gcp-chat.sh [environment]
# Environments: local, staging, production

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Environment
ENV="${1:-local}"

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Goblin Assistant - GCP Chat Deployment               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Environment:${NC} $ENV"
echo ""

# Check GCP servers are accessible
echo -e "${BLUE}[1/6]${NC} Checking GCP infrastructure..."

OLLAMA_URL="http://34.60.255.199:11434"
LLAMACPP_URL="http://34.132.226.143:8000"

if curl -s -f "$OLLAMA_URL/api/tags" > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} Ollama server accessible: $OLLAMA_URL"
else
    echo -e "  ${YELLOW}⚠${NC} Ollama server not accessible (may need VPN/firewall)"
fi

if curl -s -f "$LLAMACPP_URL/v1/models" > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} LlamaCPP server accessible: $LLAMACPP_URL"
else
    echo -e "  ${YELLOW}⚠${NC} LlamaCPP server not ready (model downloading)"
fi

echo ""

# Deploy based on environment
case "$ENV" in
    local)
        echo -e "${BLUE}[2/6]${NC} Starting local development servers..."
        
        # Check if backend is running
        if lsof -i :8004 > /dev/null 2>&1; then
            echo -e "  ${GREEN}✓${NC} Backend already running on port 8004"
        else
            echo -e "  ${BLUE}→${NC} Starting backend on port 8004..."
            nohup python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8004 > /tmp/goblin-backend.log 2>&1 &
            sleep 3
            if lsof -i :8004 > /dev/null 2>&1; then
                echo -e "  ${GREEN}✓${NC} Backend started successfully"
            else
                echo -e "  ${RED}✗${NC} Backend failed to start. Check /tmp/goblin-backend.log"
                exit 1
            fi
        fi
        
        echo ""
        echo -e "${BLUE}[3/6]${NC} Starting frontend..."
        
        # Check if frontend is running
        if lsof -i :3000 > /dev/null 2>&1; then
            echo -e "  ${GREEN}✓${NC} Frontend already running on port 3000"
        else
            echo -e "  ${BLUE}→${NC} Starting frontend on port 3000..."
            npm run dev > /tmp/goblin-frontend.log 2>&1 &
            sleep 5
            if lsof -i :3000 > /dev/null 2>&1; then
                echo -e "  ${GREEN}✓${NC} Frontend started successfully"
            else
                echo -e "  ${RED}✗${NC} Frontend failed to start. Check /tmp/goblin-frontend.log"
                exit 1
            fi
        fi
        
        echo ""
        echo -e "${BLUE}[4/6]${NC} Testing API endpoint..."
        sleep 2
        
        RESPONSE=$(curl -s -X POST http://localhost:8004/api/chat \
            -H "Content-Type: application/json" \
            -d '{"messages":[{"role":"user","content":"Test"}],"provider":"ollama_gcp"}')
        
        if echo "$RESPONSE" | grep -q '"ok":true'; then
            echo -e "  ${GREEN}✓${NC} API test successful"
        else
            echo -e "  ${YELLOW}⚠${NC} API test returned unexpected response"
            echo "  Response: $RESPONSE"
        fi
        
        echo ""
        echo -e "${BLUE}[5/6]${NC} Deployment summary..."
        echo -e "  ${GREEN}✓${NC} Backend: http://localhost:8004"
        echo -e "  ${GREEN}✓${NC} Frontend: http://localhost:3000"
        echo -e "  ${GREEN}✓${NC} Chat UI: http://localhost:3000/chat"
        
        echo ""
        echo -e "${BLUE}[6/6]${NC} Local deployment complete!"
        echo ""
        echo -e "${GREEN}Next steps:${NC}"
        echo "  1. Open http://localhost:3000/chat in your browser"
        echo "  2. Type a message and test the chat functionality"
        echo "  3. Check logs:"
        echo "     - Backend: tail -f /tmp/goblin-backend.log"
        echo "     - Frontend: tail -f /tmp/goblin-frontend.log"
        ;;
        
    staging)
        echo -e "${BLUE}[2/6]${NC} Deploying to Fly.io staging..."
        
        # Check if fly CLI is installed
        if ! command -v fly &> /dev/null; then
            echo -e "  ${RED}✗${NC} Fly CLI not installed. Install: https://fly.io/docs/hands-on/install-flyctl/"
            exit 1
        fi
        
        echo -e "  ${BLUE}→${NC} Setting secrets..."
        fly secrets set \
            OLLAMA_GCP_URL="$OLLAMA_URL" \
            LLAMACPP_GCP_URL="$LLAMACPP_URL" \
            --app goblin-assistant-staging
        
        echo ""
        echo -e "${BLUE}[3/6]${NC} Deploying backend..."
        fly deploy --app goblin-assistant-staging
        
        echo ""
        echo -e "${BLUE}[4/6]${NC} Testing staging API..."
        sleep 5
        
        STAGING_URL="https://goblin-assistant-staging.fly.dev"
        RESPONSE=$(curl -s -f "$STAGING_URL/health" || echo "FAILED")
        
        if [ "$RESPONSE" != "FAILED" ]; then
            echo -e "  ${GREEN}✓${NC} Staging API is healthy"
        else
            echo -e "  ${RED}✗${NC} Staging API health check failed"
            exit 1
        fi
        
        echo ""
        echo -e "${BLUE}[5/6]${NC} Deploying frontend to Vercel..."
        echo -e "  ${YELLOW}⚠${NC} Manual step required:"
        echo "     vercel --scope your-team"
        echo "     Set NEXT_PUBLIC_API_BASE_URL=$STAGING_URL"
        
        echo ""
        echo -e "${BLUE}[6/6]${NC} Staging deployment complete!"
        ;;
        
    production)
        echo -e "${BLUE}[2/6]${NC} Deploying to production..."
        
        # Confirmation prompt
        echo -e "${YELLOW}⚠ WARNING:${NC} You are about to deploy to PRODUCTION"
        read -p "Type 'yes' to continue: " CONFIRM
        
        if [ "$CONFIRM" != "yes" ]; then
            echo -e "${RED}Deployment cancelled${NC}"
            exit 1
        fi
        
        echo ""
        echo -e "  ${BLUE}→${NC} Setting production secrets..."
        fly secrets set \
            OLLAMA_GCP_URL="$OLLAMA_URL" \
            LLAMACPP_GCP_URL="$LLAMACPP_URL" \
            --app goblin-assistant
        
        echo ""
        echo -e "${BLUE}[3/6]${NC} Deploying backend..."
        fly deploy --app goblin-assistant
        
        echo ""
        echo -e "${BLUE}[4/6]${NC} Testing production API..."
        sleep 5
        
        PROD_URL="https://goblin-assistant.fly.dev"
        RESPONSE=$(curl -s -f "$PROD_URL/health" || echo "FAILED")
        
        if [ "$RESPONSE" != "FAILED" ]; then
            echo -e "  ${GREEN}✓${NC} Production API is healthy"
        else
            echo -e "  ${RED}✗${NC} Production API health check failed"
            exit 1
        fi
        
        echo ""
        echo -e "${BLUE}[5/6]${NC} Deploying frontend to Vercel..."
        vercel --prod
        
        echo ""
        echo -e "${BLUE}[6/6]${NC} Production deployment complete!"
        echo ""
        echo -e "${GREEN}Monitor:${NC}"
        echo "  - Fly.io: fly status --app goblin-assistant"
        echo "  - GCP: https://console.cloud.google.com"
        ;;
        
    *)
        echo -e "${RED}Error:${NC} Invalid environment: $ENV"
        echo "Usage: $0 [local|staging|production]"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Deployment to $ENV completed successfully! 🚀${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo ""
