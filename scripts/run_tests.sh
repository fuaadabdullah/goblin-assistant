#!/bin/bash
# Unified Test Runner for Goblin Assistant
# Runs all test suites: unit tests, API tests, E2E tests, and monitoring tests

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FASTAPI_PORT=3001
VITE_PORT=1420
LLAMACPP_PORT=8080

# Test results tracking
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

# Function to print section headers
print_header() {
    echo -e "\n${BLUE}===================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}===================================================${NC}\n"
}

# Function to run a test and track results
run_test() {
    local test_name="$1"
    local test_command="$2"
    local skip_condition="$3"

    echo -e "${YELLOW}🧪 Running: $test_name${NC}"

    # Check skip condition
    if [ -n "$skip_condition" ] && eval "$skip_condition"; then
        echo -e "${YELLOW}⏭️  Skipped: $test_name${NC}"
        ((TESTS_SKIPPED++))
        return 0
    fi

    # Run the test
    if eval "$test_command"; then
        echo -e "${GREEN}✅ Passed: $test_name${NC}"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}❌ Failed: $test_name${NC}"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Function to check if port is open
check_port() {
    local port=$1
    local service=$2
    local timeout=${3:-5}

    echo -n "Checking $service on port $port... "
    if timeout $timeout bash -c "echo >/dev/tcp/localhost/$port" 2>/dev/null; then
        echo -e "${GREEN}✅ Available${NC}"
        return 0
    else
        echo -e "${RED}❌ Not available${NC}"
        return 1
    fi
}

# Function to start FastAPI server
start_fastapi() {
    echo "Starting FastAPI server..."
    cd "$PROJECT_ROOT/api/fastapi"

    # Check if virtual environment exists
    if [ ! -d ".venv311" ]; then
        echo -e "${YELLOW}⚠️  Virtual environment not found, installing dependencies...${NC}"
        python3 -m venv .venv311
        source .venv311/bin/activate
        pip install -r requirements.txt
    else
        source .venv311/bin/activate
    fi

    PYTHONPATH="$PWD:$PWD/.venv311/lib/python3.11/site-packages" \
    python3 -m uvicorn app:app --host 0.0.0.0 --port $FASTAPI_PORT &
    FASTAPI_PID=$!

    # Wait for server to start
    local retries=10
    while [ $retries -gt 0 ]; do
        if check_port $FASTAPI_PORT "FastAPI" 1; then
            echo -e "${GREEN}✅ FastAPI server started successfully${NC}"
            return 0
        fi
        sleep 1
        ((retries--))
    done

    echo -e "${RED}❌ Failed to start FastAPI server${NC}"
    return 1
}

# Function to start Vite dev server
start_vite() {
    echo "Starting Vite dev server..."
    cd "$PROJECT_ROOT"

    VITE_MOCK_API=false VITE_FASTAPI_URL="http://127.0.0.1:$FASTAPI_PORT" \
    npx vite --port $VITE_PORT --host &
    VITE_PID=$!

    # Wait for server to start
    local retries=15
    while [ $retries -gt 0 ]; do
        if check_port $VITE_PORT "Vite" 1; then
            echo -e "${GREEN}✅ Vite dev server started successfully${NC}"
            return 0
        fi
        sleep 1
        ((retries--))
    done

    echo -e "${RED}❌ Failed to start Vite dev server${NC}"
    return 1
}

# Function to cleanup background processes
cleanup() {
    echo -e "\n${YELLOW}🧹 Cleaning up background processes...${NC}"
    kill $FASTAPI_PID 2>/dev/null || true
    kill $VITE_PID 2>/dev/null || true
    wait 2>/dev/null || true
}

# Trap to ensure cleanup on exit
trap cleanup EXIT

