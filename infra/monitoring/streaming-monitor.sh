#!/bin/bash
# Goblin Assistant Streaming Monitor
# Monitors streaming performance and fallback usage

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
API_BASE_URL="${API_BASE_URL:-http://localhost:3001}"
MONITOR_INTERVAL="${MONITOR_INTERVAL:-60}"  # seconds
LOG_FILE="${LOG_FILE:-/var/log/goblin-assistant/streaming-monitor.log}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Metrics storage
declare -A metrics=(
    ["total_requests"]=0
    ["streaming_requests"]=0
    ["polling_requests"]=0
    ["fallback_triggers"]=0
    ["connection_failures"]=0
    ["avg_response_time"]=0
    ["last_check_time"]=""
)

log_info() {
    echo -e "$(date '+%Y-%m-%d %H:%M:%S') ${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "$(date '+%Y-%m-%d %H:%M:%S') ${YELLOW}[WARN]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "$(date '+%Y-%m-%d %H:%M:%S') ${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

# Initialize log file
init_logs() {
    mkdir -p "$(dirname "$LOG_FILE")"
    touch "$LOG_FILE"
    log_info "Streaming monitor started"
}

# Health check
check_health() {
    local response
    local http_code

    if ! response=$(curl -s -w "HTTPSTATUS:%{http_code}" "$API_BASE_URL/api/health" 2>/dev/null); then
        log_error "Health check failed - cannot connect to API"
        return 1
    fi

    http_code=$(echo "$response" | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')
    response_body=$(echo "$response" | sed -e 's/HTTPSTATUS:.*//g')

    if [[ "$http_code" -ne 200 ]]; then
        log_error "Health check failed - HTTP $http_code"
        return 1
    fi

    log_info "Health check passed"
    return 0
}

# Get streaming metrics from API
get_streaming_metrics() {
    # This would need to be implemented in the FastAPI app
    # For now, we'll simulate some metrics
    local mock_metrics='{
        "total_requests": 1250,
        "streaming_requests": 980,
        "polling_requests": 270,
        "fallback_triggers": 45,
        "connection_failures": 12,
        "avg_response_time": 1.2
    }'

    echo "$mock_metrics"
}

# Test streaming connection
test_streaming_connection() {
    local test_payload='{"task_type": "chat", "payload": {"prompt": "test"}}'
    local start_time=$(date +%s.%3N)

    # Test SSE streaming
    local sse_response
    if sse_response=$(timeout 10 curl -s -N -H "Content-Type: application/json" \
        -d "$test_payload" "$API_BASE_URL/api/route_task_stream" 2>/dev/null); then

        local end_time=$(date +%s.%3N)
        local response_time=$(echo "$end_time - $start_time" | bc 2>/dev/null || echo "0")

        if echo "$sse_response" | grep -q "event: meta"; then
            log_info "SSE streaming test passed (response time: ${response_time}s)"
            ((metrics["streaming_requests"]++))
            return 0
        else
            log_warn "SSE streaming test failed - no meta event received"
        fi
    else
        log_warn "SSE streaming test failed - connection timeout"
    fi

    # Test polling fallback
    local poll_response
    if poll_response=$(curl -s -X POST -H "Content-Type: application/json" \
        -d "$test_payload" "$API_BASE_URL/api/route_task_stream_start" 2>/dev/null); then

        local stream_id=$(echo "$poll_response" | grep -o '"stream_id":"[^"]*"' | cut -d'"' -f4)
        if [[ -n "$stream_id" ]]; then
            log_info "Polling fallback test passed (stream_id: $stream_id)"
            ((metrics["polling_requests"]++))
            ((metrics["fallback_triggers"]++))
            return 0
        fi
    fi

    log_error "Both SSE and polling tests failed"
    ((metrics["connection_failures"]++))
    return 1
}

# Calculate metrics
calculate_metrics() {
    local api_metrics
    if ! api_metrics=$(get_streaming_metrics); then
        log_warn "Failed to get API metrics"
        return
    fi

    # Parse JSON metrics (simplified - in production use jq)
    metrics["total_requests"]=$(echo "$api_metrics" | grep -o '"total_requests":[0-9]*' | cut -d: -f2)
    metrics["streaming_requests"]=$(echo "$api_metrics" | grep -o '"streaming_requests":[0-9]*' | cut -d: -f2)
    metrics["polling_requests"]=$(echo "$api_metrics" | grep -o '"polling_requests":[0-9]*' | cut -d: -f2)
    metrics["fallback_triggers"]=$(echo "$api_metrics" | grep -o '"fallback_triggers":[0-9]*' | cut -d: -f2)
    metrics["connection_failures"]=$(echo "$api_metrics" | grep -o '"connection_failures":[0-9]*' | cut -d: -f2)
    metrics["avg_response_time"]=$(echo "$api_metrics" | grep -o '"avg_response_time":[0-9.]*' | cut -d: -f2)
}

# Display dashboard
display_dashboard() {
    echo "========================================"
    echo " Goblin Assistant Streaming Monitor"
    echo "========================================"
    echo "Time: $(date)"
    echo ""
    echo "📊 Request Metrics:"
    echo "  Total Requests: ${metrics["total_requests"]}"
    echo "  SSE Streaming:  ${metrics["streaming_requests"]}"
    echo "  Polling Fallback: ${metrics["polling_requests"]}"
    echo ""
    echo "🔄 Fallback Metrics:"
    echo "  Fallback Triggers: ${metrics["fallback_triggers"]}"
    echo "  Connection Failures: ${metrics["connection_failures"]}"
    echo ""
    echo "⚡ Performance:"
    echo "  Avg Response Time: ${metrics["avg_response_time"]}s"
    echo ""
    echo "📈 Health Status:"
    if [[ ${metrics["connection_failures"]} -gt 10 ]]; then
        echo -e "  Status: ${RED}CRITICAL${NC} (High failure rate)"
    elif [[ ${metrics["connection_failures"]} -gt 5 ]]; then
        echo -e "  Status: ${YELLOW}WARNING${NC} (Elevated failures)"
    else
        echo -e "  Status: ${GREEN}HEALTHY${NC}"
    fi

    local fallback_rate=0
    if [[ ${metrics["total_requests"]} -gt 0 ]]; then
        fallback_rate=$(( metrics["polling_requests"] * 100 / metrics["total_requests"] ))
    fi
    echo "  Fallback Rate: ${fallback_rate}%"
    echo "========================================"
}

# Generate report
generate_report() {
    local report_file="/tmp/streaming-report-$(date +%Y%m%d-%H%M%S).json"

    cat > "$report_file" << EOF
{
    "timestamp": "$(date -Iseconds)",
    "metrics": {
        "total_requests": ${metrics["total_requests"]},
        "streaming_requests": ${metrics["streaming_requests"]},
        "polling_requests": ${metrics["polling_requests"]},
        "fallback_triggers": ${metrics["fallback_triggers"]},
        "connection_failures": ${metrics["connection_failures"]},
        "avg_response_time": ${metrics["avg_response_time"]},
        "fallback_rate_percent": $((${metrics["polling_requests"]} * 100 / ${metrics["total_requests"]:-1}))
    },
    "health_status": "$(if [[ ${metrics["connection_failures"]} -gt 10 ]]; then echo "critical"; elif [[ ${metrics["connection_failures"]} -gt 5 ]]; then echo "warning"; else echo "healthy"; fi)"
}
EOF

    log_info "Report generated: $report_file"
}

# Main monitoring loop
main() {
    init_logs

    log_info "Starting streaming monitor (interval: ${MONITOR_INTERVAL}s)"
    log_info "API Base URL: $API_BASE_URL"
    log_info "Log file: $LOG_FILE"

    while true; do
        metrics["last_check_time"]=$(date)

        if check_health; then
            test_streaming_connection
            calculate_metrics
            display_dashboard

            # Generate report every hour
            if [[ $(date +%M) == "00" ]]; then
                generate_report
            fi
        fi

        sleep "$MONITOR_INTERVAL"
    done
}

# Handle signals
trap 'log_info "Streaming monitor stopped"; exit 0' INT TERM

# Show usage
usage() {
    cat << EOF
Goblin Assistant Streaming Monitor

Usage: $0 [OPTIONS]

Options:
    -i, --interval SECONDS    Monitoring interval in seconds (default: 60)
    -u, --url URL            API base URL (default: http://localhost:3001)
    -l, --log FILE          Log file path (default: /var/log/goblin-assistant/streaming-monitor.log)
    -h, --help              Show this help message

Environment Variables:
    API_BASE_URL            API base URL
    MONITOR_INTERVAL        Monitoring interval in seconds
    LOG_FILE               Log file path

Examples:
    $0 --interval 30 --url https://api.goblin-assistant.com
    $0 --log /var/log/streaming-monitor.log

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -i|--interval)
            MONITOR_INTERVAL="$2"
            shift 2
            ;;
        -u|--url)
            API_BASE_URL="$2"
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
