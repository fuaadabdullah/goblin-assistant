#!/usr/bin/env python3
"""Validate that removed docs/runbooks files have a canonical destination."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MAP = REPO_ROOT / "docs" / "operations" / "RUNBOOK_MIGRATION_MAP.md"
MAPPING_PATTERN = re.compile(r"^\|\s*`(?P<old>docs/runbooks/[^`]+)`\s*\|\s*`(?P<new>[^`]+)`\s*\|")


def _deleted_runbooks() -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-status", "--", "docs/runbooks"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git diff failed")
    deleted: list[str] = []
    for line in result.stdout.splitlines():
        status, path = line.split("\t", 1)
        if status == "D" and path != "docs/runbooks/README.md":
            deleted.append(path)
    return sorted(deleted)


def _load_map(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    mappings: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = MAPPING_PATTERN.match(line)
        if match:
            mappings[match.group("old")] = match.group("new")
    return mappings


def validate_map(path: Path = DEFAULT_MAP) -> list[str]:
    failures: list[str] = []
    deleted = _deleted_runbooks()
    mappings = _load_map(path)

    for old_path in deleted:
        new_path = mappings.get(old_path)
        if new_path is None:
            failures.append(f"{old_path}: missing migration-map entry")
            continue
        if new_path != "manual-review" and not (REPO_ROOT / new_path).exists():
            failures.append(f"{old_path}: mapped destination does not exist: {new_path}")

    for old_path in sorted(set(mappings) - set(deleted)):
        failures.append(f"{old_path}: migration-map entry has no deleted runbook")

    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP)
    args = parser.parse_args(argv)

    failures = validate_map(args.map)
    if failures:
        for failure in failures:
            print(failure)
        return 1

    print("Runbook migration map is complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
