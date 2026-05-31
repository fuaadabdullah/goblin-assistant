from typing import Any, Dict, List
from unittest.mock import AsyncMock

import pytest

from api.semantic_chat_router import _context_has_content
from api.services.context_builder import ContextBuilder as AsyncContextBuilder
from api.services.retrieval_service import ContextBuilder as LegacyContextBuilder
from api.services.retrieval_service import RetrievalService

TOKEN_LIMIT = 8


def _mk_item(source_type: str, content: str, metadata: Dict[str, Any] | None = None) -> Dict[str, Any]:
    return {
        "id": f"{source_type}_1",
        "content": content,
        "source_type": source_type,
        "source_id": "conv_1",
        "metadata": metadata or {},
        "score": 0.9,
    }


@pytest.mark.asyncio
async def test_get_context_bundle_enforces_max_tokens(monkeypatch):
    service = RetrievalService()

    async def _fake_retrieve_context(**_kwargs) -> List[Dict[str, Any]]:
        return [
            _mk_item("memory", "M" * 20),  # ~5 tokens
            _mk_item("summary", "S" * 20),  # ~5 tokens
            _mk_item("message", "V" * 20),
            _mk_item("ephemeral", "E" * 20),
            _mk_item("task", "T" * 20),
        ]

    monkeypatch.setattr(service, "retrieve_context", _fake_retrieve_context)
    monkeypatch.setattr(
        "api.services.tool_result_memory_service.get_financial_profile",
        AsyncMock(return_value={}),
    )

    context_bundle = await service.get_context_bundle(
        query="token budget test",
        user_id="user_1",
        conversation_id="conv_1",
        max_tokens=TOKEN_LIMIT,
    )

    assert context_bundle["total_tokens"] <= TOKEN_LIMIT
    assert context_bundle["token_estimate"] == context_bundle["total_tokens"]
    assert len(context_bundle["memory_facts"]) == 1
    assert len(context_bundle["summaries"]) == 1
    assert context_bundle["summaries"][0]["metadata"]["truncated_for_token_budget"] is True
    assert context_bundle["messages"] == []
    assert context_bundle["ephemeral_messages"] == []
    assert context_bundle["tasks"] == []
    assert context_bundle["metadata"]["max_tokens_applied"] is True
    assert context_bundle["metadata"]["max_tokens"] == TOKEN_LIMIT


@pytest.mark.asyncio
async def test_get_context_bundle_exposes_ephemeral_bucket(monkeypatch):
    service = RetrievalService()

    async def _fake_retrieve_context(**_kwargs) -> List[Dict[str, Any]]:
        return [
            _mk_item("ephemeral", "recent message"),
            _mk_item("message", "retrieved vector message"),
        ]

    monkeypatch.setattr(service, "retrieve_context", _fake_retrieve_context)
    monkeypatch.setattr(
        "api.services.tool_result_memory_service.get_financial_profile",
        AsyncMock(return_value={}),
    )

    context_bundle = await service.get_context_bundle(
        query="ephemeral test",
        user_id="user_1",
        conversation_id="conv_1",
        max_tokens=100,
    )

    assert "ephemeral_messages" in context_bundle
    assert len(context_bundle["ephemeral_messages"]) == 1
    assert context_bundle["ephemeral_messages"][0]["source_type"] == "ephemeral"
    assert len(context_bundle["messages"]) == 1


@pytest.mark.asyncio
async def test_async_context_builder_uses_system_prompt_override(monkeypatch):
    builder = AsyncContextBuilder()

    def _should_not_call_default_prompt(_context: str) -> str:
        raise AssertionError("default system prompt path should not be used with override")

    monkeypatch.setattr(
        "api.services.context_builder.system_prompt_manager.config.get_prompt_with_context",
        _should_not_call_default_prompt,
    )

    context_bundle = {
        "summaries": [{"content": "summary 1"}],
        "memory_facts": [{"content": "memory 1"}],
        "messages": [{"content": "vector message 1"}],
        "ephemeral_messages": [{"content": "recent message 1"}],
        "tasks": [{"content": "task 1"}],
    }
    history = [{"role": "assistant", "content": "prior answer"}]

    prompt = await builder.build_contextual_prompt(
        user_id="user_1",
        context_bundle=context_bundle,
        user_message="latest question",
        conversation_history=history,
        system_prompt_override="OVERRIDE SYSTEM",
    )

    assert len(prompt) == 1
    assert prompt[0]["role"] == "system"
    assert prompt[0]["content"].startswith("OVERRIDE SYSTEM")
    assert "[EPHEMERAL] recent message 1" in prompt[0]["content"]
    assert "user: latest question" in prompt[0]["content"]


def test_legacy_context_builder_sync_compatibility():
    prompt = LegacyContextBuilder.build_contextual_prompt(
        user_message="hello",
        context_bundle={"summaries": [], "memory_facts": [], "messages": [], "tasks": []},
        conversation_history=[],
    )

    assert len(prompt) == 1
    assert prompt[0]["role"] == "system"
    assert "user: hello" in prompt[0]["content"]


def test_context_has_content_includes_ephemeral_messages():
    assert _context_has_content({"ephemeral_messages": [{"content": "recent"}]})
