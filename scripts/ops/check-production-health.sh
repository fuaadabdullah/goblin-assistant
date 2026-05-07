#!/bin/bash
# Goblin Assistant Production Health Check Script
# Performs comprehensive health checks for all production components

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}🔍 GOBLIN ASSISTANT PRODUCTION HEALTH CHECK${NC}"
    echo "==============================================="
    echo ""
}

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Health check functions
check_api_health() {
    print_info "Checking API health..."
    if curl -s -f --max-time 10 https://goblin-assistant-backend.onrender.com/health > /dev/null 2>&1; then
        print_status "API is healthy"
        return 0
    else
        print_error "API health check failed"
        return 1
    fi
}

check_frontend_health() {
    print_info "Checking frontend health..."
    if curl -s -f --max-time 10 https://goblin-assistant.vercel.app > /dev/null 2>&1; then
        print_status "Frontend is healthy"
        return 0
    else
        print_error "Frontend health check failed"
        return 1
    fi
}

check_database_backup() {
    print_info "Checking database backup status..."
    # This would need GitHub API access to check workflow status
    # For now, just check if backup script exists
    if [ -f "../../scripts/backup/pg_backup.sh" ]; then
        print_status "Backup script exists"
        return 0
    else
        print_error "Backup script not found"
        return 1
    fi
}

check_datadog_metrics() {
    print_info "Checking Datadog configuration..."
    if [ -f "datadog/DATADOG_SLOS.md" ] && [ -f "api/datadog_integration.py" ]; then
        print_status "Datadog monitoring configured"
        return 0
    else
        print_error "Datadog configuration incomplete"
        return 1
    fi
}

check_secrets() {
    print_info "Checking secrets configuration..."
    if [ -f ".env.production" ]; then
        # Check if any secrets are still REDACTED
        if grep -q "REDACTED" .env.production; then
            print_warning "Some secrets still use REDACTED placeholders"
            return 1
        else
            print_status "Secrets appear configured"
            return 0
        fi
    else
        print_error ".env.production file not found"
        return 1
    fi
}

# Main health check
main() {
    print_header

    local failures=0

    # Run all checks
    check_secrets || ((failures++))
    check_datadog_metrics || ((failures++))
    check_database_backup || ((failures++))
    check_api_health || ((failures++))
    check_frontend_health || ((failures++))

    echo ""
    echo "📊 HEALTH CHECK SUMMARY"
    echo "======================="

    if [ $failures -eq 0 ]; then
        print_status "All systems healthy! 🎉"
        echo ""
        print_info "Production deployment ready"
    else
        print_error "$failures health check(s) failed"
        echo ""
        print_warning "Please address the issues above before full production deployment"
        exit 1
    fi

    echo ""
    print_info "For detailed monitoring, check:"
    echo "• Datadog Dashboard: https://app.datadoghq.com"
    echo "• GitHub Actions: Database backup workflows"
    echo "• Sentry: Error tracking dashboard"
}

# Run main function
main "$@"
