"""Unit tests for the ollama-python-backed OllamaProvider."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from api.providers.ollama_provider import OllamaProvider


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChatResponse:
    def __init__(self, content: str, prompt_tokens: int = 0, completion_tokens: int = 0) -> None:
        self.message = _FakeMessage(content)
        self.prompt_eval_count = prompt_tokens
        self.eval_count = completion_tokens
        self.done = True


class _FakeStreamChunk:
    def __init__(self, content: str, done: bool = False) -> None:
        self.message = _FakeMessage(content)
        self.done = done


@pytest.fixture
def provider() -> OllamaProvider:
    return OllamaProvider("ollama_local", {"endpoint": "http://localhost:11434"})


async def test_invoke_uses_native_chat(provider: OllamaProvider) -> None:
    chat = AsyncMock(return_value=_FakeChatResponse("hello", 1, 2))
    with patch.object(provider._client, "chat", chat):
        result = await provider.invoke(messages=[{"role": "user", "content": "hi"}])

    assert result.ok is True
    assert result.text == "hello"
    assert result.usage["prompt_tokens"] == 1
    assert result.usage["completion_tokens"] == 2
    assert chat.await_args.kwargs["model"] == "qwen2.5:3b"
    assert chat.await_args.kwargs["stream"] is False
    assert chat.await_args.kwargs["options"]["num_predict"] == 4096


async def test_invoke_returns_failure_on_error(provider: OllamaProvider) -> None:
    chat = AsyncMock(side_effect=RuntimeError("boom"))
    with patch.object(provider._client, "chat", chat):
        result = await provider.invoke(messages=[{"role": "user", "content": "hi"}])

    assert result.ok is False
    assert "boom" in (result.error or "")


async def test_stream_yields_text_chunks(provider: OllamaProvider) -> None:
    async def _stream():
        yield _FakeStreamChunk("he")
        yield _FakeStreamChunk("llo")
        yield _FakeStreamChunk("", done=True)

    chat = AsyncMock()
    chat.return_value = _stream()
    with patch.object(provider._client, "chat", chat):
        collected = [
            chunk["text"]
            async for chunk in provider.stream(messages=[{"role": "user", "content": "hi"}])
        ]

    assert collected == ["he", "llo"]


async def test_health_check_uses_list(provider: OllamaProvider) -> None:
    with patch.object(provider._client, "list", AsyncMock(return_value=[])):
        health = await provider.health_check()

    assert health.healthy is True
