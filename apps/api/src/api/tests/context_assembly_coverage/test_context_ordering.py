"""ContextOrdering coverage for ContextAssemblyService."""

from unittest.mock import MagicMock

import pytest

from .helpers import (
    ContextBudget,
    _make_layer,
    _make_minimal_service,
    _patch_layer,
    _snapshot_patch,
    orch,
)


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
