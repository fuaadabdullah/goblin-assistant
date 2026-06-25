#!/usr/bin/env python3
"""Repository secret scanner for config and env-like files.

Fails the build when suspicious secret patterns are found, with allowlist support.
"""

from __future__ import annotations

import argparse
import math
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ALLOWLIST = REPO_ROOT / ".secret-scan-allowlist.txt"

SCAN_EXTENSIONS = {
    ".example",
}

SCAN_NAME_PATTERNS = (
    re.compile(r"\.env", re.IGNORECASE),
    re.compile(r"example", re.IGNORECASE),
    re.compile(r"compose", re.IGNORECASE),
)

EXCLUDED_DIRS = {
    ".git",
    "node_modules",
    ".next",
    "dist",
    "build",
    "coverage",
    "__pycache__",
    ".venv",
    "venv",
    "pnpm-store",
    ".pnpm-store",
}

MAX_FILE_BYTES = 500_000

PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("gcp_private_key_field", re.compile(r"\bprivate_key\b\s*[:=]\s*[\"']?")),
    ("service_account_type", re.compile(r"\btype\b\s*[:=]\s*[\"']service_account[\"']")),
    ("pem_private_key", re.compile(r"-----BEGIN (RSA |EC |OPENSSH |)?PRIVATE KEY-----")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z\-_]{20,}\b")),
    ("aws_access_key_id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    (
        "generic_secret_assignment",
        re.compile(
            r"\b(secret|token|api[_-]?key|password)\b\s*[:=]\s*(?!\$\{?)[^\s'\"]{12,}",
            re.IGNORECASE,
        ),
    ),
]

BASE64_CANDIDATE = re.compile(r"\b[A-Za-z0-9+/]{80,}={0,2}\b")


@dataclass
class Finding:
    path: str
    line_no: int
    rule: str
    snippet: str


class Allowlist:
    def __init__(self, patterns: Iterable[str]):
        self._compiled = [re.compile(p) for p in patterns if p.strip()]

    def allows(self, finding: Finding) -> bool:
        target = f"{finding.path}:{finding.line_no}:{finding.rule}:{finding.snippet}"
        return any(p.search(target) for p in self._compiled)


def shannon_entropy(value: str) -> float:
    if not value:
        return 0.0
    freq = {ch: value.count(ch) / len(value) for ch in set(value)}
    return -sum(p * math.log2(p) for p in freq.values())


def is_scannable(path: Path) -> bool:
    if any(part in EXCLUDED_DIRS for part in path.parts):
        return False

    if path.suffix.lower() in SCAN_EXTENSIONS:
        return True

    name = path.name.lower()
    if ".env" in name:
        return True

    if name in {"docker-compose.yml", "docker-compose.yaml", "render.yaml", "render.yml"}:
        return True

    rel = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    if rel.startswith(".github/workflows/") and path.suffix.lower() in {".yml", ".yaml"}:
        return True

    return any(p.search(name) for p in SCAN_NAME_PATTERNS)


def iter_candidate_files(root: Path) -> Iterable[Path]:
    try:
        proc = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        files = [Path(p) for p in proc.stdout.decode("utf-8", errors="ignore").split("\0") if p]
        for rel_path in files:
            path = root / rel_path
            if not path.is_file() or not is_scannable(path):
                continue
            try:
                if path.stat().st_size > MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            yield path
        return
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
        base = Path(dirpath)
        for filename in filenames:
            path = base / filename
            if not is_scannable(path):
                continue
            try:
                if path.stat().st_size > MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            yield path


def scan_file(path: Path) -> list[Finding]:
    findings: list[Finding] = []

    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return findings

    rel_path = str(path.relative_to(REPO_ROOT))

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        for rule, pattern in PATTERNS:
            if pattern.search(line):
                findings.append(Finding(rel_path, idx, rule, stripped[:200]))

        for candidate in BASE64_CANDIDATE.findall(line):
            if shannon_entropy(candidate) >= 4.2:
                findings.append(
                    Finding(rel_path, idx, "high_entropy_base64_blob", stripped[:200])
                )

    return findings


def load_allowlist(path: Path) -> Allowlist:
    if not path.exists():
        return Allowlist([])

    patterns: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        candidate = raw.strip()
        if not candidate or candidate.startswith("#"):
            continue
        patterns.append(candidate)
    return Allowlist(patterns)


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan repository for accidental secrets")
    parser.add_argument(
        "--allowlist",
        type=Path,
        default=DEFAULT_ALLOWLIST,
        help="Path to regex allowlist entries",
    )
    args = parser.parse_args()

    allowlist = load_allowlist(args.allowlist)
    findings: list[Finding] = []

    for file_path in iter_candidate_files(REPO_ROOT):
        findings.extend(scan_file(file_path))

    actionable = [f for f in findings if not allowlist.allows(f)]

    if not actionable:
        print("Secret scan passed: no actionable findings.")
        return 0

    print("Secret scan failed. Actionable findings:")
    for finding in actionable:
        print(f"- {finding.path}:{finding.line_no} [{finding.rule}] {finding.snippet}")

    print("\nIf a finding is a known false positive, add a regex entry to .secret-scan-allowlist.txt")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
