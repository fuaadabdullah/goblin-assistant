#!/usr/bin/env python3
"""Cross-platform shim for `make test-critical` on Windows.

Replicates tooling/quality/run-critical-coverage.sh without shell
prerequisites so `make test-critical` can be executed directly from
cmd.exe/PowerShell.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
API_DIR = ROOT_DIR / "apps" / "api"
PYTHON_BIN = Path(sys.executable)


def run_api_suite(label: str, paths: list[str]) -> int:
    print(f"==> Critical path: {label}")
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    completed = subprocess.run(
        [PYTHON_BIN, "-m", "pytest", "-o", "addopts=", "--tb=short", "-q"] + paths,
        cwd=API_DIR,
        env=env,
    )
    return completed.returncode


def main() -> int:
    suites: list[tuple[str, list[str]]] = [
        (
            "provider routing",
            [
                "src/api/tests/test_request_pipeline_routing.py",
                "src/api/tests/test_routing_pipeline.py",
                "src/api/tests/provider_dispatcher_authority",
                "src/api/tests/provider_dispatcher_routing",
                "src/api/tests/test_provider_selection_policy.py",
                "src/api/tests/test_provider_quota_service.py",
            ],
        ),
        (
            "memory",
            [
                "src/api/tests/test_memory_write_tool.py",
                "src/api/tests/test_memory_recall_tool.py",
                "src/api/tests/test_memory_core.py",
                "src/api/tests/test_memory_contract_robustness.py",
                "src/api/tests/test_memory_promotion_embedding.py",
                "src/api/tests/test_rag_context_bundle_and_builder.py",
                "src/api/tests/test_context_assembly_layers.py",
            ],
        ),
        (
            "auth",
            [
                "src/api/tests/test_auth_comprehensive.py",
                "src/api/tests/test_auth_refresh.py",
                "src/api/tests/test_auth_session_lifecycle.py",
                "src/api/tests/test_auth_cookie_config.py",
                "src/api/tests/auth_additional_coverage",
            ],
        ),
        (
            "sandbox",
            [
                "src/api/tests/test_sandbox_tool.py",
                "src/api/tests/test_sandbox_templates.py",
                "src/api/tests/test_sandbox_worker_runtime.py",
                "src/api/tests/sandbox_api_runtime",
            ],
        ),
        (
            "billing",
            [
                "src/api/tests/test_billing_critical_paths.py",
                "src/api/tests/test_usage_event_store.py",
                "src/api/tests/test_provider_quota_service.py",
            ],
        ),
        (
            "orchestration",
            [
                "src/api/tests/test_orchestration_core.py",
                "src/api/tests/test_api_router.py",
                "src/api/tests/test_parse_router.py",
                "src/api/tests/test_context_assembly.py",
                "src/api/tests/test_context_assembly_layers.py",
            ],
        ),
    ]

    for label, paths in suites:
        code = run_api_suite(label, paths)
        if code != 0:
            return code

    print("==> Critical path suites complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
