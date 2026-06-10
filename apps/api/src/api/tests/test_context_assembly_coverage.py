"""
Comprehensive coverage tests for ContextAssemblyService.

Targets six areas of the retrieval pipeline:
  1. Token Budgeting
  2. Chunk Truncation
  3. Context Ordering
  4. Source Attribution
  5. Overflow Handling
  6. Retrieval Failures

Every test answers three questions:
  - Did the right context get selected?
  - Did it fit inside the token budget?
  - Did we lose important information?
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.services.context_assembly_service import (
    ContextAssemblyService,
    ContextBudget,
    ContextLayer,
)
from api.services.context_assembly_service import orchestrator as orch

# ======================================================================
# Helpers
# ======================================================================


def _make_layer(
    name: str,
    tokens: int,
    source_count: int = 0,
    metadata: dict | None = None,
) -> ContextLayer:
    return ContextLayer(
        name=name,
        content=f"content for {name} " * (tokens // 3 + 1),
        tokens=tokens,
        source_count=source_count,
        metadata=metadata or {},
    )


def _make_minimal_service() -> ContextAssemblyService:
    s = ContextAssemblyService.__new__(ContextAssemblyService)
    s._retrieval_service = None
    s._embedding_service = None
    s.response_reserve_tokens = 1024
    s.default_budget = ContextBudget(
        total_tokens=500,
        system_tokens=50,
        long_term_tokens=50,
        working_memory_tokens=100,
        semantic_retrieval_tokens=100,
        ephemeral_tokens=200,
    )
    s.model_context_windows = {}
    return s


def _patch_layer(target_attr: str, return_value=None, side_effect=None):
    """Patch a single layer assembler with an AsyncMock."""
    if side_effect is not None:
        return patch.object(orch, target_attr, AsyncMock(side_effect=side_effect))
    return patch.object(orch, target_attr, AsyncMock(return_value=return_value))


def _snapshot_patch(return_value="snap-default", side_effect=None):
    """Patch context_snapshotter.create_snapshot."""
    if side_effect is not None:
        return patch.object(
            orch.context_snapshotter,
            "create_snapshot",
            AsyncMock(side_effect=side_effect),
        )
    return patch.object(
        orch.context_snapshotter,
        "create_snapshot",
        AsyncMock(return_value=return_value),
    )


# ======================================================================
# 1. TOKEN BUDGETING
# ======================================================================


class TestTokenBudgeting:
    """Did the context fit inside the token budget?"""

    @pytest.mark.asyncio
    async def test_remaining_tokens_decremented_per_layer(self, monkeypatch):
        """Each layer's token cost is subtracted from remaining_tokens."""
        budget = ContextBudget(
            total_tokens=500,
            system_tokens=100,
            long_term_tokens=100,
            working_memory_tokens=100,
            semantic_retrieval_tokens=100,
            ephemeral_tokens=100,
        )
        svc = _make_minimal_service()
        monkeypatch.setattr(orch.bm, "derive_budget", lambda **_kw: budget)

        with (
            _patch_layer("assemble_system_layer", return_value=_make_layer("system", 80)),
            _patch_layer(
                "assemble_long_term_memory",
                return_value=_make_layer("long_term_memory", 60),
            ),
            _patch_layer(
                "assemble_working_memory",
                return_value=_make_layer("working_memory", 40),
            ),
            _patch_layer(
                "assemble_semantic_retrieval",
                return_value=_make_layer("semantic_retrieval", 70),
            ),
            _patch_layer(
                "assemble_ephemeral_memory",
                return_value=_make_layer("ephemeral_memory", 50),
            ),
            _snapshot_patch("snap-1"),
        ):
            result = await svc.assemble_context(
                query="q",
                user_id="u1",
                conversation_id="c1",
                conversation_history=[{"role": "user", "content": "hi"}],
            )

        # expected: 500 - (80+60+40+70+50) = 200
        assert result["remaining_tokens"] == 200
        assert result["total_tokens_used"] == 300

    @pytest.mark.asyncio
    async def test_model_param_propagates_to_derive_budget(self, monkeypatch):
        """assemble_context(model=...) is forwarded to derive_budget."""
        svc = _make_minimal_service()
        captured = {}

        def spy_budget(**kwargs):
            captured["model"] = kwargs.get("model")
            captured["max_context_tokens"] = kwargs.get("max_context_tokens")
            return svc.default_budget

        monkeypatch.setattr(orch.bm, "derive_budget", spy_budget)

        with (
            _patch_layer("assemble_system_layer", return_value=_make_layer("system", 10)),
            _snapshot_patch("snap-m"),
        ):
            await svc.assemble_context(query="q", user_id="u1", model="gpt-4o-mini")

        assert captured.get("model") == "gpt-4o-mini"
        assert captured.get("max_context_tokens") is None

    @pytest.mark.asyncio
    async def test_max_context_tokens_overrides_model_lookup(self, monkeypatch):
        """max_context_tokens=4000 is passed through to derive_budget."""
        svc = _make_minimal_service()
        captured = {}

        def spy_budget(**kwargs):
            captured["max_context_tokens"] = kwargs.get("max_context_tokens")
            return svc.default_budget

        monkeypatch.setattr(orch.bm, "derive_budget", spy_budget)

        with (
            _patch_layer("assemble_system_layer", return_value=_make_layer("system", 10)),
            _snapshot_patch("snap-mct"),
        ):
            await svc.assemble_context(query="q", user_id="u1", max_context_tokens=4000)

        assert captured.get("max_context_tokens") == 4000

    @pytest.mark.asyncio
    async def test_tiny_budget_only_system_fits(self, monkeypatch):
        """With tight budget only system layer assembles."""
        # Budget = 100. System consumes all 100, remaining=0 → nothing else runs.
        budget = ContextBudget(
            total_tokens=100,
            system_tokens=100,
            long_term_tokens=50,
            working_memory_tokens=50,
            semantic_retrieval_tokens=50,
            ephemeral_tokens=0,
        )
        svc = _make_minimal_service()
        monkeypatch.setattr(orch.bm, "derive_budget", lambda **_kw: budget)

        long_term_mock = AsyncMock()
        working_mock = AsyncMock()
        semantic_mock = AsyncMock()
        ephemeral_mock = AsyncMock()

        async def system_fn(*_a, **_kw):
            return _make_layer("system", 100)

        with (
            _patch_layer("assemble_system_layer", side_effect=system_fn),
            patch.object(orch, "assemble_long_term_memory", long_term_mock),
            patch.object(orch, "assemble_working_memory", working_mock),
            patch.object(orch, "assemble_semantic_retrieval", semantic_mock),
            patch.object(orch, "assemble_ephemeral_memory", ephemeral_mock),
            _snapshot_patch("snap-tiny"),
        ):
            result = await svc.assemble_context(query="q", user_id="u1")

        # Only system — remaining = 100-100 = 0
        assert result["remaining_tokens"] == 0
        assert len(result["layers"]) == 1
        assert result["layers"][0].name == "system"
        long_term_mock.assert_not_awaited()
        working_mock.assert_not_awaited()
        semantic_mock.assert_not_awaited()
        ephemeral_mock.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_system_exhausts_budget_nothing_else_assembles(self, monkeypatch):
        """System consumes entire budget; remaining=0 skips all subsequent layers."""
        budget = ContextBudget(
            total_tokens=80,
            system_tokens=80,
            long_term_tokens=50,
            working_memory_tokens=50,
            semantic_retrieval_tokens=50,
            ephemeral_tokens=0,
        )
        svc = _make_minimal_service()
        monkeypatch.setattr(orch.bm, "derive_budget", lambda **_kw: budget)

        async def system_fn(*_a, **_kw):
            return _make_layer("system", 80)

        long_term_mock = AsyncMock()
        working_mock = AsyncMock()
        semantic_mock = AsyncMock()
        ephemeral_mock = AsyncMock()

        with (
            _patch_layer("assemble_system_layer", side_effect=system_fn),
            patch.object(orch, "assemble_long_term_memory", long_term_mock),
            patch.object(orch, "assemble_working_memory", working_mock),
            patch.object(orch, "assemble_semantic_retrieval", semantic_mock),
            patch.object(orch, "assemble_ephemeral_memory", ephemeral_mock),
            _snapshot_patch("snap-exh"),
        ):
            result = await svc.assemble_context(
                query="q",
                user_id="u1",
                conversation_id="c1",
            )

        assert result["remaining_tokens"] == 0
        assert len(result["layers"]) == 1
        assert result["layers"][0].name == "system"
        long_term_mock.assert_not_awaited()
        working_mock.assert_not_awaited()
        semantic_mock.assert_not_awaited()
        ephemeral_mock.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_conversation_id_without_history_skips_ephemeral(self, monkeypatch):
        """conversation_id set, history=None: working memory included, ephemeral skipped."""
        budget = ContextBudget(
            total_tokens=400,
            system_tokens=50,
            long_term_tokens=50,
            working_memory_tokens=100,
            semantic_retrieval_tokens=100,
            ephemeral_tokens=100,
        )
        svc = _make_minimal_service()
        monkeypatch.setattr(orch.bm, "derive_budget", lambda **_kw: budget)

        ephemeral_calls = 0

        async def eph(*_a, **_kw):
            nonlocal ephemeral_calls
            ephemeral_calls += 1

        with (
            _patch_layer("assemble_system_layer", return_value=_make_layer("system", 30)),
            _patch_layer(
                "assemble_long_term_memory",
                return_value=_make_layer("long_term_memory", 20),
            ),
            _patch_layer(
                "assemble_working_memory",
                return_value=_make_layer("working_memory", 40),
            ),
            _patch_layer(
                "assemble_semantic_retrieval",
                return_value=_make_layer("semantic_retrieval", 50),
            ),
            _patch_layer("assemble_ephemeral_memory", side_effect=eph),
            _snapshot_patch("snap-cih"),
        ):
            svc._retrieval_service = MagicMock()
            svc._retrieval_service.get_degraded_status = MagicMock(
                return_value={"degraded_mode": False},
            )

            result = await svc.assemble_context(
                query="q",
                user_id="u1",
                conversation_id="c1",
                conversation_history=None,
            )

        assert ephemeral_calls == 0
        names = [lyr.name for lyr in result["layers"]]
        assert "working_memory" in names
        assert "ephemeral_memory" not in names


