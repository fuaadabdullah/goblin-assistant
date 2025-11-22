#!/bin/bash
# Goblin Assistant Network Testing Script
# Tests streaming reliability across different network conditions

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
API_BASE_URL="${API_BASE_URL:-http://localhost:3001}"
TEST_DURATION="${TEST_DURATION:-300}"  # 5 minutes
CONCURRENT_REQUESTS="${CONCURRENT_REQUESTS:-5}"
LOG_FILE="${LOG_FILE:-/tmp/network-test-$(date +%Y%m%d-%H%M%S).log}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test results
declare -A test_results=(
    ["total_tests"]=0
    ["passed_tests"]=0
    ["failed_tests"]=0
    ["sse_success"]=0
    ["polling_success"]=0
    ["fallback_triggers"]=0
    ["timeout_errors"]=0
    ["connection_errors"]=0
)

log_info() {
    echo -e "$(date '+%Y-%m-%d %H:%M:%S') ${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "$(date '+%Y-%m-%d %H:%M:%S') ${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "$(date '+%Y-%m-%d %H:%M:%S') ${YELLOW}[WARN]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "$(date '+%Y-%m-%d %H:%M:%S') ${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

# Initialize test environment
init_test() {
    log_info "Initializing network testing environment..."
    log_info "API Base URL: $API_BASE_URL"
    log_info "Test Duration: ${TEST_DURATION}s"
    log_info "Concurrent Requests: $CONCURRENT_REQUESTS"
    log_info "Log file: $LOG_FILE"

    # Check if API is accessible
    if ! curl -s -f "$API_BASE_URL/api/health" > /dev/null 2>&1; then
        log_error "API is not accessible at $API_BASE_URL"
        exit 1
    fi

    log_success "Test environment initialized"
}

# Simulate network conditions using tc (traffic control)
setup_network_condition() {
    local condition="$1"
    local interface="${NETWORK_INTERFACE:-eth0}"

    log_info "Setting up network condition: $condition"

    # Reset network conditions
    sudo tc qdisc del dev "$interface" root 2>/dev/null || true

    case "$condition" in
        "corporate_proxy")
            # Simulate corporate proxy with high latency and packet loss
            sudo tc qdisc add dev "$interface" root netem delay 200ms 50ms loss 5% rate 1mbit
            ;;
        "mobile_3g")
            # Simulate 3G mobile network
            sudo tc qdisc add dev "$interface" root netem delay 300ms 100ms loss 2% rate 500kbit
            ;;
        "mobile_4g")
            # Simulate 4G mobile network
            sudo tc qdisc add dev "$interface" root netem delay 100ms 50ms loss 1% rate 10mbit
            ;;
        "satellite")
            # Simulate satellite internet
            sudo tc qdisc add dev "$interface" root netem delay 600ms 200ms loss 3% rate 2mbit
            ;;
        "wifi_unstable")
            # Simulate unstable WiFi
            sudo tc qdisc add dev "$interface" root netem delay 50ms 20ms loss 10% duplicate 1% corrupt 0.1%
            ;;
        "cloudflare")
            # Simulate Cloudflare-like proxy buffering
            sudo tc qdisc add dev "$interface" root netem delay 50ms 10ms
            # Note: Actual Cloudflare simulation would require more complex setup
            ;;
        *)
            log_info "No network condition applied for: $condition"
            ;;
    esac
}

# Reset network conditions
reset_network() {
    local interface="${NETWORK_INTERFACE:-eth0}"
    log_info "Resetting network conditions"
    sudo tc qdisc del dev "$interface" root 2>/dev/null || true
}

