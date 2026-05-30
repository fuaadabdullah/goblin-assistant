import pytest

from api.services import context_assembly_service as cas
from api.services.context_assembly_service import (
    ContextAssemblyService,
    ContextBudget,
    ContextLayer,
)
from api.services.context_assembly_service import orchestrator as orch


def _build_service(monkeypatch, budget=None):
    if budget is None:
        budget = ContextBudget(
            total_tokens=1000,
            system_tokens=100,
            long_term_tokens=100,
            working_memory_tokens=200,
            semantic_retrieval_tokens=300,
            ephemeral_tokens=300,
        )

    monkeypatch.setattr(orch.bm, "load_budget_config", lambda: budget)
    monkeypatch.setattr(orch.bm, "load_model_context_windows", lambda: {})
    return ContextAssemblyService()


def test_package_exports_and_models_property():
    assert "ContextAssemblyService" in cas.__all__
    assert isinstance(cas.context_assembly_service, ContextAssemblyService)

    budget = ContextBudget(
        total_tokens=1000,
        system_tokens=100,
        long_term_tokens=100,
        working_memory_tokens=200,
    )
    assert budget.available_for_retrieval == 600


@pytest.mark.asyncio
async def test_orchestrator_happy_path(monkeypatch):
    service = _build_service(monkeypatch)
    monkeypatch.setattr(orch.bm, "derive_budget", lambda **_kwargs: service.default_budget)

    async def _system(_remaining, _budget):
        return ContextLayer(name="system", content="sys", tokens=50)

    async def _long_term(_user_id, _remaining, _budget):
        return ContextLayer(name="long_term_memory", content="ltm", tokens=40)

    async def _working(_user_id, _conversation_id, _remaining, _budget):
        return ContextLayer(name="working_memory", content="wm", tokens=30)

    async def _semantic(_query, _user_id, _conversation_id, _remaining, _correlation_id, _budget):
        return ContextLayer(
            name="semantic_retrieval",
            content="sem",
            tokens=80,
            metadata={"hard_stop_applied": False},
        )

    async def _ephemeral(_history, _remaining, _budget):
        return ContextLayer(
            name="ephemeral_memory",
            content="eph",
            tokens=20,
            metadata={"truncated": False, "summary_fallback_applied": False},
        )

    async def _snapshot(**_kwargs):
        return "snap-123"

    monkeypatch.setattr(orch, "assemble_system_layer", _system)
    monkeypatch.setattr(orch, "assemble_long_term_memory", _long_term)
    monkeypatch.setattr(orch, "assemble_working_memory", _working)
    monkeypatch.setattr(orch, "assemble_semantic_retrieval", _semantic)
    monkeypatch.setattr(orch, "assemble_ephemeral_memory", _ephemeral)
    monkeypatch.setattr(orch.context_snapshotter, "create_snapshot", _snapshot)

    service._retrieval_service = type(
        "RS", (), {"get_degraded_status": lambda self: {"degraded_mode": False}}
    )()

    result = await service.assemble_context(
        query="hello",
        user_id="u1",
        conversation_id="c1",
        conversation_history=[{"role": "user", "content": "hi"}],
    )

    assert result["context_snapshot_id"] == "snap-123"
    assert result["total_tokens_used"] == 220
    assert result["remaining_tokens"] == 780
    assert [layer.name for layer in result["layers"]] == [
        "system",
        "long_term_memory",
        "working_memory",
        "semantic_retrieval",
        "ephemeral_memory",
    ]
    assert result["assembly_log"]["layers"] == [
        "system",
        "long_term",
        "working_memory",
        "semantic_retrieval",
        "ephemeral",
    ]
    assert "[SYSTEM]" in result["context"]


@pytest.mark.asyncio
async def test_orchestrator_skips_working_and_ephemeral_without_inputs(monkeypatch):
    service = _build_service(monkeypatch)
    monkeypatch.setattr(orch.bm, "derive_budget", lambda **_kwargs: service.default_budget)

    calls = {"working": 0, "ephemeral": 0}

    async def _system(_remaining, _budget):
        return ContextLayer(name="system", content="sys", tokens=50)

    async def _long_term(_user_id, _remaining, _budget):
        return None

    async def _working(*_args, **_kwargs):
        calls["working"] += 1

    async def _semantic(*_args, **_kwargs):
        return None

    async def _ephemeral(*_args, **_kwargs):
        calls["ephemeral"] += 1

    async def _snapshot(**_kwargs):
        return "snap-124"

    monkeypatch.setattr(orch, "assemble_system_layer", _system)
    monkeypatch.setattr(orch, "assemble_long_term_memory", _long_term)
    monkeypatch.setattr(orch, "assemble_working_memory", _working)
    monkeypatch.setattr(orch, "assemble_semantic_retrieval", _semantic)
    monkeypatch.setattr(orch, "assemble_ephemeral_memory", _ephemeral)
    monkeypatch.setattr(orch.context_snapshotter, "create_snapshot", _snapshot)

    service._retrieval_service = type(
        "RS", (), {"get_degraded_status": lambda self: {"degraded_mode": False}}
    )()

    result = await service.assemble_context(
        query="hello",
        user_id="u1",
        conversation_id=None,
        conversation_history=None,
    )

    assert result["context_snapshot_id"] == "snap-124"
    assert calls["working"] == 0
    assert calls["ephemeral"] == 0


