#!/usr/bin/env python3
"""API architecture contract checks for modular boundaries and cycles.

Phase-1 friendly behavior:
- `boundaries` and `cycles` can run on full tree or changed files only.
- Changed-file mode is intended for blocking CI gates while legacy debt is reduced.
"""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple
import tomllib

REPO_ROOT = Path(__file__).resolve().parents[2]
API_ROOT = REPO_ROOT / "apps" / "api" / "src" / "api"
BOUNDARY_CONFIG_PATH = REPO_ROOT / "apps" / "api" / "architecture-boundaries.toml"

DEFAULT_SERVICE_FORBIDDEN_IMPORT_PREFIXES: Tuple[str, ...] = ("fastapi", "starlette")


@dataclass(frozen=True)
class Violation:
    file: str
    line: int
    rule: str
    detail: str


@dataclass(frozen=True)
class BoundaryConfig:
    service_forbidden_framework_prefixes: Tuple[str, ...]
    route_storage_allowlist: Set[str]
    parse_error_allowlist: Set[str]
    ignored_cycles: Set[str]
    route_no_direct_storage: bool
    service_no_route_dependency: bool
    service_no_framework_coupling: bool


def load_boundary_config() -> BoundaryConfig:
    if not BOUNDARY_CONFIG_PATH.exists():
        return BoundaryConfig(
            service_forbidden_framework_prefixes=DEFAULT_SERVICE_FORBIDDEN_IMPORT_PREFIXES,
            route_storage_allowlist=set(),
            parse_error_allowlist=set(),
            ignored_cycles=set(),
            route_no_direct_storage=True,
            service_no_route_dependency=True,
            service_no_framework_coupling=True,
        )

    data = tomllib.loads(BOUNDARY_CONFIG_PATH.read_text(encoding="utf-8"))
    services_cfg = data.get("services", {})
    routes_cfg = data.get("routes", {})
    parser_cfg = data.get("parser", {})
    cycles_cfg = data.get("cycles", {})
    rules_cfg = data.get("rules", {})

    return BoundaryConfig(
        service_forbidden_framework_prefixes=tuple(
            services_cfg.get(
                "forbidden_framework_prefixes",
                list(DEFAULT_SERVICE_FORBIDDEN_IMPORT_PREFIXES),
            )
        ),
        route_storage_allowlist=set(routes_cfg.get("allow_route_storage_imports", [])),
        parse_error_allowlist=set(parser_cfg.get("allow_parse_errors", [])),
        ignored_cycles=set(cycles_cfg.get("ignore_cycles", [])),
        route_no_direct_storage=bool(rules_cfg.get("route_no_direct_storage", True)),
        service_no_route_dependency=bool(rules_cfg.get("service_no_route_dependency", True)),
        service_no_framework_coupling=bool(rules_cfg.get("service_no_framework_coupling", True)),
    )


