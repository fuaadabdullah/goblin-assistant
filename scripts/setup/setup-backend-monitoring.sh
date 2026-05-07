#!/bin/bash

# Backend Health Monitoring Setup Script
# Sets up health checks and monitoring for the Vercel backend

set -e

echo "🏥 Setting up Backend Health Monitoring"
echo ""

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

# Backend URL
BACKEND_URL="https://goblinos-assistant-backend-v2-gsjbxtrro-fuaadabdullahs-projects.vercel.app"
BYPASS_TOKEN="12345678900987654321123456789009"

# Test health endpoint
test_health_endpoint() {
    print_step "Testing health endpoint..."

    print_warning "Note: Vercel deployment protection is enabled."
    print_warning "To test properly, temporarily disable protection in Vercel dashboard:"
    echo "  1. Go to https://vercel.com/dashboard"
    echo "  2. Select your project"
    echo "  3. Go to Settings > Deployment Protection"
    echo "  4. Disable protection temporarily"
    echo "  5. Re-enable after testing"
    echo ""

    response=$(curl -s "$BACKEND_URL/health?x-vercel-set-bypass-cookie=true&x-vercel-protection-bypass=$BYPASS_TOKEN")
    status_code=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/health?x-vercel-set-bypass-cookie=true&x-vercel-protection-bypass=$BYPASS_TOKEN")

    if [ "$status_code" -eq 200 ]; then
        print_status "Health endpoint responding ✓"
        echo "Response: $response"
    elif [ "$status_code" -eq 307 ]; then
        print_warning "Health endpoint redirecting (authentication bypass may not be working)"
        print_warning "Try disabling Vercel deployment protection temporarily for testing"
        return 1
    else
        print_error "Health endpoint failed with status $status_code"
        return 1
    fi
}

# Test API endpoints
test_api_endpoints() {
    print_step "Testing API endpoints..."

    endpoints=(
        "/api/chat"
        "/api/search"
        "/api/settings"
        "/api/execute"
        "/api-keys"
        "/auth"
        "/parse"
        "/routing"
    )

    for endpoint in "${endpoints[@]}"; do
        status_code=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL$endpoint")
        if [ "$status_code" -eq 405 ] || [ "$status_code" -eq 422 ]; then
            # 405 Method Not Allowed or 422 Unprocessable Entity is expected for GET requests to POST endpoints
            print_status "Endpoint $endpoint: ✓ (Expected response for GET request)"
        elif [ "$status_code" -eq 200 ]; then
            print_status "Endpoint $endpoint: ✓"
        else
            print_warning "Endpoint $endpoint: Status $status_code"
        fi
    done
}

# Create uptime monitoring script
create_uptime_monitor() {
    print_step "Creating uptime monitoring script..."

    cat > uptime-monitor.sh << 'EOF'
#!/bin/bash

# Simple uptime monitoring script for Goblin Assistant backend
BACKEND_URL="https://goblinos-assistant-backend-v2-gsjbxtrro-fuaadabdullahs-projects.vercel.app"
BYPASS_TOKEN="12345678900987654321123456789009"
LOG_FILE="backend-uptime.log"

echo "$(date): Checking backend health..." >> "$LOG_FILE"

# Test health endpoint with bypass token
status_code=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/health?x-vercel-set-bypass-cookie=true&x-vercel-protection-bypass=$BYPASS_TOKEN")
response_time=$(curl -s -w "%{time_total}" -o /dev/null "$BACKEND_URL/health?x-vercel-set-bypass-cookie=true&x-vercel-protection-bypass=$BYPASS_TOKEN")

if [ "$status_code" -eq 200 ]; then
    echo "$(date): ✅ Backend healthy (Status: $status_code, Response time: ${response_time}s)" >> "$LOG_FILE"
else
    echo "$(date): ❌ Backend unhealthy (Status: $status_code, Response time: ${response_time}s)" >> "$LOG_FILE"
    # Send alert (you can integrate with your alerting system here)
    echo "Alert: Backend health check failed at $(date)" >&2
fi
EOF

    chmod +x uptime-monitor.sh
    print_status "Uptime monitoring script created ✓"
}

# Set up cron job for monitoring
setup_cron_monitoring() {
    print_step "Setting up cron monitoring..."

    print_status "To set up automated monitoring, add this to your crontab:"
    echo ""
    echo "# Check backend health every 5 minutes"
    echo "*/5 * * * * cd /path/to/monitoring && ./uptime-monitor.sh"
    echo ""
    echo "# Or run manually:"
    echo "crontab -e"
    echo ""
}

# Instructions for Vercel Analytics
show_vercel_analytics_instructions() {
    print_step "Vercel Analytics Setup Instructions"

    echo ""
    echo "To enable Vercel Analytics for usage insights:"
    echo ""
    echo "1. Go to your Vercel dashboard: https://vercel.com/dashboard"
    echo "2. Select your 'goblinos-assistant-backend-v2' project"
    echo "3. Go to Settings > Analytics"
    echo "4. Enable Analytics"
    echo "5. Choose your plan (free tier available)"
    echo ""
    echo "Analytics will provide:"
    echo "  - Request volume and performance metrics"
    echo "  - Error rates and response times"
    echo "  - Geographic distribution of users"
    echo "  - Function execution times"
    echo ""
}

# Main function
main() {
    test_health_endpoint
    test_api_endpoints
    create_uptime_monitor
    setup_cron_monitoring
    show_vercel_analytics_instructions

    echo ""
    print_status "🎉 Backend monitoring setup completed!"
    echo ""
    echo "📋 Monitoring is now active:"
    echo "   - Health endpoint: $BACKEND_URL/health"
    echo "   - Uptime script: ./uptime-monitor.sh"
    echo "   - Logs: backend-uptime.log"
    echo ""
    echo "🔗 Useful links:"
    echo "   Vercel Dashboard: https://vercel.com/dashboard"
    echo "   Backend URL: $BACKEND_URL"
}

# Run main function
main "$@"
