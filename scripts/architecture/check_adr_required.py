#!/usr/bin/env python3
"""Require ADR updates for architecture-impacting changes in pull requests."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List


REPO_ROOT = Path(__file__).resolve().parents[2]
ADR_PREFIX = "docs/decisions/"
ADR_FILE_SUFFIX = ".md"

ARCHITECTURE_IMPACT_PREFIXES = (
    "apps/api/src/api/providers/",
    "apps/api/src/api/core/contracts.py",
    "apps/api/src/api/core/route_lifecycle.py",
    "scripts/architecture/check_capability_boundaries.py",
    "apps/api/architecture-capabilities.json",
)


def run_git(args: List[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def changed_files(base_ref: str) -> List[str]:
    merge_base = run_git(["merge-base", base_ref, "HEAD"])
    diff = run_git(["diff", "--name-only", f"{merge_base}...HEAD"])
    return [line.strip() for line in diff.splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-ref", required=True)
    args = parser.parse_args()

    try:
        changed = changed_files(args.base_ref)
    except subprocess.CalledProcessError as exc:
        print(f"Failed to compute changed files: {exc}", file=sys.stderr)
        return 2

    impacts_arch = any(
        any(path.startswith(prefix) for prefix in ARCHITECTURE_IMPACT_PREFIXES)
        for path in changed
    )
    if not impacts_arch:
        print("No architecture-impacting files changed; ADR requirement skipped.")
        return 0

    has_adr = any(
        path.startswith(ADR_PREFIX) and path.endswith(ADR_FILE_SUFFIX)
        for path in changed
    )
    if has_adr:
        print("ADR requirement satisfied.")
        return 0

    print(
        "Architecture changes detected without ADR update in docs/decisions/*.md",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
