from __future__ import annotations

import asyncio

import pytest

import benchmarks.baselines as baselines
from benchmarks.memory.scorer import QueryScore
from benchmarks.memory.runner import load_scenarios
from benchmarks.runner import ALL_CATEGORIES, load_prompts, run_one


def test_intelligence_benchmark_dataset_covers_requested_categories() -> None:
    prompts = load_prompts()

    assert 50 <= len(prompts) <= 100
    assert len({prompt["id"] for prompt in prompts}) == len(prompts)

    categories = {prompt["category"] for prompt in prompts}
    required_categories = {
        "coding",
        "research",
        "reasoning",
        "casual",
        "long_context",
        "memory_retrieval",
        "finance",
        "tool_usage",
        "simple",
        "difficult",
    }

    assert required_categories.issubset(categories)
    assert categories.issubset(set(ALL_CATEGORIES))

    for prompt in prompts:
        assert prompt["prompt"].strip()
        assert isinstance(prompt.get("quality_hints", []), list)
        assert isinstance(prompt.get("tags", []), list)


def test_memory_benchmark_dataset_uses_controlled_facts_and_updates() -> None:
    scenarios = load_scenarios()

    assert scenarios
    assert any(
        scenario["scenario_id"] == "contradiction-handling"
        for scenario in scenarios
    )
    assert any(
        query.get("unexpected_fact_ids")
        for scenario in scenarios
        for query in scenario.get("queries", [])
    )
    assert any(
        fact.get("seed_order", 0) > 0
        for scenario in scenarios
        for fact in scenario.get("facts", [])
    )


def test_memory_score_formula_matches_scorecard() -> None:
    score = QueryScore(
        query_id="q-1",
        scenario_id="scenario-1",
        difficulty=3,
        description="formula check",
        n_expected=4,
        n_retrieved=2,
        n_hits=1,
        n_unexpected_hits=1,
        n_entities_matched=1,
        n_entities_total=2,
        tokens_retrieved_total=100,
        tokens_retrieved_relevant=60,
    )
    score.compute()

    expected = max(-1.0, (1 / 4) * (1 / 2) * (1 / 2) - 0.4)
    assert score.memory_score == pytest.approx(expected)
    assert score.stale_contamination == pytest.approx(0.5)


@pytest.mark.asyncio
async def test_intelligence_benchmark_records_prompt_ttft_and_fallback(monkeypatch):
    class FakeDispatcher:
        def _candidate_order(self, provider_id):
            if provider_id is None:
                return ["cheap", "strong"]
            return [provider_id]

        def _auto_configured_candidates(self, candidates):
            return list(candidates)

        def is_configured(self, provider_id):
            return True

        def get_provider_config(self, provider_id):
            return {
                "cheap": {"default_model": "cheap-model"},
                "strong": {"default_model": "strong-model"},
            }.get(provider_id, {"default_model": ""})

        async def dispatch(self, pid, model, payload, timeout_ms, stream=False):
            assert stream is True
            assert payload["messages"][0]["content"] == "Explain closures in JavaScript."

            async def stream():
                yield {"text": "Closures"}
                yield {"text": " capture"}
                yield {"text": " lexical scope."}

            return {"ok": True, "provider": "strong", "model": "strong-model", "stream": stream()}

    class FakeJudge:
        def score(self, response_text, prompt, *, succeeded):
            assert succeeded is True
            return 0.88

    monkeypatch.setattr(
        baselines,
        "STRATEGIES",
        {
            "goblin": lambda: (None, None),
            "cheapest": lambda: ("cheap", "cheap-model"),
            "strongest": lambda: ("strong", "strong-model"),
            "random": lambda: ("cheap", "cheap-model"),
        },
    )

    record = await run_one(
        {
            "id": "tool-001",
            "prompt": "Explain closures in JavaScript.",
            "category": "tool_usage",
            "difficulty": 2,
            "quality_hints": [],
        },
        "goblin",
        judge=FakeJudge(),
        judge_name="heuristic",
        dispatcher=FakeDispatcher(),
        timeout_ms=1000,
        run_id="run-123",
        concurrency_sem=asyncio.Semaphore(1),
    )

    assert record["prompt"] == "Explain closures in JavaScript."
    assert record["baseline_provider"] == "cheap"
    assert record["selected_provider"] == "strong"
    assert record["selected_model"] == "strong-model"
    assert record["used_fallback"] is True
    assert record["ttft_ms"] is not None and record["ttft_ms"] >= 0
    assert record["latency_ms"] is not None and record["latency_ms"] >= record["ttft_ms"]
    assert record["cost_usd"] is not None