# ======================================================================
# 2. CHUNK TRUNCATION
# ======================================================================


class TestChunkTruncation:
    """Did we lose important information?"""

    @pytest.mark.asyncio
    async def test_semantic_hard_stop_sets_truncation_warning(self, monkeypatch):
        """Semantic layer with hard_stop_applied=True → truncation_warnings includes it."""
        budget = ContextBudget(
            total_tokens=500,
            system_tokens=300,
            long_term_tokens=50,
            working_memory_tokens=50,
            semantic_retrieval_tokens=50,
            ephemeral_tokens=50,
        )
        svc = _make_minimal_service()
        monkeypatch.setattr(orch.bm, "derive_budget", lambda **_kw: budget)

        with (
            _patch_layer("assemble_system_layer", return_value=_make_layer("system", 30)),
            _patch_layer(
                "assemble_semantic_retrieval",
                return_value=_make_layer(
                    "semantic_retrieval",
                    50,
                    metadata={"hard_stop_applied": True},
                ),
            ),
            _patch_layer(
                "assemble_ephemeral_memory",
                return_value=_make_layer(
                    "ephemeral_memory",
                    40,
                    metadata={"truncated": False},
                ),
            ),
            _snapshot_patch("snap-hs"),
        ):
            svc._retrieval_service = MagicMock()
            svc._retrieval_service.get_degraded_status = MagicMock(
                return_value={"degraded_mode": False},
            )

            result = await svc.assemble_context(
                query="q",
                user_id="u1",
                conversation_id="c1",
                conversation_history=[{"role": "u", "content": "hi"}],
            )

        assert "semantic_retrieval_truncated" in result["truncation_warnings"]

    @pytest.mark.asyncio
    async def test_ephemeral_truncated_sets_truncation_warning(self, monkeypatch):
        """Ephemeral layer with truncated=True → warning in result."""
        budget = ContextBudget(
            total_tokens=500,
            system_tokens=300,
            long_term_tokens=50,
            working_memory_tokens=50,
            semantic_retrieval_tokens=50,
            ephemeral_tokens=50,
        )
        svc = _make_minimal_service()
        monkeypatch.setattr(orch.bm, "derive_budget", lambda **_kw: budget)

        with (
            _patch_layer("assemble_system_layer", return_value=_make_layer("system", 30)),
            _patch_layer(
                "assemble_ephemeral_memory",
                return_value=_make_layer(
                    "ephemeral_memory",
                    40,
                    metadata={"truncated": True, "summary_fallback_applied": False},
                ),
            ),
            _snapshot_patch("snap-eph"),
        ):
            svc._retrieval_service = MagicMock()
            svc._retrieval_service.get_degraded_status = MagicMock(
                return_value={"degraded_mode": False},
            )

            result = await svc.assemble_context(
                query="q",
                user_id="u1",
                conversation_id="c1",
                conversation_history=[{"role": "u", "content": "hi"}],
            )

        assert "ephemeral_memory_truncated" in result["truncation_warnings"]

    @pytest.mark.asyncio
    async def test_summary_fallback_sets_flag_in_result(self, monkeypatch):
        """summary_fallback_applied=True propagates to result correctly."""
        budget = ContextBudget(
            total_tokens=500,
            system_tokens=300,
            long_term_tokens=50,
            working_memory_tokens=50,
            semantic_retrieval_tokens=50,
            ephemeral_tokens=50,
        )
        svc = _make_minimal_service()
        monkeypatch.setattr(orch.bm, "derive_budget", lambda **_kw: budget)

        with (
            _patch_layer("assemble_system_layer", return_value=_make_layer("system", 30)),
            _patch_layer(
                "assemble_ephemeral_memory",
                return_value=_make_layer(
                    "ephemeral_memory",
                    40,
                    metadata={"truncated": True, "summary_fallback_applied": True},
                ),
            ),
            _snapshot_patch("snap-sf"),
        ):
            svc._retrieval_service = MagicMock()
            svc._retrieval_service.get_degraded_status = MagicMock(
                return_value={"degraded_mode": False},
            )

            result = await svc.assemble_context(
                query="q",
                user_id="u1",
                conversation_id="c1",
                conversation_history=[{"role": "u", "content": "hi"}],
            )

        assert result["summary_fallback_applied"] is True

    def test_build_final_context_secondary_trim(self, monkeypatch):
        """_build_final_context trims when joined content exceeds the used budget."""
        budget = ContextBudget(total_tokens=200)
        layers = [
            _make_layer("system", 80),
            _make_layer("long_term_memory", 60),
        ]
        monkeypatch.setattr(orch, "_count_tokens", lambda _text: 200)
        monkeypatch.setattr(
            orch,
            "_trim_to_tokens_util",
            lambda text, limit: "trimmed-final",
        )

        final = ContextAssemblyService._build_final_context(
            layers,
            remaining_tokens=60,
            budget=budget,
        )

        assert final == "trimmed-final"