# Test streaming with specific network condition
test_streaming_scenario() {
    local scenario="$1"
    local test_payload='{"task_type": "chat", "payload": {"prompt": "Hello, test message for network conditions"}}'

    log_info "Testing scenario: $scenario"

    # Setup network condition
    setup_network_condition "$scenario"

    # Run concurrent streaming tests
    local pids=()
    local results=()

    for ((i=1; i<=CONCURRENT_REQUESTS; i++)); do
        (
            local test_id="$scenario-$i"
            local start_time=$(date +%s.%3N)

            # Test SSE streaming first
            if curl -s -N --max-time 30 -H "Content-Type: application/json" \
                -d "$test_payload" "$API_BASE_URL/api/route_task_stream" \
                2>/dev/null | head -5 | grep -q "event: meta"; then

                local end_time=$(date +%s.%3N)
                local response_time=$(echo "$end_time - $start_time" | bc 2>/dev/null || echo "0")

                echo "SSE_SUCCESS:$test_id:$response_time"
                ((test_results["sse_success"]++))
                return 0
            fi

            # Test polling fallback
            local poll_start=$(date +%s.%3N)
            local poll_response
            if poll_response=$(curl -s --max-time 10 -X POST -H "Content-Type: application/json" \
                -d "$test_payload" "$API_BASE_URL/api/route_task_stream_start" 2>/dev/null); then

                local stream_id=$(echo "$poll_response" | grep -o '"stream_id":"[^"]*"' | cut -d'"' -f4 2>/dev/null || echo "")
                if [[ -n "$stream_id" ]]; then
                    # Poll for results
                    for ((j=1; j<=10; j++)); do
                        sleep 1
                        local poll_result
                        if poll_result=$(curl -s --max-time 5 "$API_BASE_URL/api/route_task_stream_poll?stream_id=$stream_id" 2>/dev/null); then
                            if echo "$poll_result" | grep -q '"done":true'; then
                                local poll_end=$(date +%s.%3N)
                                local poll_time=$(echo "$poll_end - $poll_start" | bc 2>/dev/null || echo "0")
                                echo "POLLING_SUCCESS:$test_id:$poll_time"
                                ((test_results["polling_success"]++))
                                ((test_results["fallback_triggers"]++))
                                return 0
                            fi
                        fi
                    done
                fi
            fi

            # Both methods failed
            echo "FAILED:$test_id:timeout"
            ((test_results["timeout_errors"]++))

        ) &
        pids+=($!)
    done

    # Wait for all tests to complete
    for pid in "${pids[@]}"; do
        if wait "$pid" 2>/dev/null; then
            results+=("$?")
        else
            results+=("FAILED:$scenario:unknown:timeout")
            ((test_results["connection_errors"]++))
        fi
    done

    # Process results
    for result in "${results[@]}"; do
        ((test_results["total_tests"]++))
        if [[ "$result" == SSE_SUCCESS:* ]] || [[ "$result" == POLLING_SUCCESS:* ]]; then
            ((test_results["passed_tests"]++))
            log_success "Test passed: $result"
        else
            ((test_results["failed_tests"]++))
            log_error "Test failed: $result"
        fi
    done

    # Reset network conditions
    reset_network
}

# Run comprehensive network tests
run_network_tests() {
    local scenarios=(
        "normal"           # Baseline test
        "corporate_proxy"  # Corporate environment
        "mobile_3g"        # 3G mobile network
        "mobile_4g"        # 4G mobile network
        "satellite"        # Satellite internet
        "wifi_unstable"    # Unstable WiFi
        "cloudflare"       # Cloudflare-like proxy
    )

    log_info "Starting comprehensive network testing..."

    for scenario in "${scenarios[@]}"; do
        log_info "Running tests for scenario: $scenario"
        test_streaming_scenario "$scenario"
        sleep 5  # Brief pause between scenarios
    done
}

