#!/usr/bin/env python3
"""Policy guard for pure-by-default side effects and naming intent."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


PURE_ZONE_PATTERNS = (
    "apps/api/src/api/core/**/*.py",
    "apps/api/src/api/services/**/*.py",
    "apps/web/src/utils/**/*.{ts,tsx,js,jsx}",
    "apps/web/src/lib/**/*.{ts,tsx,js,jsx}",
)

PURE_ZONE_EXCLUDES = (
    "apps/api/src/api/services/*integration*.py",
    "apps/api/src/api/services/*storage*.py",
    "apps/api/src/api/services/**/*adapter*.py",
    "apps/web/src/lib/api/**/*",
)

SIDE_EFFECT_RULES = (
    ("global-mutation", re.compile(r"^\s*global\s+\w+", re.MULTILINE), "Global mutation in pure zone."),
    ("file-write", re.compile(r"\bopen\s*\([^)]*,\s*[\"'](?:w|a|x|wb|ab|xb)[\"']"), "File write in pure zone."),
    ("http-call", re.compile(r"\b(httpx|requests)\.(get|post|put|patch|delete)\s*\(|\bfetch\s*\("), "External API call in pure zone."),
    ("env-mutation", re.compile(r"\bos\.environ\s*\[|process\.env\.[A-Za-z_]\w*\s*="), "Environment mutation in pure zone."),
)

NAME_RULES = (
    ("ambiguous-variable", re.compile(r"\b(?:const|let|var)\s+(data|temp|helper|manager)\b"), "Ambiguous variable name; use intent-focused names."),
    ("ambiguous-python-name", re.compile(r"^\s*(data|temp|helper|manager)\s*=", re.MULTILINE), "Ambiguous variable name; use intent-focused names."),
    ("generic-process-fn", re.compile(r"\bfunction\s+process\s*\(|\bdef\s+process\s*\("), "Generic process() name; use a specific verb."),
)


@dataclass
class Violation:
    path: Path
    line: int
    rule: str
    message: str
    sample: str


def git_changed_files(base_ref: str) -> list[Path]:
    cmd = ["git", "diff", "--name-only", f"{base_ref}...HEAD"]
    result = subprocess.run(cmd, cwd=ROOT, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        return []
    return [ROOT / p for p in result.stdout.splitlines() if p.strip()]


def pure_zone_files() -> list[Path]:
    matches: set[Path] = set()
    for pattern in PURE_ZONE_PATTERNS:
        matches.update(ROOT.glob(pattern))
    exclude_set: set[Path] = set()
    for pattern in PURE_ZONE_EXCLUDES:
        exclude_set.update(ROOT.glob(pattern))
    return sorted(p for p in matches if p.is_file() and p not in exclude_set)


def pure_zone_file_set() -> set[Path]:
    return set(pure_zone_files())


def relevant_files(changed_only: bool, base_ref: str) -> list[Path]:
    if changed_only:
        changed = git_changed_files(base_ref)
        if changed:
            return [p for p in changed if p.is_file()]
    files: list[Path] = []
    files.extend(pure_zone_files())
    files.extend(ROOT.glob("apps/web/src/**/*.{ts,tsx,js,jsx}"))
    files.extend(ROOT.glob("apps/api/src/api/**/*.py"))
    return sorted({p for p in files if p.is_file()})


def line_for_offset(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def in_pure_zone(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    return path in pure_zone_file_set() and "tests/" not in rel


def scan_file(path: Path) -> list[Violation]:
    rel = path.relative_to(ROOT)
    text = path.read_text(encoding="utf-8", errors="ignore")
    violations: list[Violation] = []

    if in_pure_zone(path):
        for rule, regex, message in SIDE_EFFECT_RULES:
            for match in regex.finditer(text):
                line = line_for_offset(text, match.start())
                sample = match.group(0).strip().splitlines()[0][:120]
                violations.append(Violation(rel, line, rule, message, sample))

    for rule, regex, message in NAME_RULES:
        for match in regex.finditer(text):
            line = line_for_offset(text, match.start())
            sample = match.group(0).strip().splitlines()[0][:120]
            violations.append(Violation(rel, line, rule, message, sample))

    return violations


def run(changed_only: bool, base_ref: str) -> tuple[list[Violation], int]:
    files = relevant_files(changed_only=changed_only, base_ref=base_ref)
    violations: list[Violation] = []
    for file_path in files:
        violations.extend(scan_file(file_path))
    return violations, len(files)


def main() -> int:
    parser = argparse.ArgumentParser(description="Guard pure-by-default and naming policy.")
    parser.add_argument("--changed-only", action="store_true", help="Check only files changed from base ref.")
    parser.add_argument("--base-ref", default="origin/main", help="Git base ref for --changed-only.")
    parser.add_argument("--strict", action="store_true", help="Fail when violations are found.")
    args = parser.parse_args()

    violations, scanned = run(changed_only=args.changed_only, base_ref=args.base_ref)
    mode = "strict" if args.strict else "warn"
    scope = "changed-files" if args.changed_only else "full-repo"
    print(f"[policy-guard] mode={mode} scope={scope} scanned_files={scanned} violations={len(violations)}")
    for v in violations:
        print(f"{v.path}:{v.line}: {v.rule}: {v.message} sample='{v.sample}'")

    if args.strict and violations:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
