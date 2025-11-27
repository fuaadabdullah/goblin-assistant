#!/bin/bash

# Datadog Error Tracking Test Script
# This script helps test the error tracking integration in staging/production

set -e

echo "🧪 Testing Datadog Error Tracking Integration"

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

# Check if environment variables are set
check_env_vars() {
    print_step "Checking Datadog environment variables..."

    if [ -z "$VITE_DD_APPLICATION_ID" ]; then
        print_error "VITE_DD_APPLICATION_ID is not set"
        return 1
    fi

    if [ -z "$VITE_DD_CLIENT_TOKEN" ]; then
        print_error "VITE_DD_CLIENT_TOKEN is not set"
        return 1
    fi

    print_status "Environment variables are configured ✓"
    return 0
}

# Test build with Datadog
test_build() {
    print_step "Testing production build with Datadog..."

    npm run build

    if [ $? -eq 0 ]; then
        print_status "Build completed successfully ✓"
        return 0
    else
        print_error "Build failed!"
        return 1
    fi
}

# Start local server for testing
start_test_server() {
    print_step "Starting test server on port 4173..."

    npm run preview &
    SERVER_PID=$!

    # Wait for server to start
    sleep 3

    # Check if server is running
    if curl -s http://localhost:4173 > /dev/null; then
        print_status "Test server started successfully ✓"
        echo "Server PID: $SERVER_PID"
        return 0
    else
        print_error "Failed to start test server"
        return 1
    fi
}

# Test error tracking by making requests that should generate errors
test_error_tracking() {
    print_step "Testing error tracking (this will generate test errors)..."

    # Test API error (assuming backend is not running)
    curl -s "http://localhost:4173/api/providers" || true

    # Test invalid route
    curl -s "http://localhost:4173/invalid-route" || true

    print_status "Test errors generated. Check Datadog dashboard for logs."
}

# Instructions for manual testing
print_manual_test_instructions() {
    echo ""
    echo "📋 Manual Testing Instructions:"
    echo ""
    echo "1. Open http://localhost:4173 in your browser"
    echo "2. Try these actions to generate errors:"
    echo "   - Click buttons that make API calls"
    echo "   - Try invalid navigation"
    echo "   - Open browser dev tools and run: throw new Error('Test error')"
    echo "3. Check Datadog RUM dashboard for:"
    echo "   - Error events"
    echo "   - User sessions"
    echo "   - Performance metrics"
    echo "4. Check Datadog Logs for:"
    echo "   - Frontend error logs"
    echo "   - API call failures"
    echo "   - Component errors"
    echo ""
}

# Main test function
main() {
    echo "Testing Datadog integration for environment: ${VITE_DD_ENV:-unknown}"
    echo ""

    # Load environment variables
    if [ -f ".env.staging" ]; then
        export $(grep -v '^#' .env.staging | xargs)
    elif [ -f ".env.production" ]; then
        export $(grep -v '^#' .env.production | xargs)
    fi

    check_env_vars || exit 1
    test_build || exit 1
    start_test_server || exit 1

    echo ""
    print_status "🎉 Datadog integration test setup complete!"
    print_manual_test_instructions

    echo "Press Ctrl+C to stop the test server"
    wait $SERVER_PID
}

# Run main function
main "$@"
