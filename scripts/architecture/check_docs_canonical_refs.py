#!/usr/bin/env python3
"""Fail on stale documentation canonical-path references.

This guard catches the specific documentation drift patterns that surfaced in
the cleanup plan:

- references to a non-existent `backend/docs` tree
- accidental new content under the compatibility-only `docs/adr/` directory
"""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_ROOT = REPO_ROOT / "docs"
COMPAT_ADR_DIR = DOCS_ROOT / "adr"
STALE_REF_MARKERS = ("backend/docs", "./backend/docs", "../backend/docs")


def is_text_doc(path: Path) -> bool:
    return path.suffix.lower() in {".md", ".txt", ".rst"}


def main() -> int:
    violations: list[str] = []

    for path in DOCS_ROOT.rglob("*"):
        if not path.is_file() or not is_text_doc(path):
            continue
        if "archive" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for marker in STALE_REF_MARKERS:
            if marker in text:
                violations.append(f"{path.relative_to(REPO_ROOT)}: stale reference '{marker}'")

    if COMPAT_ADR_DIR.exists():
        for path in COMPAT_ADR_DIR.rglob("*"):
            if path.is_file() and path.name != "README.md":
                violations.append(
                    f"{path.relative_to(REPO_ROOT)}: compatibility ADR directory must only contain README.md"
                )

    if violations:
        print("Documentation canonical-reference check failed:")
        for violation in violations:
            print(f"  - {violation}")
        return 1

    print("Documentation canonical-reference check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
