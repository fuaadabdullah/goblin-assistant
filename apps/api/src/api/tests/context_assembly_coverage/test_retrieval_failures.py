"""RetrievalFailures coverage for ContextAssemblyService."""

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