def _run_git(args: List[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def get_changed_python_files(base_ref: str) -> Set[Path]:
    merge_base = _run_git(["merge-base", base_ref, "HEAD"])
    diff = _run_git(["diff", "--name-only", f"{merge_base}...HEAD"])
    changed: Set[Path] = set()
    for raw in diff.splitlines():
        if not raw.endswith(".py"):
            continue
        path = (REPO_ROOT / raw).resolve()
        if path.is_file() and API_ROOT in path.parents:
            changed.add(path)
    return changed


def iter_api_python_files(changed_only: Set[Path] | None = None) -> Iterable[Path]:
    if changed_only is not None:
        for path in sorted(changed_only):
            if "/tests/" in path.as_posix() or path.name.startswith("test_"):
                continue
            yield path
        return

    for path in sorted(API_ROOT.rglob("*.py")):
        if "/tests/" in path.as_posix() or path.name.startswith("test_"):
            continue
        yield path


def module_name_from_path(path: Path) -> str:
    rel = path.relative_to(API_ROOT.parent)
    return ".".join(rel.with_suffix("").parts)


def resolve_import_from(current_module: str, node: ast.ImportFrom) -> str | None:
    if node.level == 0:
        return node.module

    parts = current_module.split(".")
    up = node.level
    if up > len(parts):
        return None
    base = parts[:-up]
    if node.module:
        base.extend(node.module.split("."))
    if not base:
        return None
    return ".".join(base)


def is_route_module(module: str) -> bool:
    if module.startswith("api.routes"):
        return True
    leaf = module.split(".")[-1]
    return leaf.endswith("_router") or leaf.endswith("_api")


def is_service_module(module: str) -> bool:
    return module.startswith("api.services")


def is_storage_module(module: str) -> bool:
    return module.startswith("api.storage")


def classify_imports(path: Path, module: str) -> List[Tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: List[Tuple[int, str]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom):
            resolved = resolve_import_from(module, node)
            if resolved:
                imports.append((node.lineno, resolved))

    return imports


def safe_classify_imports(
    path: Path, module: str, config: BoundaryConfig
) -> Tuple[List[Tuple[int, str]], List[Violation]]:
    try:
        return classify_imports(path, module), []
    except SyntaxError as exc:
        if module in config.parse_error_allowlist:
            return [], []
        violation = Violation(
            file=str(path.relative_to(REPO_ROOT)),
            line=getattr(exc, "lineno", 1) or 1,
            rule="parse-error",
            detail=f"{module} has invalid syntax: {exc.msg}",
        )
        return [], [violation]


def check_boundaries(files: Iterable[Path], config: BoundaryConfig) -> List[Violation]:
    violations: List[Violation] = []

    for path in files:
        module = module_name_from_path(path)
        imports, parse_violations = safe_classify_imports(path, module, config)
        violations.extend(parse_violations)

        for lineno, imported in imports:
            if config.route_no_direct_storage and is_route_module(module) and is_storage_module(imported):
                route_storage_key = f"{module} -> {imported}"
                if route_storage_key in config.route_storage_allowlist:
                    continue
                violations.append(
                    Violation(
                        file=str(path.relative_to(REPO_ROOT)),
                        line=lineno,
                        rule="route-no-direct-storage",
                        detail=f"{module} directly imports storage module {imported}",
                    )
                )

            if config.service_no_route_dependency and is_service_module(module) and is_route_module(imported):
                violations.append(
                    Violation(
                        file=str(path.relative_to(REPO_ROOT)),
                        line=lineno,
                        rule="service-no-route-dependency",
                        detail=f"service module {module} imports route/controller module {imported}",
                    )
                )

            if (
                config.service_no_framework_coupling
                and is_service_module(module)
                and imported.startswith(config.service_forbidden_framework_prefixes)
            ):
                violations.append(
                    Violation(
                        file=str(path.relative_to(REPO_ROOT)),
                        line=lineno,
                        rule="service-no-fastapi-coupling",
                        detail=f"service module {module} imports framework module {imported}",
                    )
                )

    return violations


def build_api_graph(files: Iterable[Path], config: BoundaryConfig) -> Dict[str, Set[str]]:
    graph: Dict[str, Set[str]] = {}
    module_by_path: Dict[Path, str] = {}

    file_list = list(files)
    module_set: Set[str] = set()

    for path in file_list:
        mod = module_name_from_path(path)
        module_by_path[path] = mod
        module_set.add(mod)
        graph.setdefault(mod, set())

    for path in file_list:
        src = module_by_path[path]
        imports, _ = safe_classify_imports(path, src, config)
        for _, imported in imports:
            if imported in module_set:
                graph[src].add(imported)

    return graph


def find_cycles(graph: Dict[str, Set[str]]) -> List[List[str]]:
    visited: Set[str] = set()
    stack: Set[str] = set()
    path: List[str] = []
    cycles: Set[Tuple[str, ...]] = set()

    def dfs(node: str) -> None:
        visited.add(node)
        stack.add(node)
        path.append(node)

        for nxt in sorted(graph.get(node, set())):
            if nxt not in visited:
                dfs(nxt)
            elif nxt in stack:
                idx = path.index(nxt)
                cycle = path[idx:] + [nxt]
                normalized = normalize_cycle(cycle)
                cycles.add(normalized)

        path.pop()
        stack.remove(node)

    for n in sorted(graph):
        if n not in visited:
            dfs(n)

    return [list(c) for c in sorted(cycles)]


def normalize_cycle(cycle: List[str]) -> Tuple[str, ...]:
    core = cycle[:-1]
    if not core:
        return tuple(cycle)
    rotations = [tuple(core[i:] + core[:i] + [core[i]]) for i in range(len(core))]
    return min(rotations)


def check_cycles(
    files: Iterable[Path], config: BoundaryConfig, apply_ignore: bool = True
) -> List[Violation]:
    graph = build_api_graph(files, config)
    cycles = find_cycles(graph)
    violations: List[Violation] = []

    for cycle in cycles:
        if len(cycle) < 2:
            continue
        display = " -> ".join(cycle)
        if apply_ignore and display in config.ignored_cycles:
            continue
        violations.append(
            Violation(
                file="apps/api/src/api",
                line=1,
                rule="no-circular-dependencies",
                detail=display,
            )
        )

    return violations


def print_violations(violations: List[Violation]) -> None:
    for v in violations:
        print(f"{v.file}:{v.line}: {v.rule}: {v.detail}")


def write_cycle_report(violations: List[Violation], output_json: Path) -> None:
    """Write a JSON cycle report plus a Graphviz DOT graph of the cyclic edges."""
    cycles = [v.detail.split(" -> ") for v in violations if v.rule == "no-circular-dependencies"]

    output_json.parent.mkdir(parents=True, exist_ok=True)
    report = {"cycle_count": len(cycles), "cycles": cycles}
    output_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    edges: Set[Tuple[str, str]] = set()
    for cycle in cycles:
        for a, b in zip(cycle, cycle[1:]):
            edges.add((a, b))

    dot_lines = ["digraph api_cycles {", "  rankdir=LR;", "  node [fontsize=10];"]
    for a, b in sorted(edges):
        dot_lines.append(f'  "{a}" -> "{b}" [color=red];')
    dot_lines.append("}")
    output_json.with_suffix(".dot").write_text("\n".join(dot_lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check API modular architecture rules")
    parser.add_argument("mode", choices=["boundaries", "cycles"])
    parser.add_argument(
        "--changed-only",
        action="store_true",
        help="Analyze only files changed from merge-base(<base-ref>, HEAD)",
    )
    parser.add_argument(
        "--base-ref",
        default="origin/main",
        help="Base ref for --changed-only (default: origin/main)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write a JSON report to this path (cycles mode also writes a .dot graph alongside it)",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Always exit 0 regardless of violations found; used while a check is not yet a blocking gate",
    )
    args = parser.parse_args()

    changed_files: Set[Path] | None = None
    if args.changed_only:
        try:
            changed_files = get_changed_python_files(args.base_ref)
        except subprocess.CalledProcessError as exc:
            print(f"error: failed to compute changed files from git: {exc}", file=sys.stderr)
            return 2

    files = list(iter_api_python_files(changed_only=changed_files))
    if not files:
        print("No API python files to analyze.")
        return 0

    config = load_boundary_config()

    if args.mode == "boundaries":
        violations = check_boundaries(files, config)
    else:
        # In report-only mode we always show the true, unfiltered cycle count
        # (ignoring the baseline allowlist) so the dashboard/summary reflects
        # actual debt rather than what the gate currently lets through.
        violations = check_cycles(files, config, apply_ignore=not args.report_only)
        if args.output:
            write_cycle_report(violations, args.output)

    if violations:
        print_violations(violations)
        print(f"\nFound {len(violations)} violation(s).")
        if args.report_only:
            return 0
        return 1

    print("All checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
