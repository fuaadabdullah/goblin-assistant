"""Tests for routing/evaluation.py — the routing benchmark harness.

These run the real policy engine + provider scoring stack against the shipped
BENCHMARK_SUITE, so a passing suite doubles as a regression guard: if someone
edits config/routing_policies.toml and breaks its semantics, these fail.
"""

from __future__ import annotations

from api.routing.evaluation import (
    BENCHMARK_SUITE,
    BenchmarkReport,
    production_reliability_snapshot,
    run_routing_benchmark,
)
from api.routing.routing_pipeline import ROUTING_STAGE_ORDER


class TestRoutingBenchmarkSuite:
    def test_all_shipped_cases_pass(self):
        report = run_routing_benchmark()
        failures = [c for c in report.cases if not c.passed]
        assert not failures, f"benchmark regressions: {[(c.case_id, c.reason) for c in failures]}"
        assert report.pass_rate == 1.0

    def test_returns_a_result_per_case(self):
        report = run_routing_benchmark()
        assert len(report.cases) == len(BENCHMARK_SUITE)

    def test_report_is_correct_type(self):
        report = run_routing_benchmark()
        assert isinstance(report, BenchmarkReport)

    def test_trivial_case_wins_fast_tier_majority_of_trials(self):
        report = run_routing_benchmark()
        case = next(c for c in report.cases if c.case_id == "trivial_arithmetic")
        assert case.tier_win_rate >= 0.5
        assert "trivial_request" in case.matched_policies

    def test_confidential_case_restricts_to_local_tier(self):
        report = run_routing_benchmark()
        case = next(c for c in report.cases if c.case_id == "confidential_request")
        # restriction is a hard filter (not a score boost), so this is deterministic
        assert case.chosen_provider in {"gcp_vm", "ollama_local", "aliyun"}
        assert "confidential" in case.matched_policies

    def test_baseline_case_matches_no_policy(self):
        report = run_routing_benchmark()
        case = next(c for c in report.cases if c.case_id == "normal_chat_baseline")
        assert case.matched_policies == []

    def test_cases_include_pipeline_stage_timings(self):
        report = run_routing_benchmark()
        for case in report.cases:
            assert list(case.stage_durations_ms) == list(ROUTING_STAGE_ORDER)
            assert all(duration >= 0 for duration in case.stage_durations_ms.values())


class TestCostQualityFrontier:
    def test_frontier_has_an_entry_per_scored_provider(self):
        report = run_routing_benchmark()
        frontier_ids = {row["provider_id"] for row in report.cost_quality_frontier}
        # every provider scored in at least one case should appear
        all_scored = {pid for c in report.cases for pid in c.candidate_scores}
        assert frontier_ids == all_scored

    def test_frontier_sorted_by_score_descending(self):
        report = run_routing_benchmark()
        scores = [row["avg_router_score"] for row in report.cost_quality_frontier]
        assert scores == sorted(scores, reverse=True)

    def test_known_provider_has_real_pricing(self):
        report = run_routing_benchmark()
        openai_row = next(
            (r for r in report.cost_quality_frontier if r["provider_id"] == "openai"), None
        )
        assert openai_row is not None
        assert openai_row["cost_input_per1k"] > 0


class TestProductionReliabilitySnapshot:
    def test_returns_a_dict(self):
        snapshot = production_reliability_snapshot()
        assert isinstance(snapshot, dict)

    def test_entries_have_expected_shape(self):
        snapshot = production_reliability_snapshot()
        for pid, stats in snapshot.items():
            assert "success_rate" in stats
            assert "ewma_latency_ms" in stats
