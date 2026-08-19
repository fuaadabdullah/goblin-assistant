from __future__ import annotations

import asyncio
import os
import sqlite3
import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from benchmarks import baselines
from benchmarks.memory import runner as memory_runner
from benchmarks.memory.runner import load_scenarios
from benchmarks.memory.scorer import QueryScore
from benchmarks.runner import ALL_CATEGORIES, load_prompts, run_benchmark, run_one
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.services.retrieval_service import _retrieval_service as retrieval_mod
from api.storage.models import Base, UserModel
from api.storage.vector_models import MemoryFactModel


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
    assert any(scenario["scenario_id"] == "contradiction-handling" for scenario in scenarios)
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


def test_memory_benchmark_runner_works_from_repo_root() -> None:
    repo_root = Path(__file__).resolve().parents[5]
    script = repo_root / "apps" / "api" / "benchmarks" / "memory" / "runner.py"

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--dry-run",
            "--scenarios",
            "hardware-inventory",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Scenario: hardware-inventory" in result.stdout
    assert "[dry-run] Stopping before DB writes." in result.stdout


def test_memory_benchmark_prepares_temporary_sqlite_copy(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    temp_db = memory_runner._prepare_benchmark_database()

    assert temp_db is not None
    assert temp_db.exists()
    assert os.environ["DATABASE_URL"].endswith(str(temp_db))

    with sqlite3.connect(temp_db) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(memory_facts)")}
        tables = {
            row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    assert {"memory_type", "source_kind", "source_id", "memory_state", "scope"}.issubset(columns)
    assert {"memory_entities", "memory_entity_relations"}.issubset(tables)


@pytest.mark.asyncio
async def test_sqlite_memory_retrieval_fallback_returns_seeded_fact(tmp_path, monkeypatch):
    temp_db = tmp_path / "retrieval.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{temp_db}")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            session.add(UserModel(id="bench-user", email="bench-user@example.com"))
            session.add(
                MemoryFactModel(
                    id="fact-1",
                    user_id="bench-user",
                    fact_text="Node 001 uses an RTX 3060 12 GB.",
                    fact_embedding=[0.1] * 1536,
                    category="hardware",
                )
            )
            await session.commit()

        @asynccontextmanager
        async def fake_get_readonly_db_context():
            async with session_factory() as session:
                yield session

        monkeypatch.setattr(retrieval_mod, "get_readonly_db_context", fake_get_readonly_db_context)

        service = retrieval_mod.RetrievalService()
        monkeypatch.setattr(
            service.embedding_service,
            "embed_text",
            AsyncMock(return_value=[0.1] * 1536),
        )

        results = await service.retrieve_memory_facts(
            user_id="bench-user",
            query="Which GPU is Node 001 running?",
            k=5,
        )

        assert results
        assert results[0]["content"] == "Node 001 uses an RTX 3060 12 GB."
        assert results[0]["source_type"] == "memory"
    finally:
        await engine.dispose()


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


def test_benchmark_baselines_prefer_available_providers(monkeypatch) -> None:
    class _ProviderStub:
        def __init__(self, *, allowed: bool) -> None:
            self._allowed = allowed

        def should_attempt(self, *, canary: bool = False) -> bool:
            _ = canary
            return self._allowed

        def is_available(self) -> bool:
            return self._allowed

    provider_map = {
        "dead": _ProviderStub(allowed=False),
        "cheap": _ProviderStub(allowed=True),
        "strong": _ProviderStub(allowed=True),
    }

    dispatcher = SimpleNamespace(
        _cheapest_order=lambda: ["dead", "cheap", "strong"],
        _hybrid_order=lambda: ["dead", "strong", "cheap"],
        top_providers_for=lambda capability, prefer_cost=False, limit=1: [
            "dead",
            "strong",
        ],
        _configs={
            "dead": {"default_model": "dead-model"},
            "cheap": {"default_model": "cheap-model"},
            "strong": {"default_model": "strong-model"},
        },
        list_providers=lambda include_hidden=False: [
            {"id": "dead", "default_model": "dead-model"},
            {"id": "cheap", "default_model": "cheap-model"},
            {"id": "strong", "default_model": "strong-model"},
        ],
        is_configured=lambda provider_id: provider_id in provider_map,
        _ensure_provider=lambda provider_id: provider_map.get(provider_id),  # noqa: PLW0108
    )

    monkeypatch.setattr(baselines, "_dispatcher", lambda: dispatcher)
    monkeypatch.setattr(baselines.random, "choice", lambda providers: providers[0])

    assert baselines.cheapest_provider() == ("cheap", "cheap-model")
    assert baselines.strongest_provider() == ("strong", "strong-model")
    assert baselines.random_provider() == ("cheap", "cheap-model")


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


@pytest.mark.asyncio
async def test_run_benchmark_primes_health_cache_before_dispatch(monkeypatch, tmp_path):
    fake_dispatcher_module = ModuleType("api.providers.dispatcher")
    fake_dispatcher_module.dispatcher = object()
    monkeypatch.setitem(sys.modules, "api.providers.dispatcher", fake_dispatcher_module)

    refresh = AsyncMock(return_value={})
    monkeypatch.setattr("api.services.provider_health.health_monitor.refresh", refresh)
    monkeypatch.setattr(
        "benchmarks.runner.run_one",
        AsyncMock(return_value={"prompt_id": "simple-001", "strategy": "goblin"}),
    )

    prompts = [
        {
            "id": "simple-001",
            "prompt": "Say hello in one sentence.",
            "category": "simple",
            "difficulty": 1,
        }
    ]

    await run_benchmark(
        prompts,
        ["goblin"],
        out_path=tmp_path / "bench.jsonl",
        concurrency=1,
    )

    refresh.assert_awaited_once_with(include_hidden=False, deep_probe=True)
