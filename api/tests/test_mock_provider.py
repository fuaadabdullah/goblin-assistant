"""Tests for MockProvider — invoke, stream, embed, and response generation."""

from __future__ import annotations

import pytest

from api.providers.mock_provider import MockProvider
from api.providers.base import ProviderResult, ProviderHealth


def _provider() -> MockProvider:
    return MockProvider("mock", {"default_model": "mock-gpt"})


# ---------------------------------------------------------------------------
# invoke
# ---------------------------------------------------------------------------

class TestInvoke:
    @pytest.mark.asyncio
    async def test_returns_provider_result(self):
        provider = _provider()
        result = await provider.invoke(prompt="hello")
        assert isinstance(result, ProviderResult)
        assert result.ok is True
        assert result.provider == "mock"
        assert result.model == "mock-gpt"
        assert result.latency_ms > 0

    @pytest.mark.asyncio
    async def test_greeting_pattern(self):
        provider = _provider()
        result = await provider.invoke(prompt="hello there")
        assert "mock response" in result.text.lower()
        assert "Goblin Assistant" in result.text

    @pytest.mark.asyncio
    async def test_code_pattern(self):
        provider = _provider()
        result = await provider.invoke(prompt="write python code")
        assert "code" in result.text.lower() or "readable" in result.text.lower()

    @pytest.mark.asyncio
    async def test_empty_prompt(self):
        provider = _provider()
        result = await provider.invoke(prompt="")
        assert result.ok is True
        assert result.text == "Mock response."

    @pytest.mark.asyncio
    async def test_generic_prompt(self):
        provider = _provider()
        result = await provider.invoke(prompt="tell me about the weather")
        assert "Mock response to:" in result.text

    @pytest.mark.asyncio
    async def test_messages_override_prompt(self):
        provider = _provider()
        result = await provider.invoke(
            messages=[{"role": "user", "content": "hey buddy"}],
            prompt="ignored",
        )
        assert "Goblin Assistant" in result.text  # triggers greeting branch

    @pytest.mark.asyncio
    async def test_model_override(self):
        provider = _provider()
        result = await provider.invoke(prompt="hi", model="custom-model")
        assert result.model == "custom-model"


# ---------------------------------------------------------------------------
# stream
# ---------------------------------------------------------------------------

class TestStream:
    @pytest.mark.asyncio
    async def test_yields_word_chunks(self):
        provider = _provider()
        chunks = []
        async for chunk in provider.stream(prompt="hello"):
            chunks.append(chunk)

        assert len(chunks) > 0
        assert all("text" in c for c in chunks)
        full_text = "".join(c["text"] for c in chunks).strip()
        assert len(full_text) > 0

    @pytest.mark.asyncio
    async def test_stream_with_messages(self):
        provider = _provider()
        chunks = []
        async for chunk in provider.stream(
            messages=[{"role": "user", "content": "write python code"}]
        ):
            chunks.append(chunk)

        assert len(chunks) > 0


# ---------------------------------------------------------------------------
# embed
# ---------------------------------------------------------------------------

class TestEmbed:
    @pytest.mark.asyncio
    async def test_single_text_returns_flat_list(self):
        provider = _provider()
        embedding = await provider.embed("hello world")
        assert isinstance(embedding, list)
        assert len(embedding) == 32
        assert all(isinstance(v, float) for v in embedding)

    @pytest.mark.asyncio
    async def test_multiple_texts_returns_nested_lists(self):
        provider = _provider()
        embeddings = await provider.embed(["hello", "world"])
        assert isinstance(embeddings, list)
        assert len(embeddings) == 2
        assert all(len(e) == 32 for e in embeddings)

    @pytest.mark.asyncio
    async def test_embedding_values_in_range(self):
        provider = _provider()
        embedding = await provider.embed("test")
        assert all(-1 <= v <= 1 for v in embedding)


# ---------------------------------------------------------------------------
# health_check
# ---------------------------------------------------------------------------

class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_always_healthy(self):
        provider = _provider()
        health = await provider.health_check()
        assert isinstance(health, ProviderHealth)
        assert health.healthy is True
        assert health.latency_ms >= 0
