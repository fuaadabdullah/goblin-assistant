#!/usr/bin/env python3
"""Generate nightly architecture dashboard metrics as a single JSON artifact.

Aggregates: API dependency-cycle count, boundary violations, capability
violations, dead code counts, largest source files, and an import-graph diff
against a previous run's snapshot (if one is supplied).
"""

from __future__ import annotations

import argparse
import importlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

api_arch = importlib.import_module("check_api_architecture")
cap_bounds = importlib.import_module("check_capability_boundaries")

API_ROOT = REPO_ROOT / "apps" / "api" / "src" / "api"
WEB_SRC = REPO_ROOT / "apps" / "web" / "src"
LARGEST_FILES_LIMIT = 15
SKIP_DIR_NAMES = {"node_modules", ".next", "__pycache__", ".git", "dist", "build", "coverage"}


def cycle_metrics(config: api_arch.BoundaryConfig) -> Tuple[int, List[List[str]], Dict[str, List[str]]]:
    files = list(api_arch.iter_api_python_files())
    graph = api_arch.build_api_graph(files, config)
    cycles = [c for c in api_arch.find_cycles(graph) if len(c) >= 2]
    serializable_graph = {mod: sorted(deps) for mod, deps in graph.items()}
    return len(cycles), cycles, serializable_graph


def boundary_violation_count(config: api_arch.BoundaryConfig) -> int:
    files = list(api_arch.iter_api_python_files())
    return len(api_arch.check_boundaries(files, config))


def capability_violation_count() -> int:
    manifest = cap_bounds.load_manifest()
    files = list(cap_bounds.iter_api_files())
    return len(cap_bounds.check_capability_boundaries(files, manifest))


def dead_code_counts() -> Dict[str, object]:
    vulture = subprocess.run(
        [
            sys.executable,
            "-m",
            "vulture",
            "src/api",
            "vulture_whitelist.py",
            "--min-confidence",
            "80",
        ],
        cwd=REPO_ROOT / "apps" / "api",
        capture_output=True,
        check=False,
        text=True,
    )
    python_unused = len([ln for ln in vulture.stdout.splitlines() if ln.strip()])

    knip = subprocess.run(
        ["pnpm", "--filter", "@goblin/web", "exec", "knip", "--reporter", "json"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
        text=True,
    )
    typescript_unused_files: object = None
    typescript_issue_count: object = None
    try:
        knip_data = json.loads(knip.stdout or "{}")
        typescript_unused_files = len(knip_data.get("files", []))
        typescript_issue_count = len(knip_data.get("issues", []))
    except json.JSONDecodeError:
        pass

    return {
        "python_unused": python_unused,
        "typescript_unused_files": typescript_unused_files,
        "typescript_issue_count": typescript_issue_count,
    }


def largest_files(limit: int = LARGEST_FILES_LIMIT) -> List[Dict[str, object]]:
    candidates: List[Tuple[int, str]] = []

    for root_dir, extensions in ((API_ROOT, {".py"}), (WEB_SRC, {".ts", ".tsx"})):
        if not root_dir.exists():
            continue
        for path in root_dir.rglob("*"):
            if path.is_dir() or path.suffix not in extensions:
                continue
            if SKIP_DIR_NAMES & set(path.parts):
                continue
            try:
                line_count = sum(1 for _ in path.open("r", encoding="utf-8", errors="ignore"))
            except OSError:
                continue
            candidates.append((line_count, str(path.relative_to(REPO_ROOT))))

    candidates.sort(reverse=True)
    return [{"path": path, "lines": lines} for lines, path in candidates[:limit]]


def graph_diff(current: Dict[str, List[str]], previous: Dict[str, List[str]]) -> Dict[str, object]:
    def edge_set(graph: Dict[str, List[str]]) -> Set[Tuple[str, str]]:
        return {(src, dst) for src, dsts in graph.items() for dst in dsts}

    current_edges = edge_set(current)
    previous_edges = edge_set(previous)
    added = sorted(f"{a} -> {b}" for a, b in current_edges - previous_edges)
    removed = sorted(f"{a} -> {b}" for a, b in previous_edges - current_edges)
    return {
        "added_edges": added,
        "removed_edges": removed,
        "added_count": len(added),
        "removed_count": len(removed),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the nightly architecture dashboard")
    parser.add_argument("--output", type=Path, required=True, help="Path to write dashboard JSON")
    parser.add_argument(
        "--previous-graph",
        type=Path,
        help="Path to a previous run's dashboard JSON (from this script) to diff the import graph against",
    )
    args = parser.parse_args()

    config = api_arch.load_boundary_config()
    cycle_count, cycles, graph = cycle_metrics(config)

    dashboard: Dict[str, object] = {
        "cycles": {"count": cycle_count, "cycles": cycles},
        "boundary_violations": boundary_violation_count(config),
        "capability_violations": capability_violation_count(),
        "dead_code": dead_code_counts(),
        "largest_files": largest_files(),
        "import_graph": graph,
    }

    if args.previous_graph and args.previous_graph.exists():
        previous = json.loads(args.previous_graph.read_text(encoding="utf-8"))
        dashboard["import_graph_changes"] = graph_diff(graph, previous.get("import_graph", {}))
    else:
        dashboard["import_graph_changes"] = None

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(dashboard, indent=2) + "\n", encoding="utf-8")

    print(f"cycle_count={cycle_count}")
    print(f"boundary_violations={dashboard['boundary_violations']}")
    print(f"capability_violations={dashboard['capability_violations']}")
    print(f"dead_code={json.dumps(dashboard['dead_code'])}")
    if dashboard["import_graph_changes"] is not None:
        changes = dashboard["import_graph_changes"]
        print(f"import_graph_changes=+{changes['added_count']}/-{changes['removed_count']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
