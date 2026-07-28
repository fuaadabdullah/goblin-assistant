#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = (
    REPO_ROOT / "tooling" / "generators" / "generate-provider-confluence-summary.py"
)


def main() -> int:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *sys.argv[1:]],
        check=False,
    )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