# ======================================================================
# 3. CONTEXT ORDERING
# ======================================================================


class TestContextOrdering:
    """Did the right context get selected?"""

    @pytest.mark.asyncio
    async def test_system_layer_always_first(self, monkeypatch):
        """System is always the first layer in the assembled list."""
        budget = ContextBudget(
            total_tokens=500,
            system_tokens=100,
            long_term_tokens=50,
            working_memory_tokens=50,
            semantic_retrieval_tokens=50,
            ephemeral_tokens=50,
        )
        svc = _make_minimal_service()
        monkeypatch.setattr(orch.bm, "derive_budget", lambda **_kw: budget)

        with (
            _patch_layer("assemble_system_layer", return_value=_make_layer("system", 30)),
            _snapshot_patch("snap-first"),
        ):
            result = await svc.assemble_context(query="q", user_id="u1")

        assert result["layers"][0].name == "system"

    @pytest.mark.asyncio
    async def test_full_stack_order(self, monkeypatch):
        """All five layers present in correct order."""
        budget = ContextBudget(
            total_tokens=1000,
            system_tokens=200,
            long_term_tokens=200,
            working_memory_tokens=200,
            semantic_retrieval_tokens=200,
            ephemeral_tokens=200,
        )
        svc = _make_minimal_service()
        monkeypatch.setattr(orch.bm, "derive_budget", lambda **_kw: budget)

        with (
            _patch_layer("assemble_system_layer", return_value=_make_layer("system", 30)),
            _patch_layer(
                "assemble_long_term_memory",
                return_value=_make_layer("long_term_memory", 20),
            ),
            _patch_layer(
                "assemble_working_memory",
                return_value=_make_layer("working_memory", 40),
            ),
            _patch_layer(
                "assemble_semantic_retrieval",
                return_value=_make_layer("semantic_retrieval", 50),
            ),
            _patch_layer(
                "assemble_ephemeral_memory",
                return_value=_make_layer("ephemeral_memory", 30),
            ),
            _snapshot_patch("snap-full"),
        ):
            svc._retrieval_service = MagicMock()
            svc._retrieval_service.get_degraded_status = MagicMock(
                return_value={"degraded_mode": False},
            )

            result = await svc.assemble_context(
                query="q",
                user_id="u1",
                conversation_id="c1",
                conversation_history=[{"role": "u", "content": "hi"}],
            )

        names = [lyr.name for lyr in result["layers"]]
        assert names == [
            "system",
            "long_term_memory",
            "working_memory",
            "semantic_retrieval",
            "ephemeral_memory",
        ]

    @pytest.mark.asyncio
    async def test_no_conversation_id_skips_working_and_ephemeral(self, monkeypatch):
        """Without conversation_id, working_memory and ephemeral are skipped."""
        budget = ContextBudget(
            total_tokens=500,
            system_tokens=100,
            long_term_tokens=100,
            working_memory_tokens=100,
            semantic_retrieval_tokens=100,
            ephemeral_tokens=100,
        )
        svc = _make_minimal_service()
        monkeypatch.setattr(orch.bm, "derive_budget", lambda **_kw: budget)

        with (
            _patch_layer("assemble_system_layer", return_value=_make_layer("system", 30)),
            _patch_layer(
                "assemble_long_term_memory",
                return_value=_make_layer("long_term_memory", 20),
            ),
            _patch_layer(
                "assemble_semantic_retrieval",
                return_value=_make_layer("semantic_retrieval", 50),
            ),
            _snapshot_patch("snap-noid"),
        ):
            svc._retrieval_service = MagicMock()
            svc._retrieval_service.get_degraded_status = MagicMock(
                return_value={"degraded_mode": False},
            )

            result = await svc.assemble_context(
                query="q",
                user_id="u1",
                conversation_id=None,
                conversation_history=None,
            )

        names = [lyr.name for lyr in result["layers"]]
        assert "working_memory" not in names
        assert "ephemeral_memory" not in names
        assert names == ["system", "long_term_memory", "semantic_retrieval"]

    @pytest.mark.asyncio
    async def test_conversation_id_no_history_working_present_ephemeral_skipped(
        self,
        monkeypatch,
    ):
        """conversation_id present + history=None → working included, ephemeral skipped."""
        budget = ContextBudget(
            total_tokens=500,
            system_tokens=100,
            long_term_tokens=50,
            working_memory_tokens=100,
            semantic_retrieval_tokens=100,
            ephemeral_tokens=150,
        )
        svc = _make_minimal_service()
        monkeypatch.setattr(orch.bm, "derive_budget", lambda **_kw: budget)

        with (
            _patch_layer("assemble_system_layer", return_value=_make_layer("system", 30)),
            _patch_layer(
                "assemble_long_term_memory",
                return_value=_make_layer("long_term_memory", 20),
            ),
            _patch_layer(
                "assemble_working_memory",
                return_value=_make_layer("working_memory", 40),
            ),
            _patch_layer(
                "assemble_semantic_retrieval",
                return_value=_make_layer("semantic_retrieval", 50),
            ),
            _snapshot_patch("snap-cinh"),
        ):
            svc._retrieval_service = MagicMock()
            svc._retrieval_service.get_degraded_status = MagicMock(
                return_value={"degraded_mode": False},
            )

            result = await svc.assemble_context(
                query="q",
                user_id="u1",
                conversation_id="c1",
                conversation_history=None,
            )

        names = [lyr.name for lyr in result["layers"]]
        assert "working_memory" in names
        assert "ephemeral_memory" not in names

    @pytest.mark.asyncio
    async def test_history_no_conversation_id_working_skipped_ephemeral_present(
        self,
        monkeypatch,
    ):
        """history present + conversation_id=None → working skipped, ephemeral included."""
        budget = ContextBudget(
            total_tokens=500,
            system_tokens=100,
            long_term_tokens=50,
            working_memory_tokens=100,
            semantic_retrieval_tokens=100,
            ephemeral_tokens=150,
        )
        svc = _make_minimal_service()
        monkeypatch.setattr(orch.bm, "derive_budget", lambda **_kw: budget)

        with (
            _patch_layer("assemble_system_layer", return_value=_make_layer("system", 30)),
            _patch_layer(
                "assemble_long_term_memory",
                return_value=_make_layer("long_term_memory", 20),
            ),
            _patch_layer(
                "assemble_semantic_retrieval",
                return_value=_make_layer("semantic_retrieval", 50),
            ),
            _patch_layer(
                "assemble_ephemeral_memory",
                return_value=_make_layer("ephemeral_memory", 30),
            ),
            _snapshot_patch("snap-ncidh"),
        ):
            svc._retrieval_service = MagicMock()
            svc._retrieval_service.get_degraded_status = MagicMock(
                return_value={"degraded_mode": False},
            )

            result = await svc.assemble_context(
                query="q",
                user_id="u1",
                conversation_id=None,
                conversation_history=[{"role": "u", "content": "hi"}],
            )

        names = [lyr.name for lyr in result["layers"]]
        assert "working_memory" not in names
        assert "ephemeral_memory" in names


