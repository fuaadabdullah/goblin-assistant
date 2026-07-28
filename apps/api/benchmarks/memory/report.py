"""
Memory benchmark report formatter.

Prints a structured report to stdout and writes a markdown file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from .scorer import QueryScore, ScenarioScore


def _bar(value: float, width: int = 20) -> str:
    filled = int(round(max(0.0, value) * width))
    return "█" * filled + "░" * (width - filled)


def _score_badge(score: float) -> str:
    if score >= 0.8:
        return "EXCELLENT"
    if score >= 0.6:
        return "GOOD     "
    if score >= 0.4:
        return "FAIR     "
    if score >= 0.2:
        return "POOR     "
    return "FAILING  "


def print_report(
    scenario_scores: List[ScenarioScore],
    run_id: str,
    user_id: str,
    *,
    verbose: bool = False,
) -> str:
    lines = []
    lines.append("\n" + "=" * 76)
    lines.append("  GOBLIN MEMORY BENCHMARK")
    lines.append(f"  run: {run_id}   user: {user_id[:16]}")
    lines.append("=" * 76)

    # Per-scenario summary table
    lines.append(
        f"\n  {'Scenario':<28} {'Recall':>7} {'Relevance':>10} {'Correct':>8}"
        f" {'C.Waste':>8} {'Stale':>7} {'Score':>7}"
    )
    lines.append("  " + "-" * 74)

    all_scores = []
    for ss in scenario_scores:
        badge = _score_badge(ss.avg_memory_score)
        lines.append(
            f"  {ss.name[:28]:<28} {ss.avg_recall:>7.3f} {ss.avg_relevance:>10.3f}"
            f" {ss.avg_correctness:>8.3f} {ss.avg_context_waste:>8.3f}"
            f" {ss.avg_stale_contamination:>7.3f} {ss.avg_memory_score:>7.3f}  {badge}"
        )
        all_scores.append(ss.avg_memory_score)

    overall = sum(all_scores) / len(all_scores) if all_scores else 0.0
    lines.append("  " + "-" * 74)
    lines.append(
        f"  {'OVERALL':<28} {'':>7} {'':>10} {'':>8} {'':>8} {'':>7} {overall:>7.3f}  {_score_badge(overall)}"
    )

    # Visual score bars
    lines.append("\n" + "─" * 76)
    lines.append("  MEMORY SCORE  (Recall × Relevance × Correctness − ContextWaste)")
    lines.append("─" * 76)
    for ss in scenario_scores:
        s = ss.avg_memory_score
        bar = _bar(s, width=24)
        sign = "+" if s >= 0 else ""
        lines.append(f"  {ss.name[:26]:<26} [{bar}]  {sign}{s:.3f}")

    # Per-query detail
    lines.append("\n" + "─" * 76)
    lines.append("  QUERY DETAIL")
    lines.append("─" * 76)
    for ss in scenario_scores:
        lines.append(f"\n  {ss.name}")
        for qs in ss.query_scores:
            lines.append(
                f"    [{qs.query_id}] d={qs.difficulty}  "
                f"R={qs.recall:.2f} Rel={qs.relevance:.2f} Cor={qs.correctness:.2f} "
                f"Waste={qs.context_waste:.2f} Stale={qs.stale_contamination:.2f} "
                f"→ Score={qs.memory_score:+.3f}  ({qs.retrieval_latency_ms:.0f} ms)"
            )
            if verbose:
                lines.append(
                    f"       hits={qs.n_hits}/{qs.n_expected}  retrieved={qs.n_retrieved}  entities={qs.n_entities_matched}/{qs.n_entities_total}"
                )
                lines.append(f"       {qs.description}")

    # Diagnosis
    lines.append("\n" + "─" * 76)
    lines.append("  DIAGNOSIS")
    lines.append("─" * 76)
    _diagnose(lines, scenario_scores, overall)

    lines.append("\n" + "=" * 76 + "\n")
    output = "\n".join(lines)
    print(output)
    return output


def _diagnose(
    lines: List[str], scenario_scores: List[ScenarioScore], overall: float
) -> None:
    all_qs: List[QueryScore] = [qs for ss in scenario_scores for qs in ss.query_scores]
    if not all_qs:
        lines.append("  No queries scored.")
        return

    avg_recall = sum(q.recall for q in all_qs) / len(all_qs)
    avg_relevance = sum(q.relevance for q in all_qs) / len(all_qs)
    avg_correctness = sum(q.correctness for q in all_qs) / len(all_qs)
    avg_waste = sum(q.context_waste for q in all_qs) / len(all_qs)
    avg_stale = sum(q.stale_contamination for q in all_qs) / len(all_qs)
    avg_latency = sum(q.retrieval_latency_ms for q in all_qs) / len(all_qs)

    lines.append(
        f"  Recall:        {avg_recall:.3f}  (fraction of needed facts retrieved)"
    )
    lines.append(
        f"  Relevance:     {avg_relevance:.3f}  (fraction of retrieved facts that were needed)"
    )
    lines.append(
        f"  Correctness:   {avg_correctness:.3f}  (key entity values present in retrieved text)"
    )
    lines.append(
        f"  Context waste: {avg_waste:.3f}  (token share used by irrelevant facts)"
    )
    lines.append(
        f"  Stale contam.: {avg_stale:.3f}  (fraction of retrieved facts that are superseded)"
    )
    lines.append(f"  Avg latency:   {avg_latency:.0f} ms")

    lines.append("")
    if avg_recall < 0.5:
        lines.append(
            "  ⚠ LOW RECALL — retrieval is missing facts that exist in memory."
        )
        lines.append("    Check embedding quality and retrieval_limit settings.")
    if avg_relevance < 0.5:
        lines.append("  ⚠ LOW RELEVANCE — too much noise injected into context.")
        lines.append("    Reranker thresholds may need tightening.")
    if avg_stale > 0.15:
        lines.append(
            "  ⚠ HIGH STALE CONTAMINATION — outdated facts are being surfaced."
        )
        lines.append(
            "    Contradiction detection or recency weighting needs improvement."
        )
    if avg_waste > 0.4:
        lines.append("  ⚠ HIGH CONTEXT WASTE — irrelevant tokens consuming budget.")
        lines.append("    Token budget per retrieval layer may be too permissive.")
    if avg_latency > 500:
        lines.append(
            "  ⚠ HIGH RETRIEVAL LATENCY — >500 ms average is too slow for real-time."
        )

    if overall >= 0.7:
        lines.append("  ✓ Memory system is performing well. Score ≥ 0.7.")
    elif overall >= 0.4:
        lines.append(
            "  ~ Memory system is functional but has headroom for improvement."
        )
    else:
        lines.append("  ✗ Memory system needs significant work before v1 ship.")


def write_jsonl(
    scenario_scores: List[ScenarioScore],
    out_path: Path,
    run_id: str,
    user_id: str,
) -> None:
    with open(out_path, "w") as f:
        for ss in scenario_scores:
            for qs in ss.query_scores:
                record = {
                    "run_id": run_id,
                    "user_id": user_id,
                    "scenario_id": ss.scenario_id,
                    "scenario_name": ss.name,
                    "query_id": qs.query_id,
                    "difficulty": qs.difficulty,
                    "description": qs.description,
                    "n_expected": qs.n_expected,
                    "n_retrieved": qs.n_retrieved,
                    "n_hits": qs.n_hits,
                    "n_unexpected_hits": qs.n_unexpected_hits,
                    "recall": round(qs.recall, 4),
                    "relevance": round(qs.relevance, 4),
                    "correctness": round(qs.correctness, 4),
                    "context_waste": round(qs.context_waste, 4),
                    "stale_contamination": round(qs.stale_contamination, 4),
                    "memory_score": round(qs.memory_score, 4),
                    "retrieval_latency_ms": round(qs.retrieval_latency_ms, 1),
                    "tokens_retrieved_total": qs.tokens_retrieved_total,
                    "tokens_retrieved_relevant": qs.tokens_retrieved_relevant,
                }
                f.write(json.dumps(record) + "\n")


def write_markdown(
    scenario_scores: List[ScenarioScore],
    out_path: Path,
) -> None:
    lines = []
    lines.append("# Goblin Memory Benchmark\n")
    lines.append("## Score Formula\n")
    lines.append(
        "> **MemoryScore = Recall × Relevance × Correctness − ContextWaste**\n"
    )
    lines.append(
        "| Dimension | Definition |\n"
        "|---|---|\n"
        "| Recall | Fraction of expected facts that were retrieved |\n"
        "| Relevance | Fraction of retrieved facts that were actually needed (Precision) |\n"
        "| Correctness | Key entity values present in the retrieved text |\n"
        "| Context Waste | Token share consumed by irrelevant retrieved facts |\n"
        "| Stale Contamination | Fraction of retrieved facts that are superseded/outdated |\n"
    )
    lines.append("\n## Scenario Summary\n")
    lines.append(
        "| Scenario | Recall | Relevance | Correctness | Context Waste | Stale | **Score** |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    all_scores = []
    for ss in scenario_scores:
        lines.append(
            f"| {ss.name} | {ss.avg_recall:.3f} | {ss.avg_relevance:.3f}"
            f" | {ss.avg_correctness:.3f} | {ss.avg_context_waste:.3f}"
            f" | {ss.avg_stale_contamination:.3f} | **{ss.avg_memory_score:.3f}** |"
        )
        all_scores.append(ss.avg_memory_score)
    overall = sum(all_scores) / len(all_scores) if all_scores else 0.0
    lines.append(f"| **OVERALL** | | | | | | **{overall:.3f}** |")

    lines.append("\n## Query Detail\n")
    for ss in scenario_scores:
        lines.append(f"### {ss.name}\n")
        lines.append(
            "| Query | Difficulty | R | Rel | Cor | Waste | Stale | Score | Lat(ms) |"
        )
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for qs in ss.query_scores:
            lines.append(
                f"| {qs.query_id} | {qs.difficulty} | {qs.recall:.2f} | {qs.relevance:.2f}"
                f" | {qs.correctness:.2f} | {qs.context_waste:.2f} | {qs.stale_contamination:.2f}"
                f" | **{qs.memory_score:+.3f}** | {qs.retrieval_latency_ms:.0f} |"
            )
        lines.append("")

    out_path.write_text("\n".join(lines) + "\n")
