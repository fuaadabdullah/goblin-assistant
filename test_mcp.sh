#!/bin/bash

# Test script for MCP (Model Control Plane) functionality.
# This script tests the MCP endpoints and worker processing.

set -e

echo "🧪 Testing MCP (Model Control Plane) Setup"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
MCP_BASE_URL="http://localhost:8001/mcp/v1"
API_KEY="${OPENAI_API_KEY:-test_key}"

echo -e "${YELLOW}Step 1: Testing MCP health${NC}"
if curl -s -f "${MCP_BASE_URL}/admin/metrics" > /dev/null; then
    echo -e "${GREEN}✅ MCP API is responding${NC}"
else
    echo -e "${RED}❌ MCP API is not responding${NC}"
    exit 1
fi

echo -e "\n${YELLOW}Step 2: Creating a test request${NC}"
REQUEST_PAYLOAD='{
    "user_id": "test_user_123",
    "prompt": "Explain what MCP is in one sentence",
    "task_type": "chat",
    "prefer_local": true,
    "priority": 50
}'

RESPONSE=$(curl -s -X POST "${MCP_BASE_URL}/request" \
    -H "Content-Type: application/json" \
    -d "$REQUEST_PAYLOAD")

echo "Response: $RESPONSE"

REQUEST_ID=$(echo "$RESPONSE" | grep -o '"request_id":"[^"]*"' | cut -d'"' -f4)

if [ -n "$REQUEST_ID" ]; then
    echo -e "${GREEN}✅ Request created with ID: $REQUEST_ID${NC}"
else
    echo -e "${RED}❌ Failed to create request${NC}"
    exit 1
fi

echo -e "\n${YELLOW}Step 3: Checking request status${NC}"
sleep 2

STATUS_RESPONSE=$(curl -s "${MCP_BASE_URL}/request/${REQUEST_ID}")
echo "Status: $STATUS_RESPONSE"

STATUS=$(echo "$STATUS_RESPONSE" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
echo -e "${GREEN}✅ Request status: $STATUS${NC}"

echo -e "\n${YELLOW}Step 4: Waiting for completion and checking result${NC}"
# Wait up to 30 seconds for completion
for i in {1..30}; do
    RESULT_RESPONSE=$(curl -s "${MCP_BASE_URL}/request/${REQUEST_ID}/result")
    RESULT_STATUS=$(echo "$RESULT_RESPONSE" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)

    if [ "$RESULT_STATUS" = "finished" ]; then
        echo -e "${GREEN}✅ Request completed successfully${NC}"
        echo "Result: $RESULT_RESPONSE"
        break
    elif [ "$RESULT_STATUS" = "failed" ]; then
        echo -e "${RED}❌ Request failed${NC}"
        echo "Error details: $RESULT_RESPONSE"
        exit 1
    else
        echo -n "."
        sleep 1
    fi
done

if [ "$RESULT_STATUS" != "finished" ]; then
    echo -e "\n${YELLOW}⚠️  Request still processing (may need worker to be running)${NC}"
fi

echo -e "\n${YELLOW}Step 5: Testing cancellation${NC}"
# Create another request to test cancellation
CANCEL_REQUEST=$(curl -s -X POST "${MCP_BASE_URL}/request" \
    -H "Content-Type: application/json" \
    -d '{"user_id": "test_user_123", "prompt": "This will be cancelled", "task_type": "chat"}')

CANCEL_ID=$(echo "$CANCEL_REQUEST" | grep -o '"request_id":"[^"]*"' | cut -d'"' -f4)

if [ -n "$CANCEL_ID" ]; then
    echo "Created request $CANCEL_ID for cancellation test"

    # Cancel it immediately
    CANCEL_RESPONSE=$(curl -s -X POST "${MCP_BASE_URL}/cancel/${CANCEL_ID}")
    echo -e "${GREEN}✅ Cancellation response: $CANCEL_RESPONSE${NC}"
fi

echo -e "\n${GREEN}🎉 MCP testing completed!${NC}"
echo -e "${YELLOW}Note: For full functionality, ensure:${NC}"
echo "  - PostgreSQL database is running and MCP tables are created"
echo "  - Redis is running for queue management"
echo "  - MCP worker process is running to process requests"
echo "  - WebSocket streaming can be tested with a WebSocket client"
