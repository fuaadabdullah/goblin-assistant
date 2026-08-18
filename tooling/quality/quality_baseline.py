from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = REPO_ROOT / "tooling" / "quality" / "quality-baseline.json"
CACHE_PATH = REPO_ROOT / ".tmp" / "quality-baseline-cache.json"
TOOL_VERSION = "2"

WEB_ASSERTION_PATTERN = re.compile(r"\bas\s+(?:any|unknown)\b")
WEB_SUPPRESSION_PATTERN = re.compile(r"eslint-disable|@ts-ignore|@ts-expect-error")
PYTHON_NOQA_PATTERN = re.compile(r"\bnoqa\b")
XFAIL_PATTERN = re.compile(r"@pytest\.mark\.xfail|pytest\.xfail\(")
XFAIL_METADATA_FIELDS = ("reason", "issue", "subsystem", "removal")
XFAIL_DATE_FIELDS = ("expires", "review")

SUPPRESSION_PATTERNS = {
    "python_noqa": re.compile(r"#\s*noqa(?::\s*[\w, ]+)?(?P<reason>\s+#\s*\S.*)?$"),
    "web_eslint_disable": re.compile(r"eslint-disable(?:-(?:next-)?line)?(?P<reason>.*)$"),
    "web_ts_ignore": re.compile(r"@ts-ignore(?P<reason>.*)$"),
    "web_ts_expect_error": re.compile(r"@ts-expect-error(?P<reason>.*)$"),
    "web_assertion": WEB_ASSERTION_PATTERN,
}
REASON_KEYWORDS = {
    "interop": "justified_interop_typing_issue",
    "compat": "justified_interop_typing_issue",
    "compatibility": "justified_interop_typing_issue",
    "framework": "framework_limitation",
    "legacy": "legacy_debt",
    "todo": "temporary_suppression",
    "temporary": "temporary_suppression",
    "remove": "temporary_suppression",
}
SUPPRESSION_CATEGORIES = (
    "justified_interop_typing_issue",
    "framework_limitation",
    "legacy_debt",
    "temporary_suppression",
    "clearly_removable",
)


@dataclass(frozen=True)
class GovernanceIssue:
    path: str
    line: int
    message: str


@dataclass(frozen=True)
class AnalyzerResult:
    name: str
    metric_key: str
    command: list[str]
    status: str
    exit_code: int | None
    count: int
    elapsed_seconds: float
    stdout: str
    stderr: str


@dataclass(frozen=True)
class SuppressionFinding:
    path: str
    line: int
    kind: str
    category: str
    reason: str


def _log(message: str, verbose: bool) -> None:
    if verbose:
        print(message, file=sys.stderr)


