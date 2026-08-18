"""
Golden evaluation tests for retrieval ranking and cross-layer deduplication.

Each test seeds a known set of memory facts and verifies that:
  - The expected fact(s) appear in the assembled context
  - Lower-relevance facts are ranked lower or absent
  - Facts already in long-term memory are not duplicated in semantic retrieval

These tests use fully synthetic inputs so they never hit the database or
embedding model. The retrieval service is replaced with a fake that returns
pre-ranked results in the specified order.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from .helpers import (
    ContextBudget,
    _make_layer,
    _make_minimal_service,
    _patch_layer,
    _snapshot_patch,
    orch,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_result(fact_id: str, content: str, score: float = 0.9) -> dict:
    return {"id": fact_id, "content": content, "score": score, "source_type": "memory"}


def _make_long_term_layer(facts: list[dict]) -> object:
    """Build a ContextLayer that looks like what assemble_long_term_memory returns."""
    from api.services.context_assembly_service import ContextLayer

    fact_ids = [f["id"] for f in facts if f.get("id")]
    content = "## User Preferences & Stable Facts\n" + "\n".join(
        f"- [fact] {f['content']}" for f in facts
    )
    return ContextLayer(
        name="long_term_memory",
        content=content,
        tokens=len(content) // 4,
        source_count=len(facts),
        metadata={"type": "long_term", "fact_ids": fact_ids},
    )


def _make_semantic_layer(results: list[dict]) -> object:
    """Build a ContextLayer that looks like what assemble_semantic_retrieval returns."""
    from api.services.context_assembly_service import ContextLayer

    fact_ids = [r["id"] for r in results if r.get("id")]
    lines = ["## Relevant Context"]
    for i, r in enumerate(results):
        lines.append(f"### Result {i + 1} (Score: {r['score']:.2f})")
        lines.append(r["content"])
        lines.append("")
    content = "\n".join(lines)
    return ContextLayer(
        name="semantic_retrieval",
        content=content,
        tokens=len(content) // 4,
        source_count=len(results),
        metadata={"type": "semantic", "fact_ids": fact_ids},
    )


# ---------------------------------------------------------------------------
# Cross-layer deduplication
# ---------------------------------------------------------------------------


class TestCrossLayerDeduplication:
    """Facts already surfaced by long-term memory must not reappear in semantic retrieval."""

    @pytest.mark.asyncio
    async def test_semantic_excludes_long_term_fact_ids(self):
        """When assemble_semantic_retrieval receives exclude_fact_ids, it filters them out."""
        from api.services.context_assembly_service.semantic_layer import (
            assemble_semantic_retrieval,
        )

        fact_a = _make_result("fact-001", "User prefers dark mode", 0.95)
        fact_b = _make_result("fact-002", "User is learning Rust", 0.80)

        # Retrieval service returns both facts
        mock_rs = MagicMock()
        mock_rs.retrieve_context = AsyncMock(return_value=[fact_a, fact_b])

        mock_reranker = MagicMock()
        mock_reranker.rerank = lambda results, query: results

        mock_tracer = MagicMock()
        mock_tracer.start_trace = AsyncMock(return_value="trace-1")
        mock_tracer.end_trace = AsyncMock()
        mock_tracer.record_tier_breakdown = AsyncMock()

        budget = ContextBudget(total_tokens=2000, semantic_retrieval_tokens=500)

        with (
            patch(
                "api.services.context_assembly_service.semantic_layer._get_retrieval_service",
                return_value=mock_rs,
            ),
            patch(
                "api.services.context_assembly_service.semantic_layer.memory_reranker",
                mock_reranker,
                create=True,
            ),
            patch(
                "api.services.context_assembly_service.semantic_layer.retrieval_tracer",
                mock_tracer,
            ),
        ):
            layer = await assemble_semantic_retrieval(
                query="preferences",
                user_id="u1",
                conversation_id=None,
                remaining_tokens=500,
                correlation_id="corr-1",
                budget=budget,
                exclude_fact_ids={"fact-001"},  # already in long-term memory
            )

        assert layer is not None
        assert "fact-002" in layer.metadata.get("fact_ids", [])
        assert "fact-001" not in layer.metadata.get("fact_ids", [])
        assert "User is learning Rust" in layer.content
        assert "User prefers dark mode" not in layer.content

    @pytest.mark.asyncio
    async def test_semantic_not_called_when_no_remaining_after_dedup(self):
        """When all retrieved facts are already in long-term memory, semantic layer is None."""
        from api.services.context_assembly_service.semantic_layer import (
            assemble_semantic_retrieval,
        )

        fact_a = _make_result("fact-001", "User prefers dark mode", 0.95)

        mock_rs = MagicMock()
        mock_rs.retrieve_context = AsyncMock(return_value=[fact_a])

        mock_reranker = MagicMock()
        mock_reranker.rerank = lambda results, query: results

        mock_tracer = MagicMock()
        mock_tracer.start_trace = AsyncMock(return_value="trace-2")
        mock_tracer.end_trace = AsyncMock()
        mock_tracer.record_tier_breakdown = AsyncMock()

        budget = ContextBudget(total_tokens=2000, semantic_retrieval_tokens=500)

        with (
            patch(
                "api.services.context_assembly_service.semantic_layer._get_retrieval_service",
                return_value=mock_rs,
            ),
            patch(
                "api.services.context_assembly_service.semantic_layer.memory_reranker",
                mock_reranker,
                create=True,
            ),
            patch(
                "api.services.context_assembly_service.semantic_layer.retrieval_tracer",
                mock_tracer,
            ),
        ):
            layer = await assemble_semantic_retrieval(
                query="preferences",
                user_id="u1",
                conversation_id=None,
                remaining_tokens=500,
                correlation_id="corr-2",
                budget=budget,
                exclude_fact_ids={"fact-001"},
            )

        assert layer is None

    @pytest.mark.asyncio
    async def test_orchestrator_passes_long_term_ids_to_semantic(self, monkeypatch):
        """Orchestrator seeds seen_fact_ids from long-term layer into semantic retrieval."""
        budget = ContextBudget(
            total_tokens=2000,
            system_tokens=100,
            long_term_tokens=200,
            working_memory_tokens=200,
            semantic_retrieval_tokens=500,
            ephemeral_tokens=800,
        )

        svc = _make_minimal_service()
        monkeypatch.setattr(orch.bm, "derive_budget", lambda **_kw: budget)

        lt_layer = _make_long_term_layer([{"id": "fact-001", "content": "User prefers dark mode"}])

        captured_exclude_ids: set = set()

        async def fake_semantic(
            query,
            user_id,
            conversation_id,
            remaining_tokens,
            correlation_id,
            budget,
            exclude_fact_ids=None,
        ):
            if exclude_fact_ids:
                captured_exclude_ids.update(exclude_fact_ids)
            return _make_semantic_layer([_make_result("fact-002", "User is learning Rust", 0.80)])

        with (
            _patch_layer("assemble_system_layer", return_value=_make_layer("system", 30)),
            _patch_layer("assemble_long_term_memory", return_value=lt_layer),
            patch.object(orch, "assemble_semantic_retrieval", fake_semantic),
            _snapshot_patch("snap-dedup"),
        ):
            svc._retrieval_service = MagicMock()
            svc._retrieval_service.get_degraded_status = MagicMock(
                return_value={"degraded_mode": False}
            )
            await svc.assemble_context(query="q", user_id="u1")

        assert "fact-001" in captured_exclude_ids, (
            "Orchestrator should pass long-term fact IDs to semantic retrieval"
        )

    @pytest.mark.asyncio
    async def test_fact_ids_tracked_in_layer_metadata(self, monkeypatch):
        """Semantic layer metadata includes fact_ids so downstream layers can deduplicate."""
        budget = ContextBudget(
            total_tokens=2000,
            system_tokens=100,
            long_term_tokens=200,
            working_memory_tokens=200,
            semantic_retrieval_tokens=500,
            ephemeral_tokens=800,
        )
        svc = _make_minimal_service()
        monkeypatch.setattr(orch.bm, "derive_budget", lambda **_kw: budget)

        sem_layer = _make_semantic_layer(
            [
                _make_result("fact-010", "Goblin assistant uses React Query", 0.92),
                _make_result("fact-011", "Prefers TypeScript strict mode", 0.85),
            ]
        )

        with (
            _patch_layer("assemble_system_layer", return_value=_make_layer("system", 30)),
            _patch_layer("assemble_semantic_retrieval", return_value=sem_layer),
            _snapshot_patch("snap-meta"),
        ):
            svc._retrieval_service = MagicMock()
            svc._retrieval_service.get_degraded_status = MagicMock(
                return_value={"degraded_mode": False}
            )
            result = await svc.assemble_context(query="q", user_id="u1")

        semantic_layers = [
            layer for layer in result["layers"] if layer.name == "semantic_retrieval"
        ]
        assert len(semantic_layers) == 1
        fact_ids = semantic_layers[0].metadata.get("fact_ids", [])
        assert "fact-010" in fact_ids
        assert "fact-011" in fact_ids


# ---------------------------------------------------------------------------
# Retrieval ranking quality
# ---------------------------------------------------------------------------


class TestRetrievalRankingQuality:
    """Higher-relevance facts should be ranked above lower-relevance ones."""

    def test_reranker_preserves_descending_score_order(self):
        """Default reranker keeps highest-scoring results first."""
        from api.services.memory_reranker import MemoryReranker

        reranker = MemoryReranker()
        results = [
            _make_result("f1", "Fact about Python", 0.6),
            _make_result("f2", "Fact about Rust with high relevance", 0.95),
            _make_result("f3", "Fact about general preferences", 0.75),
        ]
        ranked = reranker.rerank(results, query="Rust programming")
        scores = [r["score"] for r in ranked]
        assert scores == sorted(scores, reverse=True), (
            "Reranker must return results sorted descending by score"
        )

    def test_reranker_top_result_is_highest_score(self):
        """The top result from the reranker has the highest score."""
        from api.services.memory_reranker import MemoryReranker

        reranker = MemoryReranker()
        results = [
            _make_result("f1", "Tangential fact", 0.3),
            _make_result("f2", "Highly relevant fact", 0.97),
            _make_result("f3", "Moderately relevant fact", 0.55),
        ]
        ranked = reranker.rerank(results, query="very specific query")
        assert ranked[0]["id"] == "f2", "Top result should be the highest-scoring fact"

    def test_reranker_empty_input_returns_empty(self):
        from api.services.memory_reranker import MemoryReranker

        reranker = MemoryReranker()
        assert reranker.rerank([], query="any query") == []

    def test_reranker_single_result_returned_unchanged(self):
        from api.services.memory_reranker import MemoryReranker

        reranker = MemoryReranker()
        results = [_make_result("f1", "Only fact", 0.7)]
        ranked = reranker.rerank(results, query="query")
        assert len(ranked) == 1
        assert ranked[0]["id"] == "f1"

    @pytest.mark.asyncio
    async def test_semantic_layer_exposes_top_result_first_in_content(self):
        """The formatted content of the semantic layer lists the highest-scored result first."""
        from api.services.context_assembly_service.semantic_layer import (
            assemble_semantic_retrieval,
        )

        fact_high = _make_result("f-high", "High relevance: Rust memory safety", 0.95)
        fact_low = _make_result("f-low", "Low relevance: random tangent", 0.40)

        mock_rs = MagicMock()
        mock_rs.retrieve_context = AsyncMock(return_value=[fact_low, fact_high])

        # Reranker sorts descending by score
        from api.services.memory_reranker import MemoryReranker

        mock_tracer = MagicMock()
        mock_tracer.start_trace = AsyncMock(return_value="trace-rank")
        mock_tracer.end_trace = AsyncMock()
        mock_tracer.record_tier_breakdown = AsyncMock()

        budget = ContextBudget(total_tokens=3000, semantic_retrieval_tokens=1000)

        real_reranker = MemoryReranker()
        with (
            patch(
                "api.services.context_assembly_service.semantic_layer._get_retrieval_service",
                return_value=mock_rs,
            ),
            patch(
                "api.services.memory_reranker.memory_reranker",
                real_reranker,
            ),
            patch(
                "api.services.context_assembly_service.semantic_layer.retrieval_tracer",
                mock_tracer,
            ),
        ):
            layer = await assemble_semantic_retrieval(
                query="Rust",
                user_id="u1",
                conversation_id=None,
                remaining_tokens=1000,
                correlation_id="corr-rank",
                budget=budget,
            )

        assert layer is not None
        high_pos = layer.content.find("Rust memory safety")
        low_pos = layer.content.find("random tangent")
        assert high_pos < low_pos, (
            "Higher-scored result should appear earlier in semantic layer content"
        )


# ---------------------------------------------------------------------------
# Token budget correctness
# ---------------------------------------------------------------------------


class TestRetrievalTokenBudget:
    """Retrieved context must never exceed its token allocation."""

    @pytest.mark.asyncio
    async def test_semantic_layer_respects_token_budget(self):
        """Semantic layer token count must not exceed remaining_tokens."""
        from api.services.context_assembly_service.semantic_layer import (
            assemble_semantic_retrieval,
        )

        large_fact = _make_result("f-big", "x " * 5000, 0.9)
        mock_rs = MagicMock()
        mock_rs.retrieve_context = AsyncMock(return_value=[large_fact])

        mock_reranker = MagicMock()
        mock_reranker.rerank = lambda results, query: results

        mock_tracer = MagicMock()
        mock_tracer.start_trace = AsyncMock(return_value="trace-budget")
        mock_tracer.end_trace = AsyncMock()
        mock_tracer.record_tier_breakdown = AsyncMock()

        budget = ContextBudget(total_tokens=3000, semantic_retrieval_tokens=200)
        remaining_tokens = 200

        with (
            patch(
                "api.services.context_assembly_service.semantic_layer._get_retrieval_service",
                return_value=mock_rs,
            ),
            patch(
                "api.services.context_assembly_service.semantic_layer.memory_reranker",
                mock_reranker,
                create=True,
            ),
            patch(
                "api.services.context_assembly_service.semantic_layer.retrieval_tracer",
                mock_tracer,
            ),
        ):
            layer = await assemble_semantic_retrieval(
                query="big query",
                user_id="u1",
                conversation_id=None,
                remaining_tokens=remaining_tokens,
                correlation_id="corr-bgt",
                budget=budget,
            )

        assert layer is not None
        assert layer.tokens <= remaining_tokens, (
            f"Semantic layer used {layer.tokens} tokens but limit was {remaining_tokens}"
        )
        assert layer.metadata.get("hard_stop_applied") is True
