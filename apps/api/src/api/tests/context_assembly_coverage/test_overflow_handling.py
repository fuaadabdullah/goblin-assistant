"""OverflowHandling coverage for ContextAssemblyService."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from .helpers import (
    ContextAssemblyService,
    ContextBudget,
    _make_layer,
    _make_minimal_service,
    _patch_layer,
    _snapshot_patch,
    orch,
)


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
