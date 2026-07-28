"""
Memory benchmark scorer.

Implements the MemoryScore formula:

    MemoryScore = Recall × Relevance × Correctness - ContextWaste

Where:
    Recall       = |retrieved ∩ expected| / max(|expected|, 1)
                   Fraction of expected facts that were actually retrieved.

    Relevance    = |retrieved ∩ expected| / max(|retrieved|, 1)
                   Precision: fraction of retrieved facts that were expected.
                   A system that dumps the entire memory store has Relevance → 0.

    Correctness  = fraction of expected_entities found (substring) in the
                   combined text of retrieved expected facts.
                   A retrieved fact that doesn't actually contain the right
                   value (e.g. returned the wrong GPU model) scores 0 here.

    ContextWaste = irrelevant_tokens / max(total_tokens_retrieved, 1)
                   Token overhead from facts that should not have been
                   retrieved. Ranges 0–1.

    MemoryScore  ∈ [-1, 1]. Score < 0 means the context pollution outweighs
                   the retrieval benefit.

Bonus dimension (tracked but not in the formula):
    StaleContamination: fraction of retrieved facts that were explicitly
                        listed as "unexpected" (stale / superseded).
                        High stale contamination means contradiction handling
                        is broken.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Set


def _count_tokens_approx(text: str) -> int:
    """Rough BPE estimate: 1 token ≈ 4 chars."""
    return max(1, len(text) // 4)


@dataclass
class QueryScore:
    query_id: str
    scenario_id: str
    difficulty: int
    description: str

    # Raw counts
    n_expected: int = 0
    n_retrieved: int = 0
    n_hits: int = 0  # |retrieved ∩ expected|
    n_unexpected_hits: int = 0  # |retrieved ∩ unexpected| (stale facts)
    n_entities_matched: int = 0
    n_entities_total: int = 0

    # Token counts
    tokens_retrieved_total: int = 0
    tokens_retrieved_relevant: int = 0

    # Retrieval metadata
    retrieval_latency_ms: float = 0.0

    # Computed dimensions
    recall: float = 0.0
    relevance: float = 0.0
    correctness: float = 0.0
    context_waste: float = 0.0
    stale_contamination: float = 0.0
    memory_score: float = 0.0

    def compute(self) -> None:
        self.recall = self.n_hits / max(self.n_expected, 1)
        self.relevance = self.n_hits / max(self.n_retrieved, 1)
        self.correctness = self.n_entities_matched / max(self.n_entities_total, 1)
        self.context_waste = (
            self.tokens_retrieved_total - self.tokens_retrieved_relevant
        ) / max(self.tokens_retrieved_total, 1)
        self.stale_contamination = self.n_unexpected_hits / max(self.n_retrieved, 1)
        self.memory_score = max(
            -1.0,
            self.recall * self.relevance * self.correctness - self.context_waste,
        )


@dataclass
class ScenarioScore:
    scenario_id: str
    name: str
    query_scores: List[QueryScore] = field(default_factory=list)

    @property
    def avg_recall(self) -> float:
        vals = [q.recall for q in self.query_scores]
        return sum(vals) / len(vals) if vals else 0.0

    @property
    def avg_relevance(self) -> float:
        vals = [q.relevance for q in self.query_scores]
        return sum(vals) / len(vals) if vals else 0.0

    @property
    def avg_correctness(self) -> float:
        vals = [q.correctness for q in self.query_scores]
        return sum(vals) / len(vals) if vals else 0.0

    @property
    def avg_context_waste(self) -> float:
        vals = [q.context_waste for q in self.query_scores]
        return sum(vals) / len(vals) if vals else 0.0

    @property
    def avg_stale_contamination(self) -> float:
        vals = [q.stale_contamination for q in self.query_scores]
        return sum(vals) / len(vals) if vals else 0.0

    @property
    def avg_memory_score(self) -> float:
        vals = [q.memory_score for q in self.query_scores]
        return sum(vals) / len(vals) if vals else 0.0

    @property
    def avg_latency_ms(self) -> float:
        vals = [q.retrieval_latency_ms for q in self.query_scores]
        return sum(vals) / len(vals) if vals else 0.0


def score_query(
    *,
    query: Dict[str, Any],
    scenario: Dict[str, Any],
    retrieved: List[Dict[str, Any]],
    seed_result: Any,
    retrieval_latency_ms: float,
) -> QueryScore:
    """
    Score one retrieval result against expectations.

    Args:
        query: The query dict from scenarios.jsonl.
        scenario: The parent scenario dict.
        retrieved: List of retrieved fact dicts from the retrieval service.
                   Each has at minimum: 'id' (DB UUID), 'fact_text'.
        seed_result: SeedResult from seeder — maps fact_ids ↔ db_ids.
        retrieval_latency_ms: Wall-clock time for the retrieval call.
    """
    qs = QueryScore(
        query_id=query["query_id"],
        scenario_id=scenario["scenario_id"],
        difficulty=query.get("difficulty", 1),
        description=query.get("description", ""),
    )
    qs.retrieval_latency_ms = retrieval_latency_ms

    # Map query expectations to DB IDs
    expected_fact_ids: List[str] = query.get("expected_fact_ids", [])
    unexpected_fact_ids: List[str] = query.get("unexpected_fact_ids", [])
    expected_entities: List[str] = query.get("expected_entities", [])

    expected_db_ids: Set[str] = {
        db_id
        for fid in expected_fact_ids
        if (db_id := seed_result.lookup_db_id(fid)) is not None
    }
    unexpected_db_ids: Set[str] = {
        db_id
        for fid in unexpected_fact_ids
        if (db_id := seed_result.lookup_db_id(fid)) is not None
    }

    qs.n_expected = len(expected_db_ids)
    qs.n_entities_total = len(expected_entities)

    # Analyse retrieved results
    retrieved_db_ids: Set[str] = set()
    all_retrieved_text = ""
    relevant_retrieved_text = ""

    for item in retrieved:
        db_id = str(item.get("id", ""))
        fact_text = str(item.get("fact_text") or item.get("content") or "")
        retrieved_db_ids.add(db_id)
        all_retrieved_text += " " + fact_text
        if db_id in expected_db_ids:
            relevant_retrieved_text += " " + fact_text

    qs.n_retrieved = len(retrieved_db_ids)
    qs.n_hits = len(retrieved_db_ids & expected_db_ids)
    qs.n_unexpected_hits = len(retrieved_db_ids & unexpected_db_ids)
    qs.tokens_retrieved_total = _count_tokens_approx(all_retrieved_text)
    qs.tokens_retrieved_relevant = _count_tokens_approx(relevant_retrieved_text)

    # Entity correctness: check expected_entities in the combined text of
    # retrieved hits only (not expected facts that weren't retrieved).
    if expected_entities:
        combined_hit_text = all_retrieved_text.lower()
        qs.n_entities_matched = sum(
            1 for e in expected_entities if e.lower() in combined_hit_text
        )
    else:
        qs.n_entities_matched = (
            qs.n_hits
        )  # no specific entities — count as correct if recalled
        qs.n_entities_total = max(qs.n_hits, 1)

    qs.compute()
    return qs
