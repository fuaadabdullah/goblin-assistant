"""Tests for token accuracy delta and failure recording in ContextAssemblyService."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.services.context_assembly_service.models import ContextBudget, ContextLayer
from api.services.context_assembly_service.orchestrator import ContextAssemblyService
from api.services.retrieval_metrics_service import RetrievalMetricsService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def metrics_svc() -> RetrievalMetricsService:
    return RetrievalMetricsService()


@pytest.fixture
def svc(metrics_svc) -> ContextAssemblyService:
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


def _make_layer(name: str, tokens: int) -> ContextLayer:
    return ContextLayer(name=name, content=f"content for {name}", tokens=tokens, metadata={})


def _patch_budget(budget: ContextBudget):
    return patch(
        "api.services.context_assembly_service.orchestrator.bm.derive_budget",
        return_value=budget,
    )


# ---------------------------------------------------------------------------
# Token delta written to assembly_log
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_token_delta_present_in_assembly_log(svc):
    budget = ContextBudget(
        total_tokens=500,
        system_tokens=50,
        long_term_tokens=50,
        working_memory_tokens=100,
        semantic_retrieval_tokens=100,
        ephemeral_tokens=200,
    )
    system_layer = _make_layer("SYSTEM", 40)

    with (
        _patch_budget(budget),
        patch(
            "api.services.context_assembly_service.orchestrator.assemble_system_layer",
            AsyncMock(return_value=system_layer),
        ),
        patch(
            "api.services.context_assembly_service.orchestrator.assemble_long_term_memory",
            AsyncMock(return_value=None),
        ),
        patch(
            "api.services.context_assembly_service.orchestrator.assemble_working_memory",
            AsyncMock(return_value=None),
        ),
        patch(
            "api.services.context_assembly_service.orchestrator.assemble_semantic_retrieval",
            AsyncMock(return_value=None),
        ),
        patch(
            "api.services.context_assembly_service.orchestrator.assemble_ephemeral_memory",
            AsyncMock(return_value=None),
        ),
        patch(
            "api.services.context_assembly_service.orchestrator.context_snapshotter.create_snapshot",
            AsyncMock(return_value="snap-1"),
        ),
    ):
        result = await svc.assemble_context(query="hello", user_id="u1")

    log = result["assembly_log"]
    assert "token_delta" in log
    assert "actual_final_tokens" in log
    # delta = actual - predicted; predicted = budget.total_tokens - remaining_tokens = 40
    assert isinstance(log["token_delta"], int)


@pytest.mark.asyncio
async def test_token_delta_zero_when_no_secondary_trim(svc):
    """If _build_final_context doesn't trim further, delta should equal the header overhead."""
    budget = ContextBudget(
        total_tokens=1000,
        system_tokens=100,
        long_term_tokens=100,
        working_memory_tokens=200,
        semantic_retrieval_tokens=200,
        ephemeral_tokens=400,
    )
    system_layer = _make_layer("SYSTEM", 50)

    with (
        _patch_budget(budget),
        patch(
            "api.services.context_assembly_service.orchestrator.assemble_system_layer",
            AsyncMock(return_value=system_layer),
        ),
        patch(
            "api.services.context_assembly_service.orchestrator.assemble_long_term_memory",
            AsyncMock(return_value=None),
        ),
        patch(
            "api.services.context_assembly_service.orchestrator.assemble_working_memory",
            AsyncMock(return_value=None),
        ),
        patch(
            "api.services.context_assembly_service.orchestrator.assemble_semantic_retrieval",
            AsyncMock(return_value=None),
        ),
        patch(
            "api.services.context_assembly_service.orchestrator.assemble_ephemeral_memory",
            AsyncMock(return_value=None),
        ),
        patch(
            "api.services.context_assembly_service.orchestrator.context_snapshotter.create_snapshot",
            AsyncMock(return_value="snap-1"),
        ),
    ):
        result = await svc.assemble_context(query="hello", user_id="u1")

    # Token delta should be >= 0 (format-string headers add tokens)
    assert result["assembly_log"]["token_delta"] >= 0


