"""
Goblin memory benchmark runner.

Seeds controlled facts into an isolated test user, probes the retrieval
system with structured queries, scores each result, and prints a report.

Usage (from repo root or apps/api/):
  python apps/api/benchmarks/memory/runner.py
  python apps/api/benchmarks/memory/runner.py --scenarios hardware-inventory personal-preferences
  python apps/api/benchmarks/memory/runner.py --keep        # don't delete test data
  python apps/api/benchmarks/memory/runner.py --dry-run     # plan only, no DB writes
  python apps/api/benchmarks/memory/runner.py --verbose -o results/memory_run.jsonl

Requires:
  - A configured database (SQLite dev DB or PostgreSQL)
  - A configured embedding service (needed for real similarity search)
    If the embedding service is unavailable, seeding will fail and the
    runner will exit early with a clear error.

Output:
  apps/api/benchmarks/memory/results/memory_<timestamp>.jsonl
  apps/api/benchmarks/memory/results/memory_<timestamp>.md
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
DATASET_PATH = HERE / "dataset" / "scenarios.jsonl"
RESULTS_DIR = HERE / "results"

# Bootstrap sys.path regardless of CWD.
_api_root = HERE.parents[2]  # apps/api/
_src = _api_root / "src"
for _p in (_src, _api_root):
    if _p.exists() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


# ---------------------------------------------------------------------------
# Dataset loading
# ---------------------------------------------------------------------------


def load_scenarios(
    scenario_ids: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    scenarios = []
    with open(DATASET_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            s = json.loads(line)
            if scenario_ids and s["scenario_id"] not in scenario_ids:
                continue
            scenarios.append(s)
    return scenarios


# ---------------------------------------------------------------------------
# Main benchmark coroutine
# ---------------------------------------------------------------------------


async def run_memory_benchmark(
    scenarios: List[Dict[str, Any]],
    *,
    run_id: str,
    keep_data: bool = False,
    retrieval_limit: int = 10,
    verbose: bool = False,
    dry_run: bool = False,
    out_path: Path,
) -> None:
    from benchmarks.memory.probe import probe_scenario  # noqa: PLC0415
    from benchmarks.memory.report import print_report, write_jsonl, write_markdown  # noqa: PLC0415
    from benchmarks.memory.scorer import ScenarioScore, score_query  # noqa: PLC0415
    from benchmarks.memory.seeder import delete_bench_user, seed_all  # noqa: PLC0415

    user_id = f"bench-{run_id}"
    total_facts = sum(len(s["facts"]) for s in scenarios)
    total_queries = sum(len(s["queries"]) for s in scenarios)

    print(f"\n  run_id:   {run_id}")
    print(f"  user_id:  {user_id}")
    print(f"  scenarios: {len(scenarios)}")
    print(f"  facts:    {total_facts}")
    print(f"  queries:  {total_queries}")
    print(f"  output:   {out_path}\n")

    if dry_run:
        print("  [dry-run] Stopping before DB writes.\n")
        for s in scenarios:
            print(
                f"  Scenario: {s['scenario_id']} — {len(s['facts'])} facts, {len(s['queries'])} queries"
            )
            for q in s["queries"]:
                exp = q.get("expected_fact_ids", [])
                print(f"    [{q['query_id']}] d={q['difficulty']} expected={exp}")
        return

    # --- PHASE 1: SEED -------------------------------------------------------
    print("  Phase 1: Seeding facts...")
    seed_result = await seed_all(scenarios, user_id, verbose=verbose)

    if not seed_result.fact_id_to_db_id:
        print("  ERROR: No facts were seeded. Check embedding service and DB config.")
        return

    seeded = len(seed_result.fact_id_to_db_id)
    failed = len(seed_result.failed)
    print(f"  Seeded {seeded}/{total_facts} facts ({failed} failed)")
    if failed:
        print(f"  Failed: {seed_result.failed}")

    # --- PHASE 2: PROBE -------------------------------------------------------
    print("\n  Phase 2: Probing retrieval...")
    scenario_scores: List[ScenarioScore] = []

    for scenario in scenarios:
        if verbose:
            print(f"\n  Probing scenario '{scenario['scenario_id']}'...")
        probe_results = await probe_scenario(
            scenario,
            user_id,
            retrieval_limit=retrieval_limit,
            verbose=verbose,
        )

        ss = ScenarioScore(
            scenario_id=scenario["scenario_id"],
            name=scenario["name"],
        )
        for query, retrieved, latency_ms in probe_results:
            qs = score_query(
                query=query,
                scenario=scenario,
                retrieved=retrieved,
                seed_result=seed_result,
                retrieval_latency_ms=latency_ms,
            )
            ss.query_scores.append(qs)
        scenario_scores.append(ss)

    # --- PHASE 3: REPORT ------------------------------------------------------
    print("\n  Phase 3: Computing scores and generating report...")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print_report(scenario_scores, run_id, user_id, verbose=verbose)
    write_jsonl(scenario_scores, out_path, run_id, user_id)
    md_path = out_path.with_suffix(".md")
    write_markdown(scenario_scores, md_path)
    print(f"  JSONL:    {out_path}")
    print(f"  Markdown: {md_path}\n")

    # --- PHASE 4: CLEANUP -----------------------------------------------------
    if not keep_data:
        deleted = await delete_bench_user(user_id)
        if verbose:
            print(f"  Cleaned up {deleted} DB rows for test user {user_id[:16]}")
    else:
        print(f"  --keep: leaving test data under user_id={user_id}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Goblin memory benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--scenarios",
        nargs="+",
        default=None,
        metavar="SCENARIO_ID",
        help="Scenario IDs to run (default: all)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Max facts to retrieve per query (default: 10)",
    )
    parser.add_argument(
        "--keep",
        action="store_true",
        help="Keep test user data in DB after run (for inspection)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the plan without making any DB writes",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print per-fact and per-query detail",
    )
    parser.add_argument(
        "-o",
        "--out",
        type=str,
        default=None,
        help="Output JSONL path (default: results/memory_<timestamp>.jsonl)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_id = uuid.uuid4().hex[:12]
    out_path = Path(args.out) if args.out else RESULTS_DIR / f"memory_{ts}.jsonl"

    scenarios = load_scenarios(scenario_ids=args.scenarios)
    if not scenarios:
        print("No scenarios matched the given filter.")
        sys.exit(1)

    print(f"\n  Goblin Memory Benchmark — {ts}")
    print("  " + "─" * 48)

    asyncio.run(
        run_memory_benchmark(
            scenarios,
            run_id=run_id,
            keep_data=args.keep,
            retrieval_limit=args.limit,
            verbose=args.verbose,
            dry_run=args.dry_run,
            out_path=out_path,
        )
    )


if __name__ == "__main__":
    main()
