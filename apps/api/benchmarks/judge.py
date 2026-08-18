"""
Answer quality scoring for benchmark runs.

Two scorers are available:

  HeuristicJudge  — fast, no API calls. Scores based on response length,
                    keyword presence, absence of refusal patterns, and
                    structural signals (code blocks, lists). Appropriate for
                    CI runs and local development.

  LLMJudge        — calls a configurable provider with a rubric prompt and
                    parses the 0-10 score it returns. Accurate but adds cost
                    and latency. Enable with --llm-judge.

Both return a float in [0.0, 1.0].
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


REFUSAL_PATTERNS: list[re.Pattern] = [
    re.compile(r"\bI cannot\b", re.I),
    re.compile(r"\bI'm unable to\b", re.I),
    re.compile(r"\bI don't have access to\b", re.I),
    re.compile(r"\bI'm sorry, I can't\b", re.I),
    re.compile(r"\bas an AI\b", re.I),
    re.compile(r"\bI don't have real-time\b", re.I),
]

ERROR_PATTERNS: list[re.Pattern] = [
    re.compile(r"\bAPI error\b", re.I),
    re.compile(r"\bprovider error\b", re.I),
    re.compile(r"\bfailed to generate\b", re.I),
    re.compile(r"\btimeout\b", re.I),
]


def _has_code_block(text: str) -> bool:
    return bool(re.search(r"```", text))


def _has_list(text: str) -> bool:
    return bool(re.search(r"^\s*[-*•]\s+", text, re.MULTILINE))


def _word_count(text: str) -> int:
    return len(text.split())


def _refusal_penalty(text: str) -> float:
    for pat in REFUSAL_PATTERNS:
        if pat.search(text):
            return 0.3
    return 0.0


def _error_penalty(text: str) -> float:
    for pat in ERROR_PATTERNS:
        if pat.search(text):
            return 0.5
    return 0.0


def _keyword_score(text: str, hints: List[str]) -> float:
    if not hints:
        return 0.5
    hits = sum(1 for h in hints if h.lower() in text.lower())
    return hits / len(hints)


@dataclass
class HeuristicJudge:
    """
    Score a response without any additional API calls.

    Weights:
      40% — keyword coverage (expected terms from prompt metadata)
      30% — length adequacy (proportion of expected min length reached)
      20% — structural quality (code blocks, lists, sentence variety)
      10% — absence of refusals / error strings
    """

    def score(
        self,
        response_text: str,
        prompt: Dict[str, Any],
        *,
        succeeded: bool,
    ) -> float:
        if not succeeded or not response_text.strip():
            return 0.0

        text = response_text.strip()
        hints: List[str] = prompt.get("quality_hints", [])
        max_tokens: int = prompt.get("max_tokens", 200)
        expected_words = max_tokens * 0.6

        # Keyword coverage
        kw = _keyword_score(text, hints)

        # Length adequacy
        words = _word_count(text)
        length_score = min(1.0, words / max(1, expected_words))

        # Structural quality
        structural = 0.0
        if _has_code_block(text) and any(
            t in prompt.get("tags", [])
            for t in ("python", "sql", "typescript", "bash", "code-review")
        ):
            structural += 0.6
        if _has_list(text):
            structural += 0.3
        sentence_count = len(re.split(r"[.!?]+", text))
        if sentence_count >= 3:
            structural += 0.1
        structural = min(1.0, structural)

        # Refusal / error penalties
        refusal_pen = _refusal_penalty(text)
        error_pen = _error_penalty(text)

        raw = (
            0.40 * kw
            + 0.30 * length_score
            + 0.20 * structural
            + 0.10 * (1.0 - refusal_pen - error_pen)
        )
        return max(0.0, min(1.0, raw))


@dataclass
class LLMJudge:
    """
    Score using a second LLM call with a rubric.

    The judge model receives the original prompt and the response and
    returns a score on a 0-10 scale. This is then normalized to [0, 1].

    Uses the 'strongest' provider by default. Results are cached in memory
    to avoid re-scoring the same (prompt_id, response_hash) pair.
    """

    provider_id: Optional[str] = None
    model: Optional[str] = None
    _cache: Dict[str, float] = field(default_factory=dict, init=False, repr=False)

    RUBRIC = (
        "You are an impartial evaluator. "
        "Score the following AI response on a scale from 0 to 10 based on:\n"
        "- Correctness (does it answer the question accurately?)\n"
        "- Completeness (does it cover what was asked?)\n"
        "- Clarity (is it easy to understand?)\n\n"
        "Output ONLY a single integer between 0 and 10. Nothing else.\n\n"
        "PROMPT: {prompt}\n\n"
        "RESPONSE: {response}"
    )

    async def score(
        self,
        response_text: str,
        prompt: Dict[str, Any],
        *,
        succeeded: bool,
    ) -> float:
        if not succeeded or not response_text.strip():
            return 0.0

        import hashlib  # noqa: PLC0415

        cache_key = hashlib.sha256(
            f"{prompt['id']}:{response_text[:500]}".encode()
        ).hexdigest()
        if cache_key in self._cache:
            return self._cache[cache_key]

        from api.providers.dispatcher import invoke_provider  # noqa: PLC0415

        judge_prompt = self.RUBRIC.format(
            prompt=prompt["prompt"][:800],
            response=response_text[:1200],
        )

        pid, model = self.provider_id, self.model
        if pid is None:
            from benchmarks.baselines import strongest_provider  # noqa: PLC0415

            pid, model = strongest_provider()

        result = await invoke_provider(
            pid=pid,
            model=model,
            payload={
                "messages": [{"role": "user", "content": judge_prompt}],
            },
            timeout_ms=15_000,
        )

        raw_score = 5.0
        if result.get("ok") and result.get("text"):
            match = re.search(r"\b([0-9]|10)\b", result["text"].strip())
            if match:
                raw_score = float(match.group(1))

        normalized = raw_score / 10.0
        self._cache[cache_key] = normalized
        return normalized
