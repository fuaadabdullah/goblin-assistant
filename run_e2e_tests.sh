#!/bin/bash
# Comprehensive E2E Test Runner for Goblin Assistant

echo "🚀 Starting Goblin Assistant E2E Test Suite"
echo "==========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if port is open
check_port() {
    local port=$1
    local service=$2
    if nc -z localhost $port 2>/dev/null; then
        echo -e "${GREEN}✅ $service is running on port $port${NC}"
        return 0
    else
        echo -e "${RED}❌ $service is not responding on port $port${NC}"
        return 1
    fi
}

# Start FastAPI server in background
echo "Starting FastAPI server..."
cd /Users/fuaadabdullah/ForgeMonorepo/goblin-assistant/api/fastapi
PYTHONPATH=/Users/fuaadabdullah/ForgeMonorepo/goblin-assistant/api/fastapi:/Users/fuaadabdullah/ForgeMonorepo/goblin-assistant/api/fastapi/.venv311/lib/python3.11/site-packages \
/Users/fuaadabdullah/ForgeMonorepo/goblin-assistant/api/fastapi/.venv311/bin/python3 -m uvicorn app:app --host 0.0.0.0 --port 3001 &
FASTAPI_PID=$!

# Wait for FastAPI to start
sleep 3

# Check FastAPI
if ! check_port 3001 "FastAPI Backend"; then
    echo -e "${RED}Failed to start FastAPI server${NC}"
    kill $FASTAPI_PID 2>/dev/null
    exit 1
fi

# Start Vite web server in background
echo "Starting Vite web server..."
cd /Users/fuaadabdullah/ForgeMonorepo/goblin-assistant
VITE_MOCK_API=false VITE_FASTAPI_URL=http://127.0.0.1:3001 npx vite --port 1420 --host &
VITE_PID=$!

# Wait for Vite to start
sleep 5

# Check Vite (it might start on a different port if 1420 is in use)
VITE_PORT=1420
if ! check_port $VITE_PORT "Vite Web Server"; then
    # Try port 1421
    VITE_PORT=1421
    if ! check_port $VITE_PORT "Vite Web Server"; then
        # Try port 1422
        VITE_PORT=1422
        if ! check_port $VITE_PORT "Vite Web Server"; then
            echo -e "${RED}Failed to start Vite web server${NC}"
            kill $FASTAPI_PID 2>/dev/null
            exit 1
        fi
    fi
fi

echo -e "${GREEN}✅ Vite Web Server is running on port $VITE_PORT${NC}"

echo ""
echo "🧪 Running E2E Tests..."
echo "======================"

# Run the Python test
cd /Users/fuaadabdullah/ForgeMonorepo/goblin-assistant
VITE_PORT=$VITE_PORT python3 python-tests/test_e2e_simple.py
TEST_RESULT=$?

echo ""
echo "🧹 Cleaning up servers..."
echo "========================="
kill $FASTAPI_PID 2>/dev/null
kill $VITE_PID 2>/dev/null

if [ $TEST_RESULT -eq 0 ]; then
    echo -e "${GREEN}🎉 All E2E tests passed!${NC}"
else
    echo -e "${RED}❌ E2E tests failed${NC}"
fi

exit $TEST_RESULT
