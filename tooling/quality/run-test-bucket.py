#!/usr/bin/env python3
"""Execute canonical test bucket manifests from tests/manifests."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFESTS_DIR = ROOT / "tests" / "manifests"


def load_manifest(bucket: str) -> dict:
    path = MANIFESTS_DIR / f"{bucket}.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing manifest: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def run_bucket(bucket: str) -> int:
    manifest = load_manifest(bucket)
    commands = manifest.get("commands", [])
    if not commands:
        print(f"No commands configured for bucket '{bucket}'.")
        return 1

    for command in commands:
        name = command["name"]
        run = command["run"]
        print(f"[tests/{bucket}] {name}")
        completed = subprocess.run(run, cwd=ROOT, shell=True, check=False)
        if completed.returncode != 0:
            return completed.returncode
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a canonical test bucket.")
    parser.add_argument("bucket", choices=("integration", "contract", "performance", "e2e"))
    args = parser.parse_args()
    return run_bucket(args.bucket)


if __name__ == "__main__":
    sys.exit(main())
