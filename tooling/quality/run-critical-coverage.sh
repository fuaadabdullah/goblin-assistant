#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON_BIN="${PYTHON:-python3.11}"

run_api_suite() {
  local label="$1"
  shift

  echo "==> Critical path: ${label}"
  (
    cd "$ROOT_DIR/apps/api"
    export PYTHONPATH=src
    "$PYTHON_BIN" -m pytest -o "addopts=" --tb=short -q "$@"
  )
}

run_api_suite "provider routing" \
  src/api/tests/test_request_pipeline_routing.py \
  src/api/tests/test_routing_pipeline.py \
  src/api/tests/provider_dispatcher_authority \
  src/api/tests/provider_dispatcher_routing \
  src/api/tests/test_provider_selection_policy.py \
  src/api/tests/test_provider_quota_service.py

run_api_suite "memory" \
  src/api/tests/test_memory_write_tool.py \
  src/api/tests/test_memory_recall_tool.py \
  src/api/tests/test_memory_core.py \
  src/api/tests/test_memory_contract_robustness.py \
  src/api/tests/test_memory_promotion_embedding.py \
  src/api/tests/test_rag_context_bundle_and_builder.py \
  src/api/tests/test_context_assembly_layers.py

run_api_suite "auth" \
  src/api/tests/test_auth_comprehensive.py \
  src/api/tests/test_auth_refresh.py \
  src/api/tests/test_auth_session_lifecycle.py \
  src/api/tests/test_auth_cookie_config.py \
  src/api/tests/auth_additional_coverage

run_api_suite "sandbox" \
  src/api/tests/test_sandbox_tool.py \
  src/api/tests/test_sandbox_templates.py \
  src/api/tests/test_sandbox_worker_runtime.py \
  src/api/tests/sandbox_api_runtime

run_api_suite "billing" \
  src/api/tests/test_billing_critical_paths.py \
  src/api/tests/test_usage_event_store.py \
  src/api/tests/test_provider_quota_service.py

run_api_suite "orchestration" \
  src/api/tests/test_orchestration_core.py \
  src/api/tests/test_api_router.py \
  src/api/tests/test_parse_router.py \
  src/api/tests/test_context_assembly.py \
  src/api/tests/test_context_assembly_layers.py

echo "==> Critical path suites complete"