# Generate test report
generate_report() {
    local report_file="/tmp/network-test-report-$(date +%Y%m%d-%H%M%S).json"
    local success_rate=0

    if [[ ${test_results["total_tests"]} -gt 0 ]]; then
        success_rate=$(( test_results["passed_tests"] * 100 / test_results["total_tests"] ))
    fi

    local fallback_rate=0
    if [[ ${test_results["passed_tests"]} -gt 0 ]]; then
        fallback_rate=$(( test_results["polling_success"] * 100 / test_results["passed_tests"] ))
    fi

    cat > "$report_file" << EOF
{
    "timestamp": "$(date -Iseconds)",
    "test_duration_seconds": $TEST_DURATION,
    "concurrent_requests": $CONCURRENT_REQUESTS,
    "results": {
        "total_tests": ${test_results["total_tests"]},
        "passed_tests": ${test_results["passed_tests"]},
        "failed_tests": ${test_results["failed_tests"]},
        "success_rate_percent": $success_rate,
        "sse_success_count": ${test_results["sse_success"]},
        "polling_success_count": ${test_results["polling_success"]},
        "fallback_triggers": ${test_results["fallback_triggers"]},
        "fallback_rate_percent": $fallback_rate,
        "timeout_errors": ${test_results["timeout_errors"]},
        "connection_errors": ${test_results["connection_errors"]}
    },
    "recommendations": [
        $(if [[ $success_rate -lt 80 ]]; then echo '"CRITICAL: Success rate below 80%. Check network configuration."'; fi)
        $(if [[ ${test_results["fallback_triggers"]} -gt ${test_results["sse_success"]} ]]; then echo '"WARNING: High fallback usage. SSE may be blocked by proxies."'; fi)
        $(if [[ ${test_results["timeout_errors"]} -gt 10 ]]; then echo '"ERROR: High timeout rate. Check server response times."'; fi)
    ]
}
EOF

    log_info "Test report generated: $report_file"
    log_info "Success Rate: ${success_rate}%"
    log_info "Fallback Rate: ${fallback_rate}%"
}

# Display test summary
display_summary() {
    echo "========================================"
    echo " Network Testing Summary"
    echo "========================================"
    echo "Total Tests: ${test_results["total_tests"]}"
    echo "Passed: ${test_results["passed_tests"]}"
    echo "Failed: ${test_results["failed_tests"]}"
    echo ""

    local success_rate=0
    if [[ ${test_results["total_tests"]} -gt 0 ]]; then
        success_rate=$(( test_results["passed_tests"] * 100 / test_results["total_tests"] ))
    fi

    echo "📊 Success Rate: ${success_rate}%"

    if [[ $success_rate -ge 90 ]]; then
        echo -e "Status: ${GREEN}EXCELLENT${NC}"
    elif [[ $success_rate -ge 80 ]]; then
        echo -e "Status: ${YELLOW}GOOD${NC}"
    elif [[ $success_rate -ge 70 ]]; then
        echo -e "Status: ${BLUE}FAIR${NC}"
    else
        echo -e "Status: ${RED}POOR${NC}"
    fi

    echo ""
    echo "🔄 Streaming Methods:"
    echo "  SSE Success: ${test_results["sse_success"]}"
    echo "  Polling Success: ${test_results["polling_success"]}"
    echo "  Fallback Triggers: ${test_results["fallback_triggers"]}"
    echo ""
    echo "❌ Error Breakdown:"
    echo "  Timeouts: ${test_results["timeout_errors"]}"
    echo "  Connections: ${test_results["connection_errors"]}"
    echo "========================================"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up network conditions..."
    reset_network
    log_info "Network testing completed"
}

# Main function
main() {
    trap cleanup EXIT

    init_test
    run_network_tests
    generate_report
    display_summary
}

# Show usage
usage() {
    cat << EOF
Goblin Assistant Network Testing Script

Usage: $0 [OPTIONS]

Options:
    -d, --duration SECONDS    Test duration per scenario (default: 300)
    -c, --concurrent NUM      Concurrent requests per test (default: 5)
    -u, --url URL            API base URL (default: http://localhost:3001)
    -i, --interface IFACE    Network interface (default: eth0)
    -l, --log FILE          Log file path
    -h, --help              Show this help message

Environment Variables:
    API_BASE_URL            API base URL
    TEST_DURATION          Test duration in seconds
    CONCURRENT_REQUESTS    Number of concurrent requests
    NETWORK_INTERFACE      Network interface to modify
    LOG_FILE              Log file path

Prerequisites:
    - tc (traffic control) installed and sudo access
    - curl installed
    - bc (calculator) installed

Examples:
    $0 --duration 600 --concurrent 10
    $0 --interface wlan0 --url https://api.goblin-assistant.com

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--duration)
            TEST_DURATION="$2"
            shift 2
            ;;
        -c|--concurrent)
            CONCURRENT_REQUESTS="$2"
            shift 2
            ;;
        -u|--url)
            API_BASE_URL="$2"
            shift 2
            ;;
        -i|--interface)
            NETWORK_INTERFACE="$2"
            shift 2
            ;;
        -l|--log)
            LOG_FILE="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Run main function
main "$@"
