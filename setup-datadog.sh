#!/bin/bash
# Datadog Setup Script for Goblin Assistant
# This script helps deploy Datadog monitors and dashboard for the MCP service

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONITORS_DIR="$SCRIPT_DIR/datadog/monitors"
DASHBOARD_FILE="$SCRIPT_DIR/datadog/dashboard.json"

# Check if required tools are available
check_dependencies() {
    if ! command -v curl &> /dev/null; then
        echo -e "${RED}❌ curl is not installed${NC}"
        exit 1
    fi
}

# Check if .env file exists and has required variables
check_env_file() {
    if [ ! -f ".env" ]; then
        echo -e "${RED}❌ .env file not found${NC}"
        echo -e "${YELLOW}Copy .env.example to .env and fill in your Datadog credentials${NC}"
        exit 1
    fi

    if ! grep -q "DD_API_KEY=" .env; then
        echo -e "${RED}❌ DD_API_KEY not found in .env${NC}"
        exit 1
    fi

    if ! grep -q "DD_APP_KEY=" .env; then
        echo -e "${RED}❌ DD_APP_KEY not found in .env${NC}"
        exit 1
    fi
}

# Load environment variables
load_env() {
    set -a
    source .env
    set +a
}

# Create monitors
create_monitors() {
    echo -e "${BLUE}� Creating Datadog monitors...${NC}"

    for monitor_file in "$MONITORS_DIR"/*.json; do
        if [ -f "$monitor_file" ]; then
            monitor_name=$(basename "$monitor_file" .json)
            echo -e "${YELLOW}Creating monitor: $monitor_name${NC}"

            # Create monitor using Datadog API
            response=$(curl -s -X POST "https://api.datadoghq.com/api/v1/monitor" \
                -H "Content-Type: application/json" \
                -H "DD-API-KEY: $DD_API_KEY" \
                -H "DD-APPLICATION-KEY: $DD_APP_KEY" \
                -d @"$monitor_file")

            if echo "$response" | grep -q '"id"'; then
                monitor_id=$(echo "$response" | grep -o '"id":[0-9]*' | cut -d':' -f2)
                echo -e "${GREEN}✅ Created monitor: $monitor_name (ID: $monitor_id)${NC}"
            else
                echo -e "${RED}❌ Failed to create monitor: $monitor_name${NC}"
                echo -e "${RED}Response: $response${NC}"
            fi
        fi
    done
}

# Create dashboard
create_dashboard() {
    echo -e "${BLUE}📈 Creating Datadog dashboard...${NC}"

    if [ ! -f "$DASHBOARD_FILE" ]; then
        echo -e "${RED}❌ Dashboard file not found: $DASHBOARD_FILE${NC}"
        return 1
    fi

    response=$(curl -s -X POST "https://api.datadoghq.com/api/v1/dashboard" \
        -H "Content-Type: application/json" \
        -H "DD-API-KEY: $DD_API_KEY" \
        -H "DD-APPLICATION-KEY: $DD_APP_KEY" \
        -d @"$DASHBOARD_FILE")

    if echo "$response" | grep -q '"id"'; then
        dashboard_id=$(echo "$response" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
        echo -e "${GREEN}✅ Created dashboard: Goblin Assistant - Production Monitoring${NC}"
        echo -e "${GREEN}Dashboard URL: https://app.datadoghq.com/dashboard/$dashboard_id${NC}"
    else
        echo -e "${RED}❌ Failed to create dashboard${NC}"
        echo -e "${RED}Response: $response${NC}"
    fi
}

# Test Datadog connection
test_connection() {
    echo -e "${BLUE}� Testing Datadog connection...${NC}"

    response=$(curl -s "https://api.datadoghq.com/api/v1/validate" \
        -H "DD-API-KEY: $DD_API_KEY" \
        -H "DD-APPLICATION-KEY: $DD_APP_KEY")

    if echo "$response" | grep -q '"valid":true'; then
        echo -e "${GREEN}✅ Datadog API connection successful${NC}"
    else
        echo -e "${RED}❌ Datadog API connection failed${NC}"
        echo -e "${RED}Response: $response${NC}"
        exit 1
    fi
}

# Main execution
main() {
    echo -e "${BLUE}� Setting up Datadog monitoring for Goblin Assistant${NC}"
    echo

    check_dependencies
    check_env_file
    load_env
    test_connection

    echo
    read -p "Do you want to create monitors? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        create_monitors
    fi

    echo
    read -p "Do you want to create the dashboard? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        create_dashboard
    fi

    echo
    echo -e "${GREEN}🎉 Datadog setup complete!${NC}"
    echo
    echo -e "${YELLOW}Next steps:${NC}"
    echo -e "1. Start your services: docker-compose up -d"
    echo -e "2. Check the admin dashboard: http://localhost/mcp/v1/admin/dashboard"
    echo -e "3. Monitor metrics in Datadog: https://app.datadoghq.com/"
    echo
    echo -e "${YELLOW}Monitor these KPIs:${NC}"
    echo -e "• P95 Latency: < 1.5s"
    echo -e "• Error Rate: < 3%"
    echo -e "• RAG Hit Rate: > 60%"
    echo -e "• Fallback Rate: < 5%"
    echo -e "• Queue Depth: < 50"
    echo -e "• Daily Cost: < $50"
}

# Run main function
main "$@"
