#!/bin/bash

# Goblin Assistant Production Deployment Verification
# This script verifies that both backend and frontend are deployed and operational

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[VERIFY]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Configuration
BACKEND_URL="${BACKEND_URL:-https://goblin-backend-dt30.onrender.com}"
FRONTEND_URL="${FRONTEND_URL:-https://goblin-assistant.vercel.app}"
HEALTH_ENDPOINT="${BACKEND_URL}/api/v1/health"
API_ENDPOINT="${BACKEND_URL}/api/v1/sandbox/metrics"
AUTH_ENDPOINT="${BACKEND_URL}/api/v1/auth/login"
CHAT_ENDPOINT="${BACKEND_URL}/api/v1/chat/conversations"

echo "=========================================="
echo "  Goblin Assistant - Deployment Verify"
echo "=========================================="
echo ""

# Phase 1: Backend Health Check
print_status "Checking backend health..."
echo ""

if curl -s -o /dev/null -w "%{http_code}" "${HEALTH_ENDPOINT}" | grep -q "200"; then
    print_success "Backend /api/v1/health endpoint responding (HTTP 200)"
else
    HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${HEALTH_ENDPOINT}")
    if [ "$HEALTH_STATUS" = "000" ]; then
        print_error "Cannot reach backend at ${BACKEND_URL}"
        print_warning "Backend may still be deploying. Check Render dashboard:"
        echo "   → https://dashboard.render.com/services/goblin-backend"
        BACKEND_OK=0
    else
        print_warning "Backend returned HTTP ${HEALTH_STATUS} (expected 200)"
        BACKEND_OK=0
    fi
fi

if [ "${BACKEND_OK:-1}" = "1" ]; then
    print_success "Backend is operational ✓"

    # Try API endpoint
    print_status "Testing API endpoint..."
    API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${API_ENDPOINT}")
    if [ "$API_STATUS" = "200" ]; then
        print_success "API endpoint responding (HTTP 200)"
    else
        print_warning "API endpoint returned HTTP ${API_STATUS}"
    fi

    # Try Auth endpoint
    print_status "Testing Auth endpoint..."
    AUTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${AUTH_ENDPOINT}")
    if [ "$AUTH_STATUS" = "405" ] || [ "$AUTH_STATUS" = "200" ]; then
        print_success "Auth endpoint accessible (HTTP ${AUTH_STATUS})"
    else
        print_warning "Auth endpoint returned HTTP ${AUTH_STATUS}"
    fi

    # Try Chat endpoint (should require auth)
    print_status "Testing Chat endpoint..."
    CHAT_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${CHAT_ENDPOINT}")
    if [ "$CHAT_STATUS" = "401" ]; then
        print_success "Chat endpoint properly protected (HTTP 401 - auth required)"
    elif [ "$CHAT_STATUS" = "200" ]; then
        print_success "Chat endpoint accessible (HTTP 200)"
    else
        print_warning "Chat endpoint returned HTTP ${CHAT_STATUS}"
    fi
fi

echo ""

# Phase 2: Frontend Availability Check
print_status "Checking frontend availability..."
echo ""

FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${FRONTEND_URL}")

if [ "$FRONTEND_STATUS" = "200" ] || [ "$FRONTEND_STATUS" = "301" ] || [ "$FRONTEND_STATUS" = "302" ]; then
    print_success "Frontend responding (HTTP ${FRONTEND_STATUS})"
    print_success "Frontend is operational ✓"
else
    if [ "$FRONTEND_STATUS" = "000" ]; then
        print_error "Cannot reach frontend at ${FRONTEND_URL}"
        print_warning "Frontend may still be deploying. Check Vercel dashboard:"
        echo "   → https://vercel.com/dashboard/projects"
    else
        print_warning "Frontend returned HTTP ${FRONTEND_STATUS}"
    fi
fi

echo ""

# Phase 3: Endpoint Detail Check
print_status "Fetching endpoint details..."
echo ""

print_status "Backend health response:"
curl -s "${HEALTH_ENDPOINT}" | head -20 | sed 's/^/  /'
echo ""

echo ""

# Phase 4: Summary
echo "=========================================="
echo "  Deployment Verification Summary"
echo "=========================================="
echo ""

print_status "Backend URL: ${BACKEND_URL}"
print_status "Frontend URL: ${FRONTEND_URL}"
echo ""

echo "🔗 Quick Links:"
echo "   • Render Backend: https://dashboard.render.com/services/goblin-backend"
echo "   • Vercel Frontend: https://vercel.com/dashboard/projects"
echo "   • Backend Health: ${HEALTH_ENDPOINT}"
echo "   • Auth Endpoint: ${AUTH_ENDPOINT}"
echo "   • Chat Endpoint: ${CHAT_ENDPOINT}"
echo "   • Production Frontend: ${FRONTEND_URL}"
echo "   • Debug Page: ${FRONTEND_URL}/debug/connectivity"
echo ""

echo "✅ Deployment verification complete!"
echo ""

echo "Next Steps:"
echo "  1. If both services show ✓, proceed to smoke testing"
echo "  2. If backend/frontend show ✗, check respective dashboards for build logs"
echo "  3. Run: npm run test:e2e (to run Playwright E2E tests)"
echo ""