# ======================================================================
# 4. SOURCE ATTRIBUTION
# ======================================================================


class TestSourceAttribution:
    """Did the right context get selected?  (source counts and token tracking)"""

    @pytest.mark.asyncio
    async def test_semantic_source_count_propagates(self, monkeypatch):
        """source_count on semantic layer is accessible through the result."""
        budget = ContextBudget(
            total_tokens=500,
            system_tokens=100,
            long_term_tokens=50,
            working_memory_tokens=50,
            semantic_retrieval_tokens=200,
            ephemeral_tokens=100,
        )
        svc = _make_minimal_service()
        monkeypatch.setattr(orch.bm, "derive_budget", lambda **_kw: budget)

        with (
            _patch_layer("assemble_system_layer", return_value=_make_layer("system", 30)),
            _patch_layer(
                "assemble_semantic_retrieval",
                return_value=_make_layer(
                    "semantic_retrieval",
                    50,
                    source_count=7,
                ),
            ),
            _snapshot_patch("snap-sc"),
        ):
            svc._retrieval_service = MagicMock()
            svc._retrieval_service.get_degraded_status = MagicMock(
                return_value={"degraded_mode": False},
            )

            result = await svc.assemble_context(query="q", user_id="u1")

        sem_layer = next(lyr for lyr in result["layers"] if lyr.name == "semantic_retrieval")
        assert sem_layer.source_count == 7

    @pytest.mark.asyncio
    async def test_ephemeral_source_count_propagates(self, monkeypatch):
        """source_count on ephemeral layer is accessible through the result."""
        budget = ContextBudget(
            total_tokens=500,
            system_tokens=100,
            long_term_tokens=50,
            working_memory_tokens=50,
            semantic_retrieval_tokens=50,
            ephemeral_tokens=250,
        )
        svc = _make_minimal_service()
        monkeypatch.setattr(orch.bm, "derive_budget", lambda **_kw: budget)

        with (
            _patch_layer("assemble_system_layer", return_value=_make_layer("system", 30)),
            _patch_layer(
                "assemble_semantic_retrieval",
                return_value=_make_layer(
                    "semantic_retrieval",
                    50,
                    metadata={"hard_stop_applied": False},
                ),
            ),
            _patch_layer(
                "assemble_ephemeral_memory",
                return_value=_make_layer(
                    "ephemeral_memory",
                    40,
                    source_count=5,
                ),
            ),
            _snapshot_patch("snap-ephc"),
        ):
            svc._retrieval_service = MagicMock()
            svc._retrieval_service.get_degraded_status = MagicMock(
                return_value={"degraded_mode": False},
            )

            result = await svc.assemble_context(
                query="q",
                user_id="u1",
                conversation_id="c1",
                conversation_history=[{"role": "u", "content": "hi"}] * 5,
            )

        eph_layer = next(lyr for lyr in result["layers"] if lyr.name == "ephemeral_memory")
        assert eph_layer.source_count == 5

    @pytest.mark.asyncio
    async def test_assembly_log_token_usage_per_layer(self, monkeypatch):
        """assembly_log.token_usage has correct keys and values."""
        budget = ContextBudget(
            total_tokens=1000,
            system_tokens=200,
            long_term_tokens=200,
            working_memory_tokens=200,
            semantic_retrieval_tokens=200,
            ephemeral_tokens=200,
        )
        svc = _make_minimal_service()
        monkeypatch.setattr(orch.bm, "derive_budget", lambda **_kw: budget)

        with (
            _patch_layer("assemble_system_layer", return_value=_make_layer("system", 30)),
            _patch_layer(
                "assemble_long_term_memory",
                return_value=_make_layer("long_term_memory", 20),
            ),
            _patch_layer(
                "assemble_working_memory",
                return_value=_make_layer("working_memory", 40),
            ),
            _patch_layer(
                "assemble_semantic_retrieval",
                return_value=_make_layer("semantic_retrieval", 50),
            ),
            _patch_layer(
                "assemble_ephemeral_memory",
                return_value=_make_layer("ephemeral_memory", 30),
            ),
            _snapshot_patch("snap-log"),
        ):
            svc._retrieval_service = MagicMock()
            svc._retrieval_service.get_degraded_status = MagicMock(
                return_value={"degraded_mode": False},
            )

            result = await svc.assemble_context(
                query="q",
                user_id="u1",
                conversation_id="c1",
                conversation_history=[{"role": "u", "content": "hi"}],
            )

        usage = result["assembly_log"]["token_usage"]
        assert usage["system"] == 30
        assert usage["long_term"] == 20
        assert usage["working_memory"] == 40
        assert usage["semantic_retrieval"] == 50
        assert usage["ephemeral"] == 30
        assert sum(usage.values()) == 170
        assert result["remaining_tokens"] == 830