# Main test execution
main() {
    print_header "🚀 Goblin Assistant - Unified Test Suite"

    cd "$PROJECT_ROOT"

    # Test 1: Environment and Dependencies
    print_header "1. Environment & Dependencies"

    run_test "Python environment check" \
        "python3 --version && pip --version" ""

    run_test "Node.js environment check" \
        "node --version && npm --version" ""

    run_test "Vault CLI check" \
        "vault --version" \
        "[ -z \"\$VAULT_ADDR\" ] || [ -z \"\$VAULT_TOKEN\" ]"

    run_test "Datadog CLI check" \
        "datadog-agent status >/dev/null 2>&1" \
        "true"  # Skip for now, as agent might not be running

    # Test 2: API Key Validation
    print_header "2. API Key Validation"

    run_test "Python API key test" \
        "cd '$PROJECT_ROOT' && python3 python-tests/test_api_keys.py" ""

    run_test "Node.js API key test" \
        "cd '$PROJECT_ROOT' && node test-api-keys.js" \
        "true"  # Skip - requires Tauri context

    # Test 3: Local LLM Services
    print_header "3. Local LLM Services"

    run_test "Ollama service check" \
        "curl -s http://localhost:11434/api/tags >/dev/null" \
        "true"  # Skip if not running

    run_test "llama.cpp service check" \
        "curl -s http://localhost:$LLAMACPP_PORT/health >/dev/null" \
        "true"  # Skip if not running

    # Test 4: Backend Unit Tests
    print_header "4. Backend Unit Tests"

    run_test "FastAPI unit tests" \
        "cd '$PROJECT_ROOT/api/fastapi' && source .venv311/bin/activate && python3 -m pytest" \
        "[ ! -d '$PROJECT_ROOT/api/fastapi/.venv311' ]"

    # Test 5: Frontend Unit Tests
    print_header "5. Frontend Unit Tests"

    run_test "Vitest unit tests" \
        "cd '$PROJECT_ROOT' && npm test -- --run" ""

    # Test 6: Integration Tests
    print_header "6. Integration Tests"

    run_test "Provider routing test" \
        "cd '$PROJECT_ROOT' && python3 python-tests/test_routing.py" ""

    run_test "Replicate integration test" \
        "cd '$PROJECT_ROOT' && python3 python-tests/test_replicate_direct.py" ""

    run_test "IPC communication test" \
        "cd '$PROJECT_ROOT' && node test-ipc.js" ""

    # Test 7: E2E Tests (requires servers)
    print_header "7. End-to-End Tests"

    # Start servers for E2E tests
    if start_fastapi && start_vite; then
        run_test "Playwright E2E tests" \
            "cd '$PROJECT_ROOT' && npx playwright test" ""

        run_test "Simple E2E test" \
            "cd '$PROJECT_ROOT' && VITE_PORT=$VITE_PORT python3 python-tests/test_e2e_simple.py" ""
    else
        echo -e "${YELLOW}⏭️  Skipping E2E tests - servers failed to start${NC}"
        ((TESTS_SKIPPED++))
    fi

    # Test 8: Monitoring Tests
    print_header "8. Monitoring & Observability"

    run_test "Datadog monitoring test" \
        "cd '$PROJECT_ROOT' && python3 test-monitoring.py" ""

    # Test 9: Model Validation
    print_header "9. Model Validation"

    run_test "Llama model validation" \
        "cd '$PROJECT_ROOT' && python3 scripts/validate_llama_models.py" \
        "[ ! -f '$PROJECT_ROOT/scripts/validate_llama_models.py' ]"

    # Test Summary
    print_header "📊 Test Summary"

    echo -e "${GREEN}✅ Tests Passed: $TESTS_PASSED${NC}"
    echo -e "${RED}❌ Tests Failed: $TESTS_FAILED${NC}"
    echo -e "${YELLOW}⏭️  Tests Skipped: $TESTS_SKIPPED${NC}"

    local total_tests=$((TESTS_PASSED + TESTS_FAILED + TESTS_SKIPPED))
    echo -e "📈 Total Tests: $total_tests"

    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "\n${GREEN}🎉 All tests completed successfully!${NC}"
        exit 0
    else
        echo -e "\n${RED}❌ Some tests failed. Check the output above for details.${NC}"
        exit 1
    fi
}

# Run main function
main "$@"
