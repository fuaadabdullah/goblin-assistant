"""
pytest-benchmark tests for hot-path pure functions.

Run with:
    pytest src/api/tests/test_benchmarks.py -v --benchmark-sort=mean

Add --benchmark-histogram to generate an HTML histogram, or
--benchmark-save=<name> to persist results for comparison.
"""

import random
import string
from typing import Any

import pytest

from api.core.tokenization import count_tokens, trim_to_tokens
from api.services.message_classifier import MessageClassifier
from api.services.retrieval_service._context_bundle import build_context_bundle
from api.services.retrieval_service._token_budget import (
    apply_context_token_budget,
    estimate_tokens,
    trim_item_to_token_budget,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CLASSIFIER = MessageClassifier()


def _random_text(n_words: int) -> str:
    words = [
        "".join(random.choices(string.ascii_lowercase, k=random.randint(3, 10)))
        for _ in range(n_words)
    ]
    return " ".join(words)


def _make_item(n_words: int, source_type: str = "message") -> dict:
    return {
        "content": _random_text(n_words),
        "source_type": source_type,
        "score": random.random(),
        "metadata": {},
    }


def _make_bundle(n_each: int) -> list[dict[str, Any]]:
    """Build a realistic context bundle with n_each items per bucket."""
    source_types = ["message", "summary", "memory", "document", "task", "ephemeral"]
    items = []
    for st in source_types:
        for _ in range(n_each):
            items.append(_make_item(random.randint(20, 80), source_type=st))
    return items


# ---------------------------------------------------------------------------
# estimate_tokens
# ---------------------------------------------------------------------------


def test_bench_estimate_tokens_short(benchmark):
    benchmark(estimate_tokens, "hello world")


def test_bench_estimate_tokens_medium(benchmark):
    text = _random_text(200)
    benchmark(estimate_tokens, text)


def test_bench_estimate_tokens_long(benchmark):
    text = _random_text(2000)
    benchmark(estimate_tokens, text)


# ---------------------------------------------------------------------------
# trim_item_to_token_budget
# ---------------------------------------------------------------------------


def test_bench_trim_item_fits(benchmark):
    item = _make_item(50)
    benchmark(trim_item_to_token_budget, item, 500)


def test_bench_trim_item_needs_trim(benchmark):
    item = _make_item(500)
    benchmark(trim_item_to_token_budget, item, 100)


# ---------------------------------------------------------------------------
# apply_context_token_budget
# ---------------------------------------------------------------------------


@pytest.fixture
def small_bundle():
    return {
        "memory_facts": [_make_item(50) for _ in range(5)],
        "summaries": [_make_item(80) for _ in range(5)],
        "documents": [_make_item(200) for _ in range(3)],
        "messages": [_make_item(60) for _ in range(20)],
        "ephemeral_messages": [_make_item(40) for _ in range(10)],
        "tasks": [_make_item(30) for _ in range(5)],
    }


@pytest.fixture
def large_bundle():
    return {
        "memory_facts": [_make_item(100) for _ in range(20)],
        "summaries": [_make_item(150) for _ in range(20)],
        "documents": [_make_item(400) for _ in range(10)],
        "messages": [_make_item(80) for _ in range(100)],
        "ephemeral_messages": [_make_item(50) for _ in range(50)],
        "tasks": [_make_item(40) for _ in range(20)],
    }


def test_bench_token_budget_small(benchmark, small_bundle):
    def run():
        b = {k: list(v) for k, v in small_bundle.items()}
        return apply_context_token_budget(b, max_tokens=2000)

    benchmark(run)


def test_bench_token_budget_large(benchmark, large_bundle):
    def run():
        b = {k: list(v) for k, v in large_bundle.items()}
        return apply_context_token_budget(b, max_tokens=4000)

    benchmark(run)


def test_bench_token_budget_zero_budget(benchmark, large_bundle):
    """Degenerate case: zero budget clears all buckets."""

    def run():
        b = {k: list(v) for k, v in large_bundle.items()}
        return apply_context_token_budget(b, max_tokens=0)

    benchmark(run)


# ---------------------------------------------------------------------------
# build_context_bundle
# ---------------------------------------------------------------------------


def test_bench_build_context_bundle_small(benchmark):
    items = _make_bundle(n_each=5)

    def run():
        return build_context_bundle(
            query="what is my portfolio risk?",
            user_id="user-bench",
            conversation_id="conv-bench",
            all_context=items,
            max_tokens=2000,
            degraded_status={"degraded_mode": False, "reason": None},
        )

    benchmark(run)


def test_bench_build_context_bundle_large(benchmark):
    items = _make_bundle(n_each=30)

    def run():
        return build_context_bundle(
            query="summarise my recent conversations",
            user_id="user-bench",
            conversation_id="conv-bench",
            all_context=items,
            max_tokens=6000,
            degraded_status={"degraded_mode": False, "reason": None},
        )

    benchmark(run)


# ---------------------------------------------------------------------------
# MessageClassifier.classify_message
# ---------------------------------------------------------------------------

_BENCH_MESSAGES = {
    "chat_short": ("hey how are you?", "user"),
    "chat_long": (
        "I was wondering if you could help me think through this problem. "
        "It's related to optimising a sorting algorithm for large datasets.",
        "user",
    ),
    "fact": ("I am a senior software engineer with 10 years of experience in Python.", "user"),
    "preference": ("I prefer functional programming over object-oriented patterns.", "user"),
    "finance_entity": (
        "What is the current price of AAPL stock and how does it compare to MSFT?",
        "user",
    ),
    "finance_risk": (
        "Can you calculate the value at risk (VaR) and Sharpe ratio for my portfolio?",
        "user",
    ),
    "finance_macro": (
        "How will the upcoming FOMC rate decision impact the yield curve inversion?",
        "user",
    ),
    "task_result": (
        "Done! I have successfully implemented the authentication middleware and all tests pass.",
        "assistant",
    ),
    "learning": (
        "Can you explain the concept of duration and convexity in fixed income? "
        "I am studying for my CFA exam.",
        "user",
    ),
    "noise": ("ok", "user"),
}


@pytest.mark.parametrize("label,args", _BENCH_MESSAGES.items())
def test_bench_classify_message(benchmark, label, args):
    content, role = args
    benchmark(_CLASSIFIER.classify_message, content, role)


# ---------------------------------------------------------------------------
# core.tokenization
# ---------------------------------------------------------------------------


def test_bench_count_tokens_short(benchmark):
    benchmark(count_tokens, "hello world from goblin assistant")


def test_bench_count_tokens_medium(benchmark):
    text = _random_text(300)
    benchmark(count_tokens, text)


def test_bench_count_tokens_long(benchmark):
    text = _random_text(3000)
    benchmark(count_tokens, text)


def test_bench_trim_to_tokens_no_trim(benchmark):
    text = _random_text(100)
    benchmark(trim_to_tokens, text, 500)


def test_bench_trim_to_tokens_heavy_trim(benchmark):
    text = _random_text(2000)
    benchmark(trim_to_tokens, text, 200)


# ---------------------------------------------------------------------------
# routing.feature_extractor — hot path for every provider selection decision
# ---------------------------------------------------------------------------

from api.routing.feature_extractor import FeatureExtractor  # noqa: E402

_FEATURE_EXTRACTOR = FeatureExtractor()

_SHORT_PROMPT = "What is the capital of France?"
_MEDIUM_PROMPT = _random_text(120)  # ~600 chars, bucket 1
_LONG_PROMPT = _random_text(500)  # ~2500 chars, bucket 2

_HISTORY_10 = [{"role": "user", "content": "msg"}] * 10

_SNAPSHOT_6 = {
    pid: {"ewma_latency_ms": float(200 + i * 300), "success_rate": 0.9 - i * 0.05}
    for i, pid in enumerate(["openai", "anthropic", "gemini", "deepseek", "groq", "ollama"])
}
_COSTS_6 = {
    "openai": (0.005, 0.015),
    "anthropic": (0.008, 0.024),
    "gemini": (0.002, 0.006),
    "deepseek": (0.001, 0.002),
    "groq": (0.0005, 0.001),
    "ollama": (0.0, 0.0),
}
_CANDIDATES_6 = list(_COSTS_6)


def test_bench_feature_extract_short_no_history(benchmark):
    benchmark(
        _FEATURE_EXTRACTOR.extract_request,
        _SHORT_PROMPT,
        "chat",
        [],
    )


def test_bench_feature_extract_medium_with_history(benchmark):
    benchmark(
        _FEATURE_EXTRACTOR.extract_request,
        _MEDIUM_PROMPT,
        "research",
        _HISTORY_10,
    )


def test_bench_feature_extract_long_all_signals(benchmark):
    prompt = "Please find, search, schedule and explain step by step: " + _LONG_PROMPT
    benchmark(
        _FEATURE_EXTRACTOR.extract_request,
        prompt,
        "code",
        _HISTORY_10,
        "coding",
        0.85,
    )


def test_bench_extract_providers_6_candidates(benchmark):
    benchmark(
        _FEATURE_EXTRACTOR.extract_providers,
        _CANDIDATES_6,
        _COSTS_6,
        _SNAPSHOT_6,
    )


def test_bench_extract_providers_6_with_health(benchmark):
    health = {pid: (i % 2 == 0) for i, pid in enumerate(_CANDIDATES_6)}
    benchmark(
        _FEATURE_EXTRACTOR.extract_providers,
        _CANDIDATES_6,
        _COSTS_6,
        _SNAPSHOT_6,
        health,
    )
