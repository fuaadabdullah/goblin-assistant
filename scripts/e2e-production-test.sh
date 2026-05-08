#!/bin/bash

# Production E2E Testing Script
# Tests critical user journeys on production environment

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}═══════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════${NC}"
}

print_step() {
    echo -e "${YELLOW}📋 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Default to production URLs
BACKEND_URL="${BACKEND_URL:-https://goblin-assistant-backend.onrender.com}"
FRONTEND_URL="${FRONTEND_URL:-https://goblin-assistant.vercel.app}"

print_header "Goblin Assistant - Production E2E Test Suite"

echo ""
echo "Configuration:"
echo "  Backend:  $BACKEND_URL"
echo "  Frontend: $FRONTEND_URL"
echo ""

# Pre-flight checks
print_header "Pre-Flight Checks"

print_step "1. Checking backend health..."
if curl -s -f "${BACKEND_URL}/health" > /dev/null 2>&1; then
    print_success "Backend is responding"
else
    print_error "Backend not responding. Please check dashboard."
    echo "  Render: https://dashboard.render.com/services/goblin-backend"
    exit 1
fi

print_step "2. Checking frontend accessibility..."
if curl -s -f -L "${FRONTEND_URL}" > /dev/null 2>&1; then
    print_success "Frontend is accessible"
else
    print_error "Frontend not accessible. Please check dashboard."
    echo "  Vercel: https://vercel.com/dashboard/projects/goblin-assistant"
    exit 1
fi

print_step "3. Checking Node.js and dependencies..."
if ! command -v node &> /dev/null; then
    print_error "Node.js not found"
    exit 1
fi
print_success "Node.js is installed ($(node --version))"

# Install test dependencies if needed
print_step "4. Installing Playwright if needed..."
if ! npm list @playwright/test > /dev/null 2>&1; then
    npm install --save-dev @playwright/test
fi
print_success "Playwright is ready"

echo ""
print_header "Test Suite Execution"

# Run E2E tests with production URLs
print_step "Running critical path tests..."
echo ""

export PLAYWRIGHT_TEST_BASE_URL="${FRONTEND_URL}"

# Run tests with timeout
if npx playwright test \
    e2e/auth.spec.ts \
    e2e/chat.spec.ts \
    e2e/mobile-drawer.spec.ts \
    --reporter=html \
    --timeout=30000; then
    
    print_success "All E2E tests passed!"
    echo ""
    echo "Test report: playwright-report/index.html"
    
else
    print_error "Some E2E tests failed"
    echo ""
    echo "Troubleshooting:"
    echo "  • Check test report: playwright-report/index.html"
    echo "  • Run locally for debugging: npm run test:e2e"
    echo "  • Check backend logs: https://dashboard.render.com/services/goblin-backend"
    exit 1
fi

echo ""
print_header "Post-Test Verification"

print_step "Collecting deployment summary..."
echo ""
echo "Summary:"
echo "  ✅ Backend health check passed"
echo "  ✅ Frontend accessibility verified"
echo "  ✅ Authentication flow tested"
echo "  ✅ Chat functionality tested"
echo "  ✅ Mobile UX tested"
echo ""
echo "Status: PRODUCTION DEPLOYMENT VERIFIED ✓"
echo ""
echo "Dashboard Links:"
echo "  • Render Backend: https://dashboard.render.com/services/goblin-backend"
echo "  • Vercel Frontend: https://vercel.com/dashboard/projects/goblin-assistant"
echo "  • Production Frontend: ${FRONTEND_URL}"
echo "  • Backend API: ${BACKEND_URL}"
echo ""
echo "Next Steps:"
echo "  1. Monitor error tracking: https://sentry.io"
echo "  2. Check analytics/user activity"
echo "  3. Configure post-deployment alerts (optional)"
echo ""
