"""
Benchmark report generator.

Reads a JSONL results file and prints a comparison table across strategies.
Also writes a markdown report to results/report.md.

Usage:
  python -m benchmarks.report results/run_<timestamp>.jsonl
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

# Bootstrap sys.path so this module is runnable from any CWD.
_here = Path(__file__).resolve().parent
for _p in (_here.parent / "src", _here.parent):
    if _p.exists() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


def load_results(path: str) -> List[Dict[str, Any]]:
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _mean(values: List[float]) -> float:
    return statistics.mean(values) if values else 0.0


def _pct(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "  —"
    return f"{100 * numerator / denominator:4.0f}%"


def aggregate(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Returns per-strategy aggregate metrics:
      n, success_rate, fallback_rate, avg_cost_usd, avg_latency_ms,
      avg_quality, total_cost_usd, provider_counts, category_quality
    """
    buckets: Dict[str, List[Dict]] = defaultdict(list)
    for row in rows:
        buckets[row["strategy"]].append(row)

    result = {}
    for strategy, records in buckets.items():
        n = len(records)
        successes = [r for r in records if r.get("success")]
        fallbacks = [r for r in records if r.get("used_fallback")]
        costs = [r["cost_usd"] for r in successes if r.get("cost_usd") is not None]
        latencies = [
            r["latency_ms"] for r in successes if r.get("latency_ms") is not None
        ]
        qualities = [
            r["quality_score"] for r in records if r.get("quality_score") is not None
        ]

        provider_counts: Dict[str, int] = defaultdict(int)
        for r in successes:
            if r.get("selected_provider"):
                provider_counts[r["selected_provider"]] += 1

        category_quality: Dict[str, List[float]] = defaultdict(list)
        for r in records:
            if r.get("quality_score") is not None:
                category_quality[r.get("category", "unknown")].append(
                    r["quality_score"]
                )

        result[strategy] = {
            "n": n,
            "success_count": len(successes),
            "fallback_count": len(fallbacks),
            "avg_cost_usd": _mean(costs),
            "avg_latency_ms": _mean(latencies),
            "avg_quality": _mean(qualities),
            "total_cost_usd": sum(costs),
            "provider_counts": dict(provider_counts),
            "category_quality": {k: _mean(v) for k, v in category_quality.items()},
        }
    return result


def _bar(value: float, max_value: float, width: int = 20) -> str:
    filled = int(round(value / max(max_value, 1e-9) * width))
    return "█" * filled + "░" * (width - filled)


