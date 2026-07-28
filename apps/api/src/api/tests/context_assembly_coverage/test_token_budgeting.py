"""TokenBudgeting coverage for ContextAssemblyService."""

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
