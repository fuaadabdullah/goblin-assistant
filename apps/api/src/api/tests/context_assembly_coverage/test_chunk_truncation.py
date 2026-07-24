"""ChunkTruncation coverage for ContextAssemblyService."""

from unittest.mock import MagicMock

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