# ---------------------------------------------------------------------------
# Failure events recorded for skipped layers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_layer_skip_records_failure(svc):
    budget = ContextBudget(
        total_tokens=500,
        system_tokens=50,
        long_term_tokens=50,
        working_memory_tokens=100,
        semantic_retrieval_tokens=100,
        ephemeral_tokens=200,
    )
    system_layer = _make_layer("SYSTEM", 40)

    captured_failures = []

    def fake_record_failure(user_id, failure_type, layer, detail=""):
        captured_failures.append({"failure_type": failure_type, "layer": layer, "detail": detail})

    with (
        _patch_budget(budget),
        patch(
            "api.services.context_assembly_service.orchestrator.assemble_system_layer",
            AsyncMock(return_value=system_layer),
        ),
        patch(
            "api.services.context_assembly_service.orchestrator.assemble_long_term_memory",
            AsyncMock(return_value=None),  # layer skipped
        ),
        patch(
            "api.services.context_assembly_service.orchestrator.assemble_working_memory",
            AsyncMock(return_value=None),  # layer skipped
        ),
        patch(
            "api.services.context_assembly_service.orchestrator.assemble_semantic_retrieval",
            AsyncMock(return_value=None),  # layer skipped
        ),
        patch(
            "api.services.context_assembly_service.orchestrator.assemble_ephemeral_memory",
            AsyncMock(return_value=None),
        ),
        patch(
            "api.services.context_assembly_service.orchestrator.context_snapshotter.create_snapshot",
            AsyncMock(return_value="snap-1"),
        ),
    ):
        mock_rms = MagicMock()
        mock_rms.record_failure = fake_record_failure
        mock_rms.record_token_accuracy = MagicMock()
        mock_rms.record_assembly_latency = MagicMock()

        with patch(
            "api.services.context_assembly_service.orchestrator.ContextAssemblyService._push_failure",
            side_effect=fake_record_failure,
        ):
            await svc.assemble_context(query="hello", user_id="u1", conversation_id="c1")

    # long_term, working_memory, and semantic_retrieval should have triggered layer_skipped
    skipped_layers = {f["layer"] for f in captured_failures if f["failure_type"] == "layer_skipped"}
    assert "long_term_memory" in skipped_layers
    assert "working_memory" in skipped_layers
    assert "semantic_retrieval" in skipped_layers


# ---------------------------------------------------------------------------
# Metrics pushed via static helpers
# ---------------------------------------------------------------------------


def test_push_failure_is_silent_on_import_error():
    """_push_failure must not raise even if metrics service import fails."""
    with patch.dict("sys.modules", {"api.services.retrieval_metrics_service": None}):
        ContextAssemblyService._push_failure("u1", "layer_skipped", "long_term_memory")


def test_push_token_accuracy_is_silent_on_import_error():
    with patch.dict("sys.modules", {"api.services.retrieval_metrics_service": None}):
        ContextAssemblyService._push_token_accuracy("u1", 500, 520)


def test_record_layer_skip_detail_budget_exhausted():
    calls = []
    with patch.object(
        ContextAssemblyService, "_push_failure", side_effect=lambda *a, **kw: calls.append((a, kw))
    ):
        ContextAssemblyService._record_layer_skip(
            "u1", "working_memory", remaining=10, threshold=100
        )
    assert calls[0][0][3] == "skip_budget_exhausted"


def test_record_layer_skip_detail_no_data():
    calls = []
    with patch.object(
        ContextAssemblyService, "_push_failure", side_effect=lambda *a, **kw: calls.append((a, kw))
    ):
        ContextAssemblyService._record_layer_skip(
            "u1", "long_term_memory", remaining=200, threshold=50
        )
    assert calls[0][0][3] == "skip_no_data"
