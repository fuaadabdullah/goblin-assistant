#!/bin/bash

# Goblin Assistant Migration Cutover Checklist
# Automates health checks and provides cutover guidance

set -e

echo "🧙 Goblin Assistant Migration Cutover Checklist"
echo "=============================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check if flyctl is installed
check_flyctl() {
    if ! command -v fly &> /dev/null; then
        print_error "flyctl not found. Install with: curl -L https://fly.io/install.sh | sh"
        exit 1
    fi
    print_status "flyctl installed"
}

# Check Fly app status
check_fly_app() {
    print_step "Checking Fly app status..."
    if fly status --json > /dev/null 2>&1; then
        FLY_URL=$(fly status --json | jq -r '.Hostname')
        print_status "Fly app running at: https://$FLY_URL"
    else
        print_error "Fly app not accessible"
        exit 1
    fi
}

# Health check
health_check() {
    print_step "Running health checks..."
    if curl -s -f "https://$FLY_URL/health" > /dev/null; then
        print_status "Health endpoint OK"
    else
        print_error "Health check failed"
        exit 1
    fi

    if curl -s -f "https://$FLY_URL/api/health/db" > /dev/null; then
        print_status "Database health OK"
    else
        print_warning "Database health check failed (may be expected during migration)"
    fi
}

# DNS TTL check (manual)
dns_ttl_check() {
    print_step "DNS TTL Check"
    print_warning "Ensure DNS TTL is set to 60s or less for zero-downtime cutover"
    echo "Current DNS records:"
    echo "  - goblin.fuaad.ai → Render (current)"
    echo "  - api.goblin.fuaad.ai → Render (current)"
    echo "Target:"
    echo "  - goblin.fuaad.ai → $FLY_URL"
    echo "  - api.goblin.fuaad.ai → $FLY_URL"
    read -p "Press Enter when DNS TTL is adjusted..."
}

# Cutover steps
cutover() {
    print_step "Cutover Steps"
    echo "1. Update DNS CNAME records:"
    echo "   - goblin.fuaad.ai → $FLY_URL"
    echo "   - api.goblin.fuaad.ai → $FLY_URL"
    echo "2. Wait for DNS propagation (5-10 minutes)"
    echo "3. Test frontend: https://goblin.fuaad.ai"
    echo "4. Monitor logs: fly logs -a goblin-assistant"
    echo "5. If issues, rollback DNS to Render"
    read -p "Press Enter after DNS cutover..."
}

# Post-cutover tests
post_cutover_tests() {
    print_step "Post-cutover tests"
    sleep 30  # Wait for DNS
    if curl -s -f "https://goblin.fuaad.ai/health" > /dev/null; then
        print_status "Frontend health OK"
    else
        print_warning "Frontend health check failed - check DNS propagation"
    fi

    if curl -s -f "https://api.goblin.fuaad.ai/health" > /dev/null; then
        print_status "API health OK"
    else
        print_warning "API health check failed - check DNS propagation"
    fi
}

# Rollback guidance
rollback_guidance() {
    print_step "Rollback Plan"
    echo "If issues occur:"
    echo "1. Revert DNS to Render IPs"
    echo "2. Check Fly logs: fly logs -a goblin-assistant"
    echo "3. Scale down Fly if needed: fly scale count 0"
    echo "4. Investigate and redeploy"
}

# Main
main() {
    check_flyctl
    check_fly_app
    health_check
    dns_ttl_check
    cutover
    post_cutover_tests
    rollback_guidance

    echo ""
    print_status "🎉 Migration cutover checklist completed!"
    echo "Monitor for 24-48 hours before deprovisioning Render resources."
}

main "$@"