# ======================================================================
# 5. OVERFLOW HANDLING
# ======================================================================


class TestOverflowHandling:
    """Did it fit inside the token budget?  (overflow edge cases)"""

    @pytest.mark.asyncio
    async def test_remaining_tokens_never_negative(self, monkeypatch):
        """Even with oversized layers, remaining_tokens stays >= 0."""
        budget = ContextBudget(
            total_tokens=100,
            system_tokens=50,
            long_term_tokens=50,
            working_memory_tokens=50,
            semantic_retrieval_tokens=50,
            ephemeral_tokens=50,
        )
        svc = _make_minimal_service()
        monkeypatch.setattr(orch.bm, "derive_budget", lambda **_kw: budget)

        with (
            _patch_layer("assemble_system_layer", return_value=_make_layer("system", 60)),
            _snapshot_patch("snap-neg"),
        ):
            result = await svc.assemble_context(query="q", user_id="u1")

        assert result["remaining_tokens"] >= 0
        assert result["remaining_tokens"] == 40

    @pytest.mark.asyncio
    async def test_all_layers_return_data_graceful_trim(self, monkeypatch):
        """All 5 layers return data — final context trimmed if it exceeds budget."""
        budget = ContextBudget(
            total_tokens=300,
            system_tokens=60,
            long_term_tokens=60,
            working_memory_tokens=60,
            semantic_retrieval_tokens=60,
            ephemeral_tokens=60,
        )
        svc = _make_minimal_service()
        monkeypatch.setattr(orch.bm, "derive_budget", lambda **_kw: budget)

        with (
            _patch_layer("assemble_system_layer", return_value=_make_layer("system", 60)),
            _patch_layer(
                "assemble_long_term_memory",
                return_value=_make_layer("long_term_memory", 60),
            ),
            _patch_layer(
                "assemble_working_memory",
                return_value=_make_layer("working_memory", 60),
            ),
            _patch_layer(
                "assemble_semantic_retrieval",
                return_value=_make_layer("semantic_retrieval", 60),
            ),
            _patch_layer(
                "assemble_ephemeral_memory",
                return_value=_make_layer("ephemeral_memory", 60),
            ),
            _snapshot_patch("snap-over"),
        ):
            svc._retrieval_service = MagicMock()
            svc._retrieval_service.get_degraded_status = MagicMock(
                return_value={"degraded_mode": False},
            )

            # Force _build_final_context to trigger trim
            monkeypatch.setattr(orch, "_count_tokens", lambda text: 500)
            monkeypatch.setattr(
                orch,
                "_trim_to_tokens_util",
                lambda text, limit: "gracefully-trimmed",
            )

            result = await svc.assemble_context(
                query="q",
                user_id="u1",
                conversation_id="c1",
                conversation_history=[{"role": "u", "content": "hi"}],
            )

        assert result["context"] == "gracefully-trimmed"

    def test_build_final_context_empty_layers(self):
        """Empty layers list produces empty context string."""
        budget = ContextBudget(total_tokens=500)
        final = ContextAssemblyService._build_final_context(
            [],
            remaining_tokens=500,
            budget=budget,
        )
        assert final == ""

    @pytest.mark.asyncio
    async def test_zero_remaining_skips_all_subsequent(self, monkeypatch):
        """System consumes entire budget; remaining=0 skips all subsequent layers."""
        budget = ContextBudget(
            total_tokens=60,
            system_tokens=60,
            long_term_tokens=0,
            working_memory_tokens=0,
            semantic_retrieval_tokens=0,
            ephemeral_tokens=0,
        )
        svc = _make_minimal_service()
        monkeypatch.setattr(orch.bm, "derive_budget", lambda **_kw: budget)

        long_term_mock = AsyncMock()
        working_mock = AsyncMock()
        semantic_mock = AsyncMock()
        ephemeral_mock = AsyncMock()

        async def system_fn(*_a, **_kw):
            return _make_layer("system", 60)

        with (
            _patch_layer("assemble_system_layer", side_effect=system_fn),
            patch.object(orch, "assemble_long_term_memory", long_term_mock),
            patch.object(orch, "assemble_working_memory", working_mock),
            patch.object(orch, "assemble_semantic_retrieval", semantic_mock),
            patch.object(orch, "assemble_ephemeral_memory", ephemeral_mock),
            _snapshot_patch("snap-zero"),
        ):
            result = await svc.assemble_context(
                query="q",
                user_id="u1",
                conversation_id="c1",
                conversation_history=[{"role": "u", "content": "hi"}],
            )

        assert result["remaining_tokens"] == 0
        assert len(result["layers"]) == 1
        assert result["layers"][0].name == "system"
        long_term_mock.assert_not_awaited()
        working_mock.assert_not_awaited()
        semantic_mock.assert_not_awaited()
        ephemeral_mock.assert_not_awaited()


