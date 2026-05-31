#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR/apps/api"
export PYTHONPATH=src

DEFAULT_THRESHOLD="${CRITICAL_COVERAGE_THRESHOLD:-85}"
WEB_CRITICAL_THRESHOLD="${WEB_CRITICAL_THRESHOLD:-80}"

run_gate() {
  local label="$1"
  local cov_target="$2"
  local tests_glob="$3"
  local threshold="${4:-$DEFAULT_THRESHOLD}"

  echo "Running critical coverage gate: $label (threshold ${threshold}%)"
  python -m pytest -o "addopts=" -v $tests_glob \
    --cov="$cov_target" \
    --cov-report=term-missing \
    --cov-fail-under="$threshold"
}

run_gate "auth" "src/api/auth" "src/api/tests/test_auth*.py src/api/tests/test_security_config*.py" "${CRIT_AUTH_THRESHOLD:-85}"
run_gate "execution-engine" "src/api/assistant_tools" "src/api/tests/test_executor*.py src/api/tests/test_tool*.py src/api/tests/test_sandbox_templates.py" "${CRIT_EXECUTION_THRESHOLD:-85}"
run_gate "sandboxing" "src/api/sandbox_api.py" "src/api/tests/test_sandbox*.py src/api/tests/test_sandbox_api_runtime.py" "${CRIT_SANDBOX_THRESHOLD:-85}"
run_gate "risk-logic" "src/api/services/financial_guardrails.py" "src/api/tests/test_financial_guardrails.py src/api/tests/test_finance_memory_and_router.py" "${CRIT_RISK_THRESHOLD:-85}"
run_gate "persistence" "src/api/storage" "src/api/tests/test_db_conn.py src/api/tests/test_task_store.py src/api/tests/test_user_service.py src/api/tests/test_preferences_service.py src/api/tests/test_conversations.py src/api/tests/test_api_keys*.py" "${CRIT_PERSISTENCE_THRESHOLD:-85}"
run_gate "websocket-state" "src/api/stream_router.py" "src/api/tests/test_stream_router.py src/api/tests/test_sse*.py src/api/tests/test_chat_router_core.py" "${CRIT_WEBSOCKET_THRESHOLD:-85}"
run_gate "orchestration" "src/api/core/orchestration.py" "src/api/tests/test_context_assembly*.py src/api/tests/test_smart_router_service.py src/api/tests/test_routing_router.py" "${CRIT_ORCHESTRATION_THRESHOLD:-85}"
run_gate "api-contracts" "src/api/api_router.py" "src/api/tests/test_contract_boundaries.py src/api/tests/test_api_router.py" "${CRIT_CONTRACT_THRESHOLD:-85}"

cd "$ROOT_DIR"
mkdir -p "$ROOT_DIR/.tmp"
echo "Running critical web consumer + state persistence gates (threshold ${WEB_CRITICAL_THRESHOLD}%)"
TMPDIR="$ROOT_DIR/.tmp" pnpm --filter @goblin/web exec jest --runInBand --coverage \
  --collectCoverageFrom='src/api/api-client.ts' \
  --collectCoverageFrom='src/store/authStore.ts' \
  --coverageThreshold="{\"global\":{\"lines\":${WEB_CRITICAL_THRESHOLD},\"statements\":${WEB_CRITICAL_THRESHOLD},\"functions\":${WEB_CRITICAL_THRESHOLD},\"branches\":70}}" \
  src/api/__tests__/apiClient.contract.test.ts \
  src/store/__tests__/authStore.bootstrap.test.ts
