import pytest
from pathlib import Path

from api.services.context_assembly_service import (
    ContextAssemblyService,
    ContextLayer,
    ContextBudget,
)
from api.services.context_assembly_service import ephemeral_layer as _ephemeral_mod
from api.services.context_assembly_service import orchestrator as _orch_mod


PROJECT_ROOT = Path("/Volumes/GOBLINOS 1/apps/...")


def test_main_dotenv_load_block_is_not_duplicated():
    main_py = (PROJECT_ROOT / "api" / "main.py").read_text(encoding="utf-8")
    assert main_py.count("# Load environment variables from .env.local if it exists") == 1


@pytest.mark.parametrize(
    "relative_path",
    [
        Path("api/main.py"),
        Path("api/chat_router.py"),
        Path("api/services/retrieval_service.py"),
    ],
)
def test_critical_runtime_files_do_not_use_print(relative_path: Path):
    content = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
    assert "print(" not in content


@pytest.mark.asyncio
async def test_ephemeral_layer_marks_truncation_and_summary_fallback():
    from api.services.context_assembly_service.ephemeral_layer import assemble_ephemeral_memory

    budget = ContextBudget(total_tokens=200, ephemeral_tokens=70)
    history = [
        {"role": "user", "content": "very long message " * 30},
        {"role": "assistant", "content": "very long response " * 30},
        {"role": "user", "content": "another long message " * 30},
        {"role": "assistant", "content": "another long response " * 30},
        {"role": "user", "content": "follow up " * 30},
        {"role": "assistant", "content": "final note " * 30},
    ]

    layer = await assemble_ephemeral_memory(
        conversation_history=history,
        remaining_tokens=70,
        budget=budget,
    )

    assert layer is not None
    assert layer.metadata["truncated"] is True
    assert layer.metadata["summary_fallback_applied"] is True


@pytest.mark.asyncio
async def test_assemble_context_surfaces_truncation_warnings(monkeypatch):
    service = ContextAssemblyService()

    async def _system(*_args, **_kwargs):
        return ContextLayer(name="system", content="s", tokens=10, metadata={})

    async def _none(*_args, **_kwargs):
        return None

    async def _semantic(*_args, **_kwargs):
        return ContextLayer(
            name="semantic_retrieval",
            content="x",
            tokens=20,
            metadata={"hard_stop_applied": True},
        )

    async def _ephemeral(*_args, **_kwargs):
        return ContextLayer(
            name="ephemeral_memory",
            content="y",
            tokens=20,
            metadata={"truncated": True, "summary_fallback_applied": True},
        )

    monkeypatch.setattr(_orch_mod, "assemble_system_layer", _system)
    monkeypatch.setattr(_orch_mod, "assemble_long_term_memory", _none)
    monkeypatch.setattr(_orch_mod, "assemble_working_memory", _none)
    monkeypatch.setattr(_orch_mod, "assemble_semantic_retrieval", _semantic)
    monkeypatch.setattr(_orch_mod, "assemble_ephemeral_memory", _ephemeral)

    # Prevent lazy retrieval_service property from triggering embedding import chain
    service._retrieval_service = type("FakeRS", (), {"get_degraded_status": lambda self: {}})()

    from api.observability.context_snapshotter import context_snapshotter

    async def _snapshot_stub(**_kwargs):
        return "ctx_snapshot_entropy_test"

    monkeypatch.setattr(context_snapshotter, "create_snapshot", _snapshot_stub)

    result = await service.assemble_context(
        query="q",
        user_id="u1",
        conversation_id="c1",
        conversation_history=[{"role": "user", "content": "hello"}],
    )

    assert result["degraded_mode"] is True
    assert "context_truncated" in (result.get("degraded_reason") or "")
    assert "semantic_retrieval_truncated" in result["truncation_warnings"]
    assert result["summary_fallback_applied"] is True


def test_user_model_uses_boolean_is_active():
    from api.storage.models import UserModel

    column = UserModel.__table__.c.is_active
    assert column.type.__class__.__name__.lower() == "boolean"
