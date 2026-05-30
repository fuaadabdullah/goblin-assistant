#!/usr/bin/env python3
"""Enforce canonical placement for tooling and script wrappers."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

ALLOWED_SCRIPT_PREFIXES = (
    "scripts/ops/",
    "scripts/deploy/",
    "scripts/setup/",
    "scripts/config/",
    "scripts/architecture/",
    "scripts/tests/",
)

ALLOWED_SCRIPT_WRAPPERS = {
    "scripts/check-e2e-budget.sh",
    "scripts/check-contrast.js",
    "scripts/ci-policy-check.sh",
    "scripts/generate-providers-json.py",
    "scripts/generate-theme-css.js",
    "scripts/guard-no-client-v1.js",
    "scripts/guard-no-inline-styles.js",
    "scripts/quality-metrics.js",
    "scripts/run-critical-coverage.sh",
    "scripts/run-test-bucket.py",
}

ALLOWED_SCRIPT_FILES = {
    "scripts/DEPLOYMENT_SCRIPTS_README.md",
    "scripts/cleanup_backend.py",
    "scripts/deployment-execution.sh",
    "scripts/e2e-production-test.sh",
    "scripts/load-storage-env.sh",
    "scripts/load-test.py",
    "scripts/load_env.sh",
    "scripts/policy_guard.py",
    "scripts/quick-verify-deployment.sh",
    "scripts/run-full-deployment-setup.sh",
    "scripts/setup_bitwarden.sh",
    "scripts/setup-circleci.sh",
    "scripts/setup-ci-cd.sh",
    "scripts/setup-deployment-credentials.sh",
    "scripts/setup-external-storage.sh",
    "scripts/setup-github-secrets.sh",
    "scripts/setup-supabase-from-bw.sh",
    "scripts/setup.js",
    "scripts/setup_ssh_key.sh",
    "scripts/simple-test.py",
    "scripts/test-theme-runtime.html",
    "scripts/test_database.py",
    "scripts/test_vault.sh",
    "scripts/validate-env.ts",
    "scripts/validate-production-env.py",
    "scripts/validate_database_config.py",
    "scripts/validate_privacy_integration.py",
    "scripts/verify-a11y.js",
    "scripts/verify-cicd-setup.sh",
    "scripts/verify-deployment.sh",
    "scripts/verify-logo-optimization.js",
    "scripts/verify-theme-system.js",
}


def changed_paths(revision_range: str) -> list[str]:
    cmd = ["git", "diff", "--name-only", "--diff-filter=AM", revision_range]
    result = subprocess.run(cmd, cwd=ROOT, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"git diff failed for range {revision_range}: {result.stderr.strip()}")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def is_allowed_script_path(path: str) -> bool:
    if path in ALLOWED_SCRIPT_WRAPPERS or path in ALLOWED_SCRIPT_FILES:
        return True
    return any(path.startswith(prefix) for prefix in ALLOWED_SCRIPT_PREFIXES)


def check_structure(revision_range: str) -> tuple[list[str], list[str]]:
    violations: list[str] = []
    notices: list[str] = []

    for rel_path in changed_paths(revision_range):
        if rel_path.startswith("scripts/") and not is_allowed_script_path(rel_path):
            violations.append(
                f"{rel_path}: new non-runtime script path is not allowed in scripts/. "
                "Place non-runtime utilities under tooling/{codemods,generators,automation,quality}."
            )
        if rel_path.startswith("tooling/"):
            notices.append(rel_path)

    return violations, notices


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate script/tooling structure policy.")
    parser.add_argument("--range", default="HEAD~1..HEAD", help="Git revision range to inspect.")
    args = parser.parse_args()

    violations, notices = check_structure(args.range)
    if notices:
        print(f"[structure-policy] tooling changes detected: {len(notices)}")
    if violations:
        print("[structure-policy] violations:")
        for item in violations:
            print(f"  - {item}")
        return 1
    print("[structure-policy] passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
