import pytest

from api.services.embedding_service import EmbeddingService
from api.services.retrieval_service import RetrievalService
from api.services.context_assembly_service import ContextAssemblyService


class _CaptureEmbedProvider:
    def __init__(self):
        self.last_text = None

    async def embed(self, texts, model=None):
        self.last_text = texts if isinstance(texts, str) else texts[0]
        return [0.1, 0.2, 0.3]


@pytest.mark.asyncio
async def test_embedding_truncation_is_token_based_not_character_based():
    service = EmbeddingService()
    provider = _CaptureEmbedProvider()
    service.client = provider

    # 9000 chars, but ~2250 tokens with fallback estimation; should NOT be char-truncated to 8000.
    long_text = "a" * 9000
    _ = await service.embed_text(long_text)

    assert provider.last_text == long_text


@pytest.mark.asyncio
async def test_context_assembly_accepts_model_aware_budgeting(monkeypatch):
    service = ContextAssemblyService()

    # Prevent DB/retrieval access for this contract test.
    async def _no_layer(*args, **kwargs):
        return None

    monkeypatch.setattr(service, "_assemble_system_layer", _no_layer)
    monkeypatch.setattr(service, "_assemble_long_term_memory", _no_layer)
    monkeypatch.setattr(service, "_assemble_working_memory", _no_layer)
    monkeypatch.setattr(service, "_assemble_semantic_retrieval", _no_layer)
    monkeypatch.setattr(service, "_assemble_ephemeral_memory", _no_layer)

    from api.observability.context_snapshotter import context_snapshotter

    async def _snapshot_stub(**_kwargs):
        return "ctx_snapshot_test"

    monkeypatch.setattr(context_snapshotter, "create_snapshot", _snapshot_stub)

    result = await service.assemble_context(
        query="hi",
        user_id="u1",
        conversation_id=None,
        conversation_history=[],
        model="gpt-4o-mini",
    )

    assert "total_tokens_used" in result


def test_background_and_chat_use_same_dispatcher_path():
    with open("/Volumes/GOBLINOS 1/apps/.../api/services/background_tasks.py", "r", encoding="utf-8") as f:
        bg = f.read()
    with open("/Volumes/GOBLINOS 1/apps/.../api/chat_router.py", "r", encoding="utf-8") as f:
        chat = f.read()

    assert "from ..providers.dispatcher import invoke_provider" in bg
    assert "from .providers.dispatcher import invoke_provider" in chat
    assert "dispatcher_fixed" not in bg
    assert "dispatcher_fixed" not in chat


@pytest.mark.asyncio
async def test_retrieval_surfaces_embedding_degraded_mode(monkeypatch):
    service = RetrievalService()

    async def _fail_embed(_text):
        raise RuntimeError("missing-openai-key")

    monkeypatch.setattr(service.embedding_service, "embed_text", _fail_embed)

    result = await service.retrieve_context(query="hello", user_id="u1")

    assert result == []
    status = service.get_degraded_status()
    assert status["degraded_mode"] is True
    assert "missing-openai-key" in status["reason"]
