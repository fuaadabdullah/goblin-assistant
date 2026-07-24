"""SourceAttribution coverage for ContextAssemblyService."""

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