@pytest.mark.asyncio
async def test_orchestrator_degraded_reason_merges_retrieval_and_truncation(
    monkeypatch,
):
    service = _build_service(monkeypatch)
    monkeypatch.setattr(orch.bm, "derive_budget", lambda **_kwargs: service.default_budget)

    async def _system(_remaining, _budget):
        return ContextLayer(name="system", content="sys", tokens=20)

    async def _none(*_args, **_kwargs):
        return None

    async def _semantic(*_args, **_kwargs):
        return ContextLayer(
            name="semantic_retrieval",
            content="sem",
            tokens=50,
            metadata={"hard_stop_applied": True},
        )

    async def _ephemeral(*_args, **_kwargs):
        return ContextLayer(
            name="ephemeral_memory",
            content="eph",
            tokens=40,
            metadata={"truncated": True, "summary_fallback_applied": True},
        )

    async def _snapshot(**_kwargs):
        return "snap-125"

    monkeypatch.setattr(orch, "assemble_system_layer", _system)
    monkeypatch.setattr(orch, "assemble_long_term_memory", _none)
    monkeypatch.setattr(orch, "assemble_working_memory", _none)
    monkeypatch.setattr(orch, "assemble_semantic_retrieval", _semantic)
    monkeypatch.setattr(orch, "assemble_ephemeral_memory", _ephemeral)
    monkeypatch.setattr(orch.context_snapshotter, "create_snapshot", _snapshot)

    service._retrieval_service = type(
        "RS",
        (),
        {
            "get_degraded_status": lambda self: {
                "degraded_mode": True,
                "reason": "embedding unavailable",
            }
        },
    )()

    result = await service.assemble_context(
        query="hello",
        user_id="u1",
        conversation_id="c1",
        conversation_history=[{"role": "user", "content": "hi"}],
    )

    assert result["degraded_mode"] is True
    assert result["truncation_warnings"] == [
        "semantic_retrieval_truncated",
        "ephemeral_memory_truncated",
        "ephemeral_summary_fallback_applied",
    ]
    assert result["summary_fallback_applied"] is True
    assert "embedding unavailable" in (result["degraded_reason"] or "")
    assert "context_truncated:" in (result["degraded_reason"] or "")


@pytest.mark.asyncio
async def test_orchestrator_exception_fallback_returns_minimal_context(monkeypatch):
    service = _build_service(monkeypatch)
    monkeypatch.setattr(orch.bm, "derive_budget", lambda **_kwargs: service.default_budget)

    async def _boom(*_args, **_kwargs):
        raise RuntimeError("system layer failed")

    monkeypatch.setattr(orch, "assemble_system_layer", _boom)

    result = await service.assemble_context(query="what now", user_id="u1")

    assert result["degraded_mode"] is True
    assert result["total_tokens_used"] == 0
    assert result["context_snapshot_id"] is None
    assert "minimal context" in result["context"]
    assert "system layer failed" in (result["degraded_reason"] or "")


@pytest.mark.asyncio
async def test_get_minimal_context_includes_query():
    text = await ContextAssemblyService._get_minimal_context("hello")

    assert "Query: hello" in text
    assert "minimal context" in text


def test_build_final_context_trims_when_joined_text_exceeds_used_budget(monkeypatch):
    layers = [ContextLayer(name="system", content="x" * 500, tokens=100)]
    budget = ContextBudget(total_tokens=200)

    monkeypatch.setattr(orch, "_count_tokens", lambda _text: 500)
    monkeypatch.setattr(orch, "_trim_to_tokens_util", lambda _text, _limit: "trimmed-final")

    final = ContextAssemblyService._build_final_context(layers, remaining_tokens=120, budget=budget)

    assert final == "trimmed-final"
