#!/usr/bin/env python3
"""Run blocking mypy + pyright only for changed API files in a PR.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List

REPO_ROOT = Path(__file__).resolve().parents[2]


def run_git(args: List[str]) -> str:
    result = subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def changed_api_files(base_ref: str) -> List[str]:
    merge_base = run_git(["merge-base", base_ref, "HEAD"])
    diff = run_git(["diff", "--name-only", f"{merge_base}...HEAD"])
    out: List[str] = []
    for file in diff.splitlines():
        if not file.endswith(".py"):
            continue
        if not file.startswith("apps/api/src/api/"):
            continue
        if "/tests/" in file:
            continue
        out.append(file)
    return sorted(set(out))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-ref", required=True)
    args = parser.parse_args()

    try:
        changed = changed_api_files(args.base_ref)
    except subprocess.CalledProcessError as exc:
        print(f"Failed to compute changed files: {exc}", file=sys.stderr)
        return 2

    if not changed:
        print("No changed API Python files to type-check.")
        return 0

    rel_files = [str(Path(f).relative_to("apps/api")) for f in changed]

    mypy_cmd = [
        "python",
        "-m",
        "mypy",
        "--config-file",
        "pyproject.toml",
        *rel_files,
    ]
    pyright_cmd = ["python", "-m", "pyright", *rel_files]

    print("Running mypy on changed files...")
    mypy = subprocess.run(mypy_cmd, cwd=REPO_ROOT / "apps/api")
    if mypy.returncode != 0:
        return mypy.returncode

    print("Running pyright on changed files...")
    pyright = subprocess.run(pyright_cmd, cwd=REPO_ROOT / "apps/api")
    return pyright.returncode


if __name__ == "__main__":
    raise SystemExit(main())
