#!/usr/bin/env python3
"""Generate the canonical architecture evidence report.

This report is intentionally structured data first. Historical narrative debt
reports can point here, but release decisions should use this artifact because
it records the exact revision, tool version, scanned file count, parser
failures, skipped files, and violations from the current tree.
"""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
API_ROOT = REPO_ROOT / "apps" / "api" / "src" / "api"
TOOL_VERSION = "1"
DEFAULT_OUTPUT = REPO_ROOT / "artifacts" / "architecture-evidence.json"


@dataclass(frozen=True)
class FileParseResult:
    path: Path
    module: str
    skipped_reason: str | None
    parse_error: str | None
    parse_error_line: int | None


def _run_git(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return "unknown"
    return result.stdout.strip()


def _commit_sha() -> str:
    return _run_git(["rev-parse", "HEAD"])


def _module_name(path: Path) -> str:
    rel = path.relative_to(API_ROOT.parent)
    return ".".join(rel.with_suffix("").parts)


def _iter_api_files() -> Iterable[Path]:
    for path in sorted(API_ROOT.rglob("*.py")):
        yield path


def _parse_files() -> list[FileParseResult]:
    results: list[FileParseResult] = []
    for path in _iter_api_files():
        module = _module_name(path)
        skipped_reason = None
        if "/tests/" in path.as_posix() or path.name.startswith("test_"):
            skipped_reason = "test-file"
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            results.append(
                FileParseResult(
                    path=path,
                    module=module,
                    skipped_reason=skipped_reason,
                    parse_error=None,
                    parse_error_line=None,
                )
            )
        except SyntaxError as exc:
            results.append(
                FileParseResult(
                    path=path,
                    module=module,
                    skipped_reason=skipped_reason,
                    parse_error=exc.msg,
                    parse_error_line=getattr(exc, "lineno", 1) or 1,
                )
            )
    return results


def _as_rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def _load_architecture_modules() -> tuple[object, object]:
    architecture_path = str(REPO_ROOT / "scripts" / "architecture")
    sys.path.insert(0, architecture_path)
    try:
        import check_api_architecture as api_arch
        import check_capability_boundaries as cap_bounds
    finally:
        if sys.path and sys.path[0] == architecture_path:
            sys.path.pop(0)
    return api_arch, cap_bounds


def _safe_boundary_violations(api_arch: object, parsed_files: list[FileParseResult]) -> list[dict[str, object]]:
    config = api_arch.load_boundary_config()
    files = [
        result.path
        for result in parsed_files
        if result.skipped_reason is None and result.parse_error is None
    ]
    violations = api_arch.check_boundaries(files, config)
    return [asdict(violation) for violation in violations]


def _safe_capability_violations(
    cap_bounds: object, parsed_files: list[FileParseResult]
) -> list[dict[str, object]]:
    manifest = cap_bounds.load_manifest()
    files = [
        result.path
        for result in parsed_files
        if result.skipped_reason is None and result.parse_error is None
    ]
    violations = cap_bounds.check_capability_boundaries(files, manifest)
    return [asdict(violation) for violation in violations]


def generate_report() -> dict[str, object]:
    parsed_files = _parse_files()
    api_arch, cap_bounds = _load_architecture_modules()
    boundary_violations = _safe_boundary_violations(api_arch, parsed_files)
    capability_violations = _safe_capability_violations(cap_bounds, parsed_files)
    parser_failures = [
        {
            "file": _as_rel(result.path),
            "line": result.parse_error_line,
            "module": result.module,
            "error": result.parse_error,
        }
        for result in parsed_files
        if result.parse_error is not None
    ]
    skipped_files = [
        {
            "file": _as_rel(result.path),
            "module": result.module,
            "reason": result.skipped_reason,
        }
        for result in parsed_files
        if result.skipped_reason is not None
    ]
    scanned_files = [
        _as_rel(result.path)
        for result in parsed_files
        if result.skipped_reason is None and result.parse_error is None
    ]
    violations = [
        {"analyzer": "api-boundaries", **violation}
        for violation in boundary_violations
    ] + [
        {"analyzer": "capability-boundaries", **violation}
        for violation in capability_violations
    ]

    return {
        "schema_version": 1,
        "tool": "generate_architecture_evidence",
        "tool_version": TOOL_VERSION,
        "commit_sha": _commit_sha(),
        "generation_timestamp": datetime.now(timezone.utc).isoformat(),
        "scanned_file_count": len(scanned_files),
        "parser_failure_count": len(parser_failures),
        "violation_count": len(violations),
        "skipped_file_count": len(skipped_files),
        "violations": violations,
        "skipped_files": skipped_files,
        "unresolved_parsing_failures": parser_failures,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    report = generate_report()
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.check:
        if not args.output.exists():
            print(f"{args.output} does not exist; run make architecture-evidence", file=sys.stderr)
            return 2
        existing = args.output.read_text(encoding="utf-8")
        existing_payload = json.loads(existing)
        existing_payload.pop("generation_timestamp", None)
        comparable_report = dict(report)
        comparable_report.pop("generation_timestamp", None)
        if existing_payload != comparable_report:
            print(f"{args.output} is stale; run make architecture-evidence", file=sys.stderr)
            return 1
        print(f"{args.output} is up-to-date")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
