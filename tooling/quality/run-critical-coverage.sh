#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR/apps/api"
export PYTHONPATH=src
PYTHON_BIN="${PYTHON:-python3.11}"

DEFAULT_THRESHOLD="${CRITICAL_COVERAGE_THRESHOLD:-85}"
WEB_CRITICAL_THRESHOLD="${WEB_CRITICAL_THRESHOLD:-80}"

run_gate() {
  local label="$1"
  local cov_target="$2"
  local tests_glob="$3"
  local threshold="${4:-$DEFAULT_THRESHOLD}"
  local coverage_label
  coverage_label="${label//[^a-zA-Z0-9]/_}"

  echo "Running critical coverage gate: $label (threshold ${threshold}%)"
  COVERAGE_FILE="$ROOT_DIR/apps/api/.coverage.${coverage_label}" \
  "$PYTHON_BIN" -m pytest -o "addopts=" -v $tests_glob \
    --cov="$cov_target" \
    --cov-report=term-missing \
    --cov-fail-under="$threshold"
}

run_gate "auth" "src/api/auth" "src/api/tests/test_auth*.py src/api/tests/test_security_config*.py" "${CRIT_AUTH_THRESHOLD:-85}"
echo "Running critical coverage gate: execution-engine (threshold ${CRIT_EXECUTION_THRESHOLD:-85}%)"
COVERAGE_FILE="$ROOT_DIR/apps/api/.coverage.execution_engine" \
"$PYTHON_BIN" -m pytest -o "addopts=" -v \
  src/api/tests/test_executor*.py \
  src/api/tests/test_tool*.py \
  src/api/tests/test_sandbox_templates.py \
  --cov=api.assistant_tools.executor \
  --cov=api.assistant_tools.registry \
  --cov=api.assistant_tools.contracts \
  --cov=api.assistant_tools.sandbox_templates \
  --cov-report=term-missing \
  --cov-fail-under="${CRIT_EXECUTION_THRESHOLD:-85}"
run_gate "sandboxing" "api.sandbox_api" "src/api/tests/test_sandbox*.py src/api/tests/test_sandbox_api_runtime.py" "${CRIT_SANDBOX_THRESHOLD:-85}"
run_gate "risk-logic" "api.services.financial_guardrails" "src/api/tests/test_financial_guardrails.py src/api/tests/test_finance_memory_and_router.py" "${CRIT_RISK_THRESHOLD:-85}"
echo "Running critical coverage gate: persistence (threshold ${CRIT_PERSISTENCE_THRESHOLD:-85}%)"
COVERAGE_FILE="$ROOT_DIR/apps/api/.coverage.persistence" \
"$PYTHON_BIN" -m pytest -o "addopts=" -v \
  src/api/tests/test_db_conn.py \
  src/api/tests/test_task_store.py \
  src/api/tests/test_user_service.py \
  src/api/tests/test_preferences_service.py \
  src/api/tests/test_conversations.py \
  src/api/tests/test_api_keys*.py \
  --cov=api.storage.api_keys \
  --cov=api.storage.preferences_service \
  --cov=api.storage.tasks \
  --cov=api.storage.user_service \
  --cov=api.storage.conversations_pkg.in_memory \
  --cov=api.storage.conversations_pkg.manager \
  --cov=api.storage.conversations_pkg.models \
  --cov=api.storage.models \
  --cov-report=term-missing \
  --cov-fail-under="${CRIT_PERSISTENCE_THRESHOLD:-85}"
run_gate "websocket-state" "api.stream_router" "src/api/tests/test_stream_router.py src/api/tests/test_sse*.py src/api/tests/test_chat_router_core.py" "${CRIT_WEBSOCKET_THRESHOLD:-85}"
run_gate "orchestration" "api.core.orchestration" "src/api/tests/test_context_assembly*.py src/api/tests/test_smart_router_service.py src/api/tests/test_routing_router.py src/api/tests/test_orchestration_core.py" "${CRIT_ORCHESTRATION_THRESHOLD:-85}"
run_gate "api-contracts" "api.api_router" "src/api/tests/test_contract_boundaries.py src/api/tests/test_api_router.py" "${CRIT_CONTRACT_THRESHOLD:-85}"

echo "Running critical coverage gate: provider-routing-rag (threshold ${CRIT_PROVIDER_RAG_THRESHOLD:-75}%)"
COVERAGE_FILE="$ROOT_DIR/apps/api/.coverage.provider_routing_rag" \
"$PYTHON_BIN" -m pytest -o "addopts=" -v \
  src/api/tests/test_provider_dispatcher_authority.py \
  src/api/tests/test_smart_router_service.py \
  src/api/tests/test_context_assembly.py \
  src/api/tests/test_rag_context_bundle_and_builder.py \
  src/api/tests/test_retrieval_by_source.py \
  src/api/tests/test_chat_router_core.py \
  --cov=api.providers.dispatcher \
  --cov=api.services.context_assembly_service.orchestrator \
  --cov=api.services.retrieval_service._context_bundle \
  --cov-report=term-missing \
  --cov-fail-under="${CRIT_PROVIDER_RAG_THRESHOLD:-75}"

cd "$ROOT_DIR"
mkdir -p "$ROOT_DIR/.tmp"
echo "Running critical web consumer + state persistence gates (threshold ${WEB_CRITICAL_THRESHOLD}%)"
TMPDIR="$ROOT_DIR/.tmp" \
VITEST_COVERAGE_INCLUDE='src/api/api-client.ts,src/lib/auth-state.ts' \
WEB_CRITICAL_THRESHOLD="$WEB_CRITICAL_THRESHOLD" \
pnpm --filter @goblin/web exec vitest run --coverage \
  src/api/__tests__/apiClient.contract.test.ts \
  src/lib/__tests__/auth-state.bootstrap.test.ts