def _run_rg(args: list[str], root: Path) -> list[str]:
    completed = subprocess.run(
        ["rg", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode not in (0, 1):
        raise RuntimeError(completed.stderr.strip() or "rg failed")
    return [line for line in completed.stdout.splitlines() if line]


def _count_matches(
    root: Path, base: Path, pattern: re.Pattern[str], suffixes: set[str]
) -> int:
    if not base.exists():
        return 0

    globs = [
        f"{base.relative_to(root).as_posix()}/**/*{suffix}"
        for suffix in sorted(suffixes)
    ]
    return len(
        _run_rg(
            ["-o", pattern.pattern, *sum([["--glob", glob] for glob in globs], [])],
            root,
        )
    )


def _count_files_with_pattern(
    root: Path, base: Path, pattern: re.Pattern[str], suffixes: set[str]
) -> int:
    if not base.exists():
        return 0

    globs = [
        f"{base.relative_to(root).as_posix()}/**/*{suffix}"
        for suffix in sorted(suffixes)
    ]
    return len(
        _run_rg(
            ["-l", pattern.pattern, *sum([["--glob", glob] for glob in globs], [])],
            root,
        )
    )


def _iter_files(base: Path, suffixes: set[str]) -> Iterable[Path]:
    if not base.exists():
        return
    for suffix in sorted(suffixes):
        yield from sorted(base.rglob(f"*{suffix}"))


def _fingerprint(path: Path) -> str:
    stat = path.stat()
    raw = f"{path}:{stat.st_mtime_ns}:{stat.st_size}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _load_cache(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"version": TOOL_VERSION, "files": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"version": TOOL_VERSION, "files": {}}
    if payload.get("version") != TOOL_VERSION:
        return {"version": TOOL_VERSION, "files": {}}
    return payload


def _write_cache(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _reason_text(line: str, kind: str) -> str:
    if kind == "python_noqa":
        match = SUPPRESSION_PATTERNS[kind].search(line)
        reason = (match.group("reason") if match else "") or ""
        return reason.lstrip(" #").strip()
    if kind.startswith("web_ts_"):
        return line.split(kind.replace("web_ts_", "@ts-"), 1)[-1].lstrip(" :-#").strip()
    if kind == "web_eslint_disable":
        match = SUPPRESSION_PATTERNS[kind].search(line)
        return (match.group("reason") if match else "").lstrip(" :-#").strip()
    return ""


def _classify_reason(reason: str, kind: str) -> str:
    lower = reason.lower()
    for keyword, category in REASON_KEYWORDS.items():
        if keyword in lower:
            return category
    if kind == "web_assertion":
        return "justified_interop_typing_issue"
    if reason:
        return "legacy_debt"
    return "clearly_removable"


def _scan_suppression_lines(
    root: Path, path: Path, candidates: list[tuple[int, str]]
) -> list[SuppressionFinding]:
    findings: list[SuppressionFinding] = []
    suffix = path.suffix
    for line_number, line in candidates:
        applicable: dict[str, re.Pattern[str]]
        if suffix == ".py":
            applicable = {"python_noqa": SUPPRESSION_PATTERNS["python_noqa"]}
        else:
            applicable = {
                key: pattern
                for key, pattern in SUPPRESSION_PATTERNS.items()
                if key != "python_noqa"
            }
        for kind, pattern in applicable.items():
            if not pattern.search(line):
                continue
            reason = _reason_text(line, kind)
            findings.append(
                SuppressionFinding(
                    path=str(path.relative_to(root)),
                    line=line_number,
                    kind=kind,
                    category=_classify_reason(reason, kind),
                    reason=reason,
                )
            )
    return findings


def _suppression_candidate_lines(root: Path) -> dict[Path, list[tuple[int, str]]]:
    globs = [
        "apps/api/**/*.py",
        "apps/web/**/*.ts",
        "apps/web/**/*.tsx",
        "apps/web/**/*.js",
        "apps/web/**/*.jsx",
        "packages/**/*.ts",
        "packages/**/*.tsx",
        "packages/**/*.js",
        "packages/**/*.jsx",
    ]
    lines = _run_rg(
        [
            "-n",
            r"noqa|eslint-disable|@ts-ignore|@ts-expect-error|\bas\s+(?:any|unknown)\b",
            *sum([["--glob", glob] for glob in globs], []),
            "--glob",
            "!**/node_modules/**",
            "--glob",
            "!**/src/generated/**",
            "--glob",
            "!**/openapi/**",
        ],
        root,
    )
    grouped: dict[Path, list[tuple[int, str]]] = {}
    for raw in lines:
        path_str, line_number, content = raw.split(":", 2)
        grouped.setdefault(root / path_str, []).append((int(line_number), content))
    return grouped


def classify_suppressions(
    root: Path = REPO_ROOT, cache_path: Path = CACHE_PATH
) -> list[SuppressionFinding]:
    cache = _load_cache(cache_path)
    files_cache = cache.setdefault("files", {})
    assert isinstance(files_cache, dict)
    findings: list[SuppressionFinding] = []
    candidate_lines = _suppression_candidate_lines(root)

    for path, candidates in sorted(candidate_lines.items()):
        path_text = path.as_posix()
        if (
            "/node_modules/" in path_text
            or "/src/generated/" in path_text
            or "/openapi/" in path_text
        ):
            continue
        rel = str(path.relative_to(root))
        fingerprint = _fingerprint(path)
        cached = files_cache.get(rel)
        if (
            isinstance(cached, dict)
            and cached.get("fingerprint") == fingerprint
            and isinstance(cached.get("findings"), list)
        ):
            findings.extend(SuppressionFinding(**item) for item in cached["findings"])
            continue
        file_findings = _scan_suppression_lines(root, path, candidates)
        files_cache[rel] = {
            "fingerprint": fingerprint,
            "findings": [asdict(item) for item in file_findings],
        }
        findings.extend(file_findings)

    _write_cache(cache_path, cache)
    return findings


def collect_source_metrics(root: Path = REPO_ROOT) -> dict[str, int]:
    suppressions = classify_suppressions(root)
    categories = {f"suppression_{category}": 0 for category in SUPPRESSION_CATEGORIES}
    for finding in suppressions:
        categories[f"suppression_{finding.category}"] = (
            categories.get(f"suppression_{finding.category}", 0) + 1
        )

    return {
        "web_assertions": _count_matches(
            root,
            root / "apps" / "web" / "src",
            WEB_ASSERTION_PATTERN,
            {".ts", ".tsx"},
        ),
        "web_eslint_suppression_files": _count_files_with_pattern(
            root,
            root / "apps" / "web",
            WEB_SUPPRESSION_PATTERN,
            {".ts", ".tsx", ".js", ".jsx"},
        ),
        "python_noqa_files": _count_files_with_pattern(
            root,
            root / "apps" / "api",
            PYTHON_NOQA_PATTERN,
            {".py"},
        ),
        "xfail_tests": _count_matches(
            root,
            root / "apps" / "api" / "src" / "api" / "tests",
            XFAIL_PATTERN,
            {".py"},
        )
        + _count_matches(root, root / "tests", XFAIL_PATTERN, {".py"}),
        **categories,
    }


def _run_analyzer(
    name: str,
    metric_key: str,
    command: list[str],
    timeout_seconds: int,
    verbose: bool,
) -> AnalyzerResult:
    _log(f"[quality] running {name}", verbose)
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
        elapsed = time.perf_counter() - started
        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()
        count = _parse_violation_count(stdout)
        status = "ok" if completed.returncode in (0, 1) else "analyzer-failure"
        return AnalyzerResult(
            name=name,
            metric_key=metric_key,
            command=command,
            status=status,
            exit_code=completed.returncode,
            count=count,
            elapsed_seconds=elapsed,
            stdout=stdout,
            stderr=stderr,
        )
    except subprocess.TimeoutExpired as exc:
        elapsed = time.perf_counter() - started
        return AnalyzerResult(
            name=name,
            metric_key=metric_key,
            command=command,
            status="timeout",
            exit_code=None,
            count=0,
            elapsed_seconds=elapsed,
            stdout=(exc.stdout or "").strip() if isinstance(exc.stdout, str) else "",
            stderr=(exc.stderr or "").strip() if isinstance(exc.stderr, str) else "",
        )


def _parse_violation_count(output: str) -> int:
    match = re.search(r"Found\s+(\d+)\s+violation", output)
    if match:
        return int(match.group(1))
    if "All checks passed." in output or "Capability boundary check passed." in output:
        return 0
    return len([line for line in output.splitlines() if ": " in line or line.strip().startswith("- ")])


def collect_architecture_metrics(
    timeout_seconds: int, verbose: bool
) -> tuple[dict[str, int], list[AnalyzerResult]]:
    analyzers = [
        (
            "architecture-boundaries",
            "architecture_boundary_violations",
            [sys.executable, "scripts/architecture/check_api_architecture.py", "boundaries"],
        ),
        (
            "architecture-capabilities",
            "architecture_capability_violations",
            [sys.executable, "scripts/architecture/check_capability_boundaries.py"],
        ),
    ]
    results = [
        _run_analyzer(name, metric_key, command, timeout_seconds, verbose)
        for name, metric_key, command in analyzers
    ]
    metrics = {result.metric_key: result.count for result in results}
    metrics["architecture_total_violations"] = sum(metrics.values())
    return metrics, results


def collect_metrics(
    root: Path = REPO_ROOT, timeout_seconds: int = 30, verbose: bool = True
) -> tuple[dict[str, int], list[AnalyzerResult]]:
    _log("[quality] collecting source metrics", verbose)
    source_metrics = collect_source_metrics(root)
    architecture_metrics, analyzer_results = collect_architecture_metrics(
        timeout_seconds=timeout_seconds,
        verbose=verbose,
    )
    return {**source_metrics, **architecture_metrics}, analyzer_results


def _iter_xfail_matches(root: Path = REPO_ROOT) -> list[tuple[Path, int]]:
    globs = [
        "apps/api/src/api/tests/**/*.py",
        "tests/**/*.py",
    ]
    lines = _run_rg(
        [
            "-n",
            r"@pytest\.mark\.xfail|pytest\.xfail\(",
            *sum([["--glob", glob] for glob in globs], []),
        ],
        root,
    )
    matches: list[tuple[Path, int]] = []
    for line in lines:
        path_str, line_str, _ = line.split(":", 2)
        matches.append((root / path_str, int(line_str)))
    return matches


def find_xfail_governance_issues(root: Path = REPO_ROOT) -> list[GovernanceIssue]:
    issues: list[GovernanceIssue] = []
    cache: dict[Path, list[str]] = {}
    for path, line_number in _iter_xfail_matches(root):
        lines = cache.setdefault(path, path.read_text(encoding="utf-8").splitlines())
        line = lines[line_number - 1]

        if "pytestmark" in line and "xfail" in line:
            issues.append(
                GovernanceIssue(
                    path=str(path.relative_to(root)),
                    line=line_number,
                    message="file-level xfail is not allowed",
                )
            )

        comment_window = "\n".join(
            candidate.strip().lower()
            for candidate in lines[max(0, line_number - 6) : line_number - 1]
        )
        missing = [
            field
            for field in XFAIL_METADATA_FIELDS
            if f"{field}:" not in comment_window
        ]
        has_date = any(f"{field}:" in comment_window for field in XFAIL_DATE_FIELDS)
        if missing or not has_date:
            date_requirement = [] if has_date else ["expires: or review:"]
            issues.append(
                GovernanceIssue(
                    path=str(path.relative_to(root)),
                    line=line_number,
                    message="xfail metadata missing: "
                    + ", ".join([*missing, *date_requirement]),
                )
            )

    return issues


def find_suppression_governance_issues(
    root: Path = REPO_ROOT,
) -> list[GovernanceIssue]:
    issues: list[GovernanceIssue] = []
    for finding in classify_suppressions(root):
        if finding.kind == "web_assertion":
            continue
        if finding.category != "clearly_removable":
            continue
        issues.append(
            GovernanceIssue(
                path=finding.path,
                line=finding.line,
                message=f"{finding.kind} suppression missing reason",
            )
        )
    return issues


def _added_source_lines(root: Path = REPO_ROOT) -> list[tuple[str, int, str]]:
    completed = subprocess.run(
        [
            "git",
            "diff",
            "--unified=0",
            "--",
            "apps/api",
            "apps/web",
            "packages",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode not in (0, 1):
        raise RuntimeError(completed.stderr.strip() or "git diff failed")

    current_path = ""
    new_line = 0
    additions: list[tuple[str, int, str]] = []
    for raw in completed.stdout.splitlines():
        if raw.startswith("+++ b/"):
            current_path = raw.removeprefix("+++ b/")
            continue
        if raw.startswith("@@"):
            match = re.search(r"\+(\d+)(?:,(\d+))?", raw)
            if match:
                new_line = int(match.group(1))
            continue
        if not current_path:
            continue
        if raw.startswith("+") and not raw.startswith("+++"):
            additions.append((current_path, new_line, raw[1:]))
            new_line += 1
        elif not raw.startswith("-"):
            new_line += 1
    return additions


def find_new_suppression_governance_issues(
    root: Path = REPO_ROOT,
) -> list[GovernanceIssue]:
    issues: list[GovernanceIssue] = []
    for path_str, line_number, line in _added_source_lines(root):
        path = root / path_str
        if path.suffix == ".py":
            kinds = ["python_noqa"]
        else:
            kinds = ["web_eslint_disable", "web_ts_ignore", "web_ts_expect_error"]
        for kind in kinds:
            pattern = SUPPRESSION_PATTERNS[kind]
            if not pattern.search(line):
                continue
            reason = _reason_text(line, kind)
            if reason:
                continue
            issues.append(
                GovernanceIssue(
                    path=path_str,
                    line=line_number,
                    message=f"new {kind} suppression missing reason",
                )
            )
    return issues


def load_baseline(path: Path) -> dict[str, int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {key: int(value) for key, value in payload["metrics"].items()}


def compare_to_baseline(actual: dict[str, int], baseline: dict[str, int]) -> list[str]:
    failures: list[str] = []
    for key, baseline_value in baseline.items():
        actual_value = actual.get(key)
        if actual_value is None:
            failures.append(f"missing metric: {key}")
            continue
        if actual_value > baseline_value:
            failures.append(f"{key} increased: {actual_value} > {baseline_value}")
    return failures


def write_baseline(path: Path, metrics: dict[str, int]) -> None:
    path.write_text(json.dumps({"metrics": metrics}, indent=2) + "\n", encoding="utf-8")


def _write_partial_result(
    path: Path | None,
    metrics: dict[str, int],
    analyzer_results: list[AnalyzerResult],
    issues: list[GovernanceIssue],
) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "tool": "quality_baseline",
        "tool_version": TOOL_VERSION,
        "metrics": metrics,
        "analyzers": [asdict(result) for result in analyzer_results],
        "governance_issues": [asdict(issue) for issue in issues],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _print_analyzer_failure(result: AnalyzerResult) -> None:
    command = " ".join(result.command)
    print(
        f"{result.name} analyzer {result.status} after "
        f"{result.elapsed_seconds:.2f}s: {command}",
        file=sys.stderr,
    )
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    if result.stdout:
        print(result.stdout, file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check repo debt baselines.")
    parser.add_argument("--baseline", type=Path, default=BASELINE_PATH)
    parser.add_argument("--write-baseline", action="store_true")
    parser.add_argument("--timeout-seconds", type=int, default=30)
    parser.add_argument("--partial-output", type=Path)
    parser.add_argument(
        "--strict-suppression-reasons",
        action="store_true",
        help="Fail on every suppression missing an inline reason, not just baseline increases.",
    )
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    metrics, analyzer_results = collect_metrics(
        timeout_seconds=args.timeout_seconds,
        verbose=not args.quiet,
    )
    xfail_issues = find_xfail_governance_issues()
    suppression_issues = find_new_suppression_governance_issues()
    if args.strict_suppression_reasons:
        suppression_issues.extend(find_suppression_governance_issues())
    governance_issues = [*xfail_issues, *suppression_issues]
    analyzer_failures = [
        result for result in analyzer_results if result.status != "ok"
    ]

    _write_partial_result(args.partial_output, metrics, analyzer_results, governance_issues)

    if analyzer_failures:
        for result in analyzer_failures:
            _print_analyzer_failure(result)
        return 2

    if args.write_baseline:
        write_baseline(args.baseline, metrics)
        return 0

    baseline = load_baseline(args.baseline)
    failures = compare_to_baseline(metrics, baseline)

    for key, value in metrics.items():
        print(f"{key}={value}")

    if governance_issues:
        for issue in governance_issues:
            print(f"{issue.path}:{issue.line}: {issue.message}")
        return 1

    if failures:
        for failure in failures:
            print(failure)
        return 1

    print("quality baseline check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