# ======================================================================
# 6. RETRIEVAL FAILURES
# ======================================================================


class TestRetrievalFailures:
    """Did we lose important information?  (failure/edge cases)"""

    @pytest.mark.asyncio
    async def test_semantic_failure_triggers_minimal_context(self, monkeypatch):
        """Semantic raises exception → orchestrator returns minimal context."""
        budget = ContextBudget(
            total_tokens=500,
            system_tokens=100,
            long_term_tokens=100,
            working_memory_tokens=100,
            semantic_retrieval_tokens=100,
            ephemeral_tokens=100,
        )
        svc = _make_minimal_service()
        monkeypatch.setattr(orch.bm, "derive_budget", lambda **_kw: budget)

        async def boom(*_a, **_kw):
            raise RuntimeError("semantic retrieval failed")

        with (
            _patch_layer("assemble_system_layer", return_value=_make_layer("system", 30)),
            _patch_layer(
                "assemble_long_term_memory",
                return_value=_make_layer("long_term_memory", 20),
            ),
            _patch_layer("assemble_semantic_retrieval", side_effect=boom),
            _snapshot_patch("snap-semfail"),
        ):
            result = await svc.assemble_context(
                query="q",
                user_id="u1",
                conversation_id="c1",
            )

        # Exception bubbles up through the orchestrator's try/except (line 256)
        # → minimal context fallback with degraded_mode=True
        assert result["degraded_mode"] is True
        assert "semantic retrieval failed" in (result["degraded_reason"] or "")
        assert len(result["layers"]) == 0

    @pytest.mark.asyncio
    async def test_system_layer_failure_triggers_minimal_context(self, monkeypatch):
        """System layer raises → orchestrator returns minimal context."""
        budget = ContextBudget(
            total_tokens=500,
            system_tokens=100,
            long_term_tokens=100,
            working_memory_tokens=100,
            semantic_retrieval_tokens=100,
            ephemeral_tokens=100,
        )
        svc = _make_minimal_service()
        monkeypatch.setattr(orch.bm, "derive_budget", lambda **_kw: budget)

        async def boom(*_a, **_kw):
            raise RuntimeError("system layer failed")

        with (
            _patch_layer("assemble_system_layer", side_effect=boom),
            _snapshot_patch("snap-sysfail"),
        ):
            result = await svc.assemble_context(
                query="q",
                user_id="u1",
                conversation_id="c1",
            )

        assert result["degraded_mode"] is True
        assert "system layer failed" in (result["degraded_reason"] or "")
        assert len(result["layers"]) == 0

    @pytest.mark.asyncio
    async def test_multiple_layers_failure_triggers_minimal_context(self, monkeypatch):
        """Multiple layers fail → orchestrator returns minimal context."""
        budget = ContextBudget(
            total_tokens=500,
            system_tokens=100,
            long_term_tokens=100,
            working_memory_tokens=100,
            semantic_retrieval_tokens=100,
            ephemeral_tokens=100,
        )
        svc = _make_minimal_service()
        monkeypatch.setattr(orch.bm, "derive_budget", lambda **_kw: budget)

        async def boom(*_a, **_kw):
            raise RuntimeError("fail")

        with (
            _patch_layer("assemble_system_layer", return_value=_make_layer("system", 30)),
            _patch_layer("assemble_long_term_memory", side_effect=boom),
            _patch_layer("assemble_working_memory", side_effect=boom),
            _patch_layer("assemble_semantic_retrieval", side_effect=boom),
            _snapshot_patch("snap-multifail"),
        ):
            result = await svc.assemble_context(
                query="q",
                user_id="u1",
                conversation_id="c1",
            )

        # The first failure (long_term) causes assembly to abort → minimal context
        assert result["degraded_mode"] is True

    @pytest.mark.asyncio
    async def test_snapshotter_failure_returns_result_without_snapshot(
        self,
        monkeypatch,
    ):
        """create_snapshot raises; result falls back to minimal context."""
        budget = ContextBudget(
            total_tokens=200,
            system_tokens=100,
            long_term_tokens=50,
            working_memory_tokens=50,
            semantic_retrieval_tokens=50,
            ephemeral_tokens=50,
        )
        svc = _make_minimal_service()
        monkeypatch.setattr(orch.bm, "derive_budget", lambda **_kw: budget)

        with (
            _patch_layer("assemble_system_layer", return_value=_make_layer("system", 30)),
            _snapshot_patch(side_effect=RuntimeError("snapshotter error")),
        ):
            result = await svc.assemble_context(query="q", user_id="u1")

        # Snapshot failure is caught by try/except → returns minimal context
        assert result["context_snapshot_id"] is None
        assert result["degraded_mode"] is True

    @pytest.mark.asyncio
    async def test_embedding_unavailable_sets_degraded_mode(self, monkeypatch):
        """get_degraded_status returns degraded → degraded_mode=True in result."""
        budget = ContextBudget(
            total_tokens=500,
            system_tokens=100,
            long_term_tokens=50,
            working_memory_tokens=50,
            semantic_retrieval_tokens=200,
            ephemeral_tokens=100,
        )
        svc = _make_minimal_service()
        monkeypatch.setattr(orch.bm, "derive_budget", lambda **_kw: budget)

        with (
            _patch_layer("assemble_system_layer", return_value=_make_layer("system", 30)),
            _patch_layer(
                "assemble_semantic_retrieval",
                return_value=_make_layer(
                    "semantic_retrieval",
                    50,
                    metadata={"hard_stop_applied": False},
                ),
            ),
            _snapshot_patch("snap-deg"),
        ):
            svc._retrieval_service = MagicMock()
            svc._retrieval_service.get_degraded_status = MagicMock(
                return_value={
                    "degraded_mode": True,
                    "reason": "embedding model unavailable",
                },
            )

            result = await svc.assemble_context(
                query="q",
                user_id="u1",
                conversation_id="c1",
            )

        assert result["degraded_mode"] is True
        assert "embedding model unavailable" in result["degraded_reason"]

    @pytest.mark.asyncio
    async def test_retrieval_service_lacks_degraded_check_no_crash(self, monkeypatch):
        """Retrieval service without get_degraded_status doesn't crash."""
        budget = ContextBudget(
            total_tokens=500,
            system_tokens=100,
            long_term_tokens=50,
            working_memory_tokens=50,
            semantic_retrieval_tokens=200,
            ephemeral_tokens=100,
        )
        svc = _make_minimal_service()
        monkeypatch.setattr(orch.bm, "derive_budget", lambda **_kw: budget)

        with (
            _patch_layer("assemble_system_layer", return_value=_make_layer("system", 30)),
            _patch_layer(
                "assemble_semantic_retrieval",
                return_value=_make_layer(
                    "semantic_retrieval",
                    50,
                    metadata={"hard_stop_applied": False},
                ),
            ),
            _snapshot_patch("snap-nodeg"),
        ):
            # No get_degraded_status attribute
            svc._retrieval_service = object()

            result = await svc.assemble_context(query="q", user_id="u1")
            assert result["degraded_mode"] is False

    @pytest.mark.asyncio
    async def test_all_layers_failure_provides_minimal_context(self, monkeypatch):
        """Only system succeeds; all other layers fail. Returns valid minimal context."""
        budget = ContextBudget(
            total_tokens=500,
            system_tokens=100,
            long_term_tokens=100,
            working_memory_tokens=100,
            semantic_retrieval_tokens=100,
            ephemeral_tokens=100,
        )
        svc = _make_minimal_service()
        monkeypatch.setattr(orch.bm, "derive_budget", lambda **_kw: budget)

        async def boom(*_a, **_kw):
            raise RuntimeError("fail")

        with (
            _patch_layer("assemble_system_layer", return_value=_make_layer("system", 30)),
            _patch_layer("assemble_long_term_memory", side_effect=boom),
            _patch_layer("assemble_working_memory", side_effect=boom),
            _patch_layer("assemble_semantic_retrieval", side_effect=boom),
            _patch_layer("assemble_ephemeral_memory", side_effect=boom),
            _snapshot_patch("snap-almost"),
        ):
            result = await svc.assemble_context(
                query="q",
                user_id="u1",
                conversation_id="c1",
                conversation_history=[{"role": "u", "content": "hi"}],
            )

        # After system succeeds, long_term fails and exception propagates
        # to orchestrator's try/except → minimal context
        assert result["degraded_mode"] is True

    @pytest.mark.asyncio
    async def test_non_semantic_layer_returns_none_skipped_gracefully(
        self,
        monkeypatch,
    ):
        """Layers returning None are skipped without impacting other layers."""
        budget = ContextBudget(
            total_tokens=500,
            system_tokens=100,
            long_term_tokens=100,
            working_memory_tokens=100,
            semantic_retrieval_tokens=100,
            ephemeral_tokens=100,
        )
        svc = _make_minimal_service()
        monkeypatch.setattr(orch.bm, "derive_budget", lambda **_kw: budget)

        with (
            _patch_layer("assemble_system_layer", return_value=_make_layer("system", 30)),
            # long_term returns None (no data found)
            _patch_layer("assemble_long_term_memory", return_value=None),
            # working memory returns None (no data found)
            _patch_layer("assemble_working_memory", return_value=None),
            _patch_layer(
                "assemble_semantic_retrieval",
                return_value=_make_layer("semantic_retrieval", 50),
            ),
            _snapshot_patch("snap-skipnone"),
        ):
            svc._retrieval_service = MagicMock()
            svc._retrieval_service.get_degraded_status = MagicMock(
                return_value={"degraded_mode": False},
            )

            result = await svc.assemble_context(
                query="q",
                user_id="u1",
                conversation_id="c1",
            )

        names = [lyr.name for lyr in result["layers"]]
        assert names == ["system", "semantic_retrieval"]