def print_summary(agg: Dict[str, Dict[str, Any]]) -> str:
    strategies = sorted(agg.keys())
    lines = []

    lines.append("\n" + "=" * 72)
    lines.append("  GOBLIN INTELLIGENCE LAYER BENCHMARK")
    lines.append("=" * 72)

    # Main comparison table
    header = f"{'Strategy':<12} {'N':>4} {'Success':>8} {'Fallback':>9} {'Avg Cost':>10} {'Avg Lat(ms)':>12} {'Quality':>9}"
    lines.append("\n" + header)
    lines.append("-" * 72)

    for s in strategies:
        d = agg[s]
        lines.append(
            f"{s:<12} {d['n']:>4} "
            f"{_pct(d['success_count'], d['n']):>8} "
            f"{_pct(d['fallback_count'], d['n']):>9} "
            f"${d['avg_cost_usd']:>8.5f} "
            f"{d['avg_latency_ms']:>11.0f} "
            f"{d['avg_quality']:>8.3f}"
        )

    # Cost efficiency vs quality scatter (text-based)
    lines.append("\n" + "─" * 72)
    lines.append("  COST vs QUALITY (normalized — lower left = better value)")
    lines.append("─" * 72)
    max_cost = max((d["avg_cost_usd"] for d in agg.values()), default=1.0)
    for s in strategies:
        d = agg[s]
        cost_bar = _bar(d["avg_cost_usd"], max_cost, width=16)
        q = d["avg_quality"]
        lines.append(f"  {s:<12} cost [{cost_bar}]  quality {q:.3f}")

    # Per-category quality breakdown
    categories = sorted(
        {cat for d in agg.values() for cat in d["category_quality"].keys()}
    )
    if categories:
        lines.append("\n" + "─" * 72)
        lines.append("  QUALITY BY CATEGORY")
        lines.append("─" * 72)
        cat_header = f"  {'Category':<18}" + "".join(
            f"{s[:10]:>12}" for s in strategies
        )
        lines.append(cat_header)
        lines.append("  " + "-" * 66)
        for cat in categories:
            row = f"  {cat:<18}"
            for s in strategies:
                val = agg[s]["category_quality"].get(cat)
                row += f"{val:>12.3f}" if val is not None else f"{'—':>12}"
            lines.append(row)

    # Provider distribution (for goblin strategy)
    if "goblin" in agg:
        pc = agg["goblin"].get("provider_counts", {})
        if pc:
            lines.append("\n" + "─" * 72)
            lines.append("  GOBLIN PROVIDER SELECTION DISTRIBUTION")
            lines.append("─" * 72)
            total = sum(pc.values())
            for pid, count in sorted(pc.items(), key=lambda x: -x[1]):
                pct_str = f"{100 * count / total:.0f}%"
                lines.append(f"  {pid:<20} {count:>4} calls  ({pct_str})")

    # Verdict
    lines.append("\n" + "─" * 72)
    lines.append("  VERDICT")
    lines.append("─" * 72)

    if "goblin" in agg and "strongest" in agg and "cheapest" in agg:
        g = agg["goblin"]
        s = agg["strongest"]
        c = agg["cheapest"]

        quality_gap_vs_strongest = g["avg_quality"] - s["avg_quality"]
        cost_savings_vs_strongest = (
            (1 - g["avg_cost_usd"] / s["avg_cost_usd"]) * 100
            if s["avg_cost_usd"] > 0
            else 0
        )
        quality_vs_cheapest = g["avg_quality"] - c["avg_quality"]

        lines.append(
            f"  Goblin vs strongest:  quality delta {quality_gap_vs_strongest:+.3f},"
            f"  cost savings {cost_savings_vs_strongest:.1f}%"
        )
        lines.append(
            f"  Goblin vs cheapest:   quality delta {quality_vs_cheapest:+.3f}"
        )

        if quality_gap_vs_strongest >= -0.05 and cost_savings_vs_strongest >= 15:
            lines.append(
                "\n  ✓ Goblin achieves comparable quality at meaningfully lower cost."
            )
            lines.append("    The routing moat is working.")
        elif quality_gap_vs_strongest >= 0 and cost_savings_vs_strongest >= 5:
            lines.append(
                "\n  ~ Goblin is cost-efficient but the savings margin is thin."
            )
            lines.append("    Check if cheapest-capable model thresholds need tuning.")
        elif quality_vs_cheapest > 0.05:
            lines.append(
                "\n  ~ Goblin improves over cheapest but costs more than strongest."
            )
            lines.append("    Routing logic may be over-selecting premium providers.")
        else:
            lines.append("\n  ✗ Goblin's routing is not yet differentiated.")
            lines.append(
                "    Review the scoring weights and context window thresholds."
            )

    lines.append("\n" + "=" * 72 + "\n")
    output = "\n".join(lines)
    print(output)
    return output


def write_markdown(agg: Dict[str, Dict[str, Any]], out_path: Path) -> None:
    strategies = sorted(agg.keys())
    lines = []
    lines.append("# Goblin Intelligence Layer Benchmark\n")
    lines.append("## Summary\n")
    lines.append(
        "| Strategy | N | Success | Fallback | Avg Cost ($) | Avg Latency (ms) | Quality |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    for s in strategies:
        d = agg[s]
        lines.append(
            f"| {s} | {d['n']} "
            f"| {_pct(d['success_count'], d['n'])} "
            f"| {_pct(d['fallback_count'], d['n'])} "
            f"| {d['avg_cost_usd']:.5f} "
            f"| {d['avg_latency_ms']:.0f} "
            f"| {d['avg_quality']:.3f} |"
        )

    categories = sorted(
        {cat for d in agg.values() for cat in d["category_quality"].keys()}
    )
    if categories:
        lines.append("\n## Quality by Category\n")
        header = "| Category |" + "".join(f" {s} |" for s in strategies)
        sep = "|---|" + "".join("---|" for _ in strategies)
        lines.append(header)
        lines.append(sep)
        for cat in categories:
            row = f"| {cat} |"
            for s in strategies:
                val = agg[s]["category_quality"].get(cat)
                row += f" {val:.3f} |" if val is not None else " — |"
            lines.append(row)

    out_path.write_text("\n".join(lines) + "\n")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m benchmarks.report <results.jsonl>")
        sys.exit(1)

    results_path = sys.argv[1]
    rows = load_results(results_path)
    if not rows:
        print("No results found in file.")
        sys.exit(1)

    agg = aggregate(rows)
    print_summary(agg)

    out_md = Path(results_path).with_suffix(".md")
    write_markdown(agg, out_md)
    print(f"Markdown report written to {out_md}")


if __name__ == "__main__":
    main()
