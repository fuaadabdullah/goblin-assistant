#!/usr/bin/env bash

# Production E2E Testing Script
# Tests critical user journeys against a deployed frontend URL.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}===========================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}===========================================${NC}"
}

print_step() {
    echo -e "${YELLOW}[*] $1${NC}"
}

print_success() {
    echo -e "${GREEN}[ok] $1${NC}"
}

print_error() {
    echo -e "${RED}[err] $1${NC}"
}

BACKEND_URL="${BACKEND_URL:-https://goblin-backend-dt30.onrender.com}"
FRONTEND_URL="${FRONTEND_URL:-https://goblin-assistant.vercel.app}"
TMPDIR="${TMPDIR:-${ROOT_DIR}/.tmp}"
PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-${ROOT_DIR}/.playwright/browsers}"

mkdir -p "$TMPDIR" "$PLAYWRIGHT_BROWSERS_PATH"

print_header "Goblin Assistant - Production E2E Test Suite"
echo
echo "Configuration:"
echo "  Backend:  ${BACKEND_URL}"
echo "  Frontend: ${FRONTEND_URL}"
echo "  TMPDIR:   ${TMPDIR}"
echo "  Browsers: ${PLAYWRIGHT_BROWSERS_PATH}"
echo

print_header "Pre-Flight Checks"

print_step "1. Checking backend health"
if curl -s -f "${BACKEND_URL}/health" > /dev/null 2>&1; then
    print_success "Backend is responding"
else
    print_error "Backend is not responding"
    exit 1
fi

print_step "2. Checking frontend accessibility"
if curl -s -f -L "${FRONTEND_URL}" > /dev/null 2>&1; then
    print_success "Frontend is accessible"
else
    print_error "Frontend is not accessible"
    exit 1
fi

print_step "3. Checking Node.js and pnpm"
if ! command -v node > /dev/null 2>&1; then
    print_error "Node.js not found"
    exit 1
fi
if ! command -v pnpm > /dev/null 2>&1; then
    print_error "pnpm not found"
    exit 1
fi
print_success "Node.js $(node --version), pnpm $(pnpm --version)"

print_step "4. Ensuring Playwright browsers are provisioned"
TMPDIR="$TMPDIR" PLAYWRIGHT_BROWSERS_PATH="$PLAYWRIGHT_BROWSERS_PATH" \
  pnpm --filter @goblin/web exec playwright install > /dev/null
print_success "Playwright browser provisioning completed"

echo
print_header "Test Suite Execution"
print_step "Running critical production paths"
echo

if PLAYWRIGHT_TEST_BASE_URL="$FRONTEND_URL" \
   TMPDIR="$TMPDIR" \
   PLAYWRIGHT_BROWSERS_PATH="$PLAYWRIGHT_BROWSERS_PATH" \
   pnpm --filter @goblin/web exec playwright test \
      e2e/auth.spec.ts \
      e2e/chat.spec.ts \
      e2e/mobile-drawer.spec.ts \
      --reporter=html \
      --timeout=30000; then
    print_success "All production E2E tests passed"
    echo "Test report: ${ROOT_DIR}/.playwright/html-report/index.html"
else
    print_error "Production E2E tests failed"
    echo "Troubleshooting:"
    echo "  - Check report: ${ROOT_DIR}/.playwright/html-report/index.html"
    echo "  - Run local suite: make test-e2e"
    exit 1
fi

echo
print_header "Post-Test Verification"
echo "Status: PRODUCTION DEPLOYMENT VERIFIED"
echo "Backend: ${BACKEND_URL}"
echo "Frontend: ${FRONTEND_URL}"
