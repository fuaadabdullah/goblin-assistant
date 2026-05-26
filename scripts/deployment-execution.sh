#!/bin/bash

# Goblin Assistant v0.2.0 - Production Deployment Execution Timeline
# Use this script to execute all deployment verification steps

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

print_banner() {
    echo -e "${CYAN}"
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║  Goblin Assistant v0.2.0 - Production Deployment Execution    ║"
    echo "║  Status: Phase 2 - Monitoring & Verification                 ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_step() {
    echo -e "${YELLOW}>>> $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_section() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# ==================== MAIN EXECUTION ====================

print_banner

print_section "STEP 1: Current Deployment Status"

print_step "Checking deployment progress..."
echo ""

bash scripts/quick-verify-deployment.sh

print_section "STEP 2: Key Resources"

print_info "Open these in your browser and monitor:"
echo ""
echo "  🔴 Render Backend (Watch for 'Live' status):"
echo "     https://dashboard.render.com/services/goblin-backend"
echo ""
echo "  🟦 Vercel Frontend (Watch for green checkmark):"
echo "     https://vercel.com/dashboard/projects/goblin-assistant"
echo ""
echo "  📊 Error Tracking (Monitor for issues):"
echo "     https://sentry.io/organizations/goblin/"
echo ""

print_section "STEP 3: What To Do Now"

print_info "Phase 1: Wait for Services (T+0 to T+5 minutes)"
echo ""
echo "  ⏳ Monitor the dashboards above"
echo "  ⏳ Watch for status changes to 'Live'"
echo "  ⏳ Check Sentry for any startup errors"
echo ""

print_info "Phase 2: Quick Health Check (Once both are Live)"
echo ""
echo "  Commands to run:"
echo ""
echo "  # Test backend health"
echo "  curl https://goblin-backend-dt30.onrender.com/health"
echo ""
echo "  # Test frontend accessibility"
echo "  curl -I https://goblin-assistant.vercel.app"
echo ""
echo "  # Run quick verify again"
echo "  bash scripts/quick-verify-deployment.sh"
echo ""

print_info "Phase 3: Full E2E Testing (Once health checks pass)"
echo ""
echo "  bash scripts/e2e-production-test.sh"
echo ""

print_section "STEP 4: Deployment Checklist"

echo "Code Level:"
echo "  [x] Frontend ESLint validation passed"
echo "  [x] Frontend TypeScript type-check passed"
echo "  [x] Frontend Next.js build successful"
echo "  [x] Backend tests passed"
echo "  [x] Version bumped to v0.2.0"
echo ""

echo "Git Level:"
echo "  [x] 34 files committed with changelog"
echo "  [x] Merged fix/remove-embedded-secrets → main"
echo "  [x] Pushed main → origin/main"
echo "  [x] GitHub commit: 3922f3e"
echo ""

echo "Deployment Level:"
echo "  [ ] Render backend shows 'Live'"
echo "  [ ] Vercel frontend shows green checkmark"
echo "  [ ] Backend /health returns 200"
echo "  [ ] Frontend homepage loads"
echo "  [ ] E2E tests pass"
echo ""

print_section "STEP 5: Troubleshooting Quick Reference"

echo "If Backend Build Fails:"
echo "  1. Check Render dashboard Logs tab"
echo "  2. Common issues: Missing env vars, Docker build error"
echo "  3. Solution: Set DATABASE_URL, REDIS_URL, SENTRY_DSN in Render"
echo ""

echo "If Frontend Build Fails:"
echo "  1. Check Vercel deployment logs"
echo "  2. Common issues: TypeScript error, missing env var"
echo "  3. Solution: Run 'npm run build' locally to reproduce"
echo ""

echo "If Services Live but Getting 503:"
echo "  1. Check service logs in respective dashboards"
echo "  2. Likely: Database or Redis connection issue"
echo "  3. Verify connection strings are correct"
echo ""

print_section "STEP 6: Success Indicators"

echo "Deployment is successful when:"
echo "  ✓ Backend service shows 'Live' on Render"
echo "  ✓ Frontend shows green checkmark on Vercel"
echo "  ✓ curl https://goblin-backend-dt30.onrender.com/health = 200"
echo "  ✓ https://goblin-assistant.vercel.app loads cleanly"
echo "  ✓ Browser console shows no critical errors"
echo "  ✓ All E2E tests pass"
echo "  ✓ No new critical errors in Sentry"
echo ""

print_section "STEP 7: Post-Deployment Actions"

echo "Once deployment is verified:"
echo "  1. ✓ Monitor error tracking for 24 hours"
echo "  2. ✓ Check user activity in analytics"
echo "  3. ✓ Review performance metrics (response times, build size)"
echo "  4. ✓ Test critical user journeys in production"
echo "  5. ✓ Update status page if one exists"
echo "  6. ✓ Notify stakeholders of successful deployment"
echo ""

print_section "STEP 8: Important Notes"

echo "Timeline Expected:"
echo "  • Current: Code deployed, auto-build triggered"
echo "  • +2-3m: Services should show 'Live'"
echo "  • +5m: Ready for health checks"
echo "  • +10m: E2E tests can start"
echo "  • +15m: Deployment complete & verified"
echo ""

echo "Environment Configuration:"
echo "  • All required env vars should be in service dashboards"
echo "  • Backend: DATABASE_URL, REDIS_URL, SENTRY_DSN, API keys"
echo "  • Frontend: NEXT_PUBLIC_API_BASE_URL (points to Render backend)"
echo ""

echo "Rollback Procedure (if needed):"
echo "  1. Render: Select previous Deploy from history"
echo "  2. Vercel: Click previous deployment → 'Promote to Production'"
echo "  3. Time to rollback: ~1-2 minutes"
echo ""

print_section "NEXT COMMAND TO RUN"

echo -e "${CYAN}Once services show 'Live' on dashboards:${NC}"
echo ""
echo -e "  ${GREEN}bash scripts/e2e-production-test.sh${NC}"
echo ""
echo -e "Or re-run this status check anytime:"
echo ""
echo -e "  ${GREEN}bash scripts/quick-verify-deployment.sh${NC}"
echo ""

print_banner

echo -e "${GREEN}📋 Deployment script execution complete!${NC}"
echo ""
echo "Dashboard Links:"
echo "  • Render:  https://dashboard.render.com/services/goblin-backend"
echo "  • Vercel:  https://vercel.com/dashboard/projects/goblin-assistant"
echo "  • Sentry:  https://sentry.io/organizations/goblin/"
echo ""
