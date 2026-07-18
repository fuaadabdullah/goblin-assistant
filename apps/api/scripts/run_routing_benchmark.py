#!/usr/bin/env python3
"""
Run the GoblinOS routing benchmark and print a report.

Usage:
    python scripts/run_routing_benchmark.py              # human-readable report
    python scripts/run_routing_benchmark.py --json        # machine-readable
    python scripts/run_routing_benchmark.py --json --out /tmp/routing_benchmark.json

Scope: this benchmarks ROUTING DECISIONS (policy rules + provider scoring),
not live model output quality. No network calls, no API keys required.
See apps/api/src/api/routing/evaluation.py module docstring for what this
does and does not prove.
"""

import argparse
import json
import os
import sys

_here = os.path.dirname(os.path.abspath(__file__))
_src = os.path.join(_here, "..", "src")
sys.path.insert(0, _src)

from api.routing.evaluation import (  # noqa: E402
    production_reliability_snapshot,
    run_routing_benchmark,
)


def _print_human(report) -> None:
    print("=" * 72)
    print("GoblinOS Routing Benchmark")
    print("=" * 72)
    for case in report.cases:
        status = "PASS" if case.passed else "FAIL"
        print(f"[{status}] {case.case_id}: {case.description}")
        print(f"       matched_policies={case.matched_policies}")
        print(f"       chosen_provider={case.chosen_provider} (score={case.chosen_score:.4f})")
        if case.stage_durations_ms:
            timings = ", ".join(
                f"{stage}={duration:.4f}ms" for stage, duration in case.stage_durations_ms.items()
            )
            print(f"       stage_durations_ms={timings}")
        if not case.passed:
            print(f"       reason: {case.reason}")
        print()

    print(f"Pass rate: {report.pass_rate * 100:.1f}% ({len(report.cases)} cases)")
    print()
    print("-" * 72)
    print("Cost vs. router-assigned score (not a measurement of response quality)")
    print("-" * 72)
    print(f"{'provider':<16}{'avg_score':>12}{'$/1k in':>12}{'$/1k out':>12}")
    for row in report.cost_quality_frontier:
        print(
            f"{row['provider_id']:<16}{row['avg_router_score']:>12.4f}"
            f"{row['cost_input_per1k']:>12.5f}{row['cost_output_per1k']:>12.5f}"
        )

    print()
    print("-" * 72)
    print("Production reliability (real traffic since process start, if any)")
    print("-" * 72)
    reliability = production_reliability_snapshot()
    if not reliability:
        print("(no traffic recorded in this process — this is a fresh in-memory registry)")
    else:
        for pid, stats in reliability.items():
            print(
                f"{pid:<16}success_rate={stats['success_rate']:.3f}  "
                f"ewma_latency_ms={stats['ewma_latency_ms']:.1f}"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print JSON instead of a table")
    parser.add_argument("--out", help="also write JSON report to this path")
    args = parser.parse_args()

    report = run_routing_benchmark()

    payload = {
        "pass_rate": report.pass_rate,
        "cases": [
            {
                "case_id": c.case_id,
                "description": c.description,
                "matched_policies": c.matched_policies,
                "chosen_provider": c.chosen_provider,
                "chosen_score": c.chosen_score,
                "candidate_scores": c.candidate_scores,
                "stage_durations_ms": c.stage_durations_ms,
                "passed": c.passed,
                "reason": c.reason,
            }
            for c in report.cases
        ],
        "cost_quality_frontier": report.cost_quality_frontier,
        "production_reliability": production_reliability_snapshot(),
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        _print_human(report)

    if args.out:
        with open(args.out, "w") as f:
            json.dump(payload, f, indent=2)

    return 0 if report.pass_rate == 1.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
