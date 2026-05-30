"""Tests for OpenAIProvider — invoke, stream, health_check, embed, errors."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from api.providers.openai_provider import OpenAIProvider
from api.providers.base import ProviderResult, ProviderHealth


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _provider(
    api_key: str = "sk-test-key",
    endpoint: str = "https://api.openai.com/v1",
    default_model: str = "gpt-4o-mini",
) -> OpenAIProvider:
    """Build a provider instance with test config."""
    config = {
        "api_key_env": "OPENAI_API_KEY",
        "endpoint": endpoint,
        "default_model": default_model,
    }
    provider = OpenAIProvider("openai", config)
    provider._api_key = api_key
    provider._base_url = endpoint.rstrip("/")
    return provider


def _chat_response(
    text: str = "hello",
    model: str = "gpt-4o-mini",
    prompt_tokens: int = 5,
    completion_tokens: int = 3,
) -> dict:
    """Build a mock OpenAI chat response."""
    return {
        "choices": [{"message": {"content": text}}],
        "model": model,
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


def _stream_response(chunks: list[str]) -> list[str]:
    """Build mock OpenAI streaming response lines."""
    lines = []
    for chunk in chunks:
        data = f'{{"choices": [{{"delta": {{"content": "{chunk}"}}}}]}}'
        lines.append(f"data: {data}")
    lines.append("data: [DONE]")
    return lines


# ---------------------------------------------------------------------------
# invoke — successful cases
# ---------------------------------------------------------------------------


class TestInvokeSuccess:
    @pytest.mark.asyncio
    async def test_successful_invoke_with_messages(self):
        """Test successful invoke with message list."""
        provider = _provider()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _chat_response("world")
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await provider.invoke(
                messages=[{"role": "user", "content": "hi"}],
                model="gpt-4o-mini",
            )

        assert isinstance(result, ProviderResult)
        assert result.ok is True
        assert result.text == "world"
        assert result.provider == "openai"
        assert result.model == "gpt-4o-mini"
        assert result.usage["prompt_tokens"] == 5
        assert result.usage["completion_tokens"] == 3
        assert result.latency_ms > 0

    @pytest.mark.asyncio
    async def test_invoke_with_prompt(self):
        """Test invoke with prompt string instead of messages."""
        provider = _provider()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _chat_response("response")
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await provider.invoke(prompt="test prompt")

        assert result.ok is True
        assert result.text == "response"

    @pytest.mark.asyncio
    async def test_invoke_cost_calculation_gpt4o(self):
        """Test cost calculation for gpt-4o model."""
        provider = _provider()
        # gpt-4o costs: input 0.005, output 0.015 per 1k tokens
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _chat_response(
            "text",
            "gpt-4o",
            prompt_tokens=1000,
            completion_tokens=1000,
        )
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await provider.invoke(model="gpt-4o")

        # Cost = (1000 * 0.005 / 1000) + (1000 * 0.015 / 1000)
        # = 0.005 + 0.015 = 0.02
        assert result.ok is True
        assert result.cost_usd == 0.02

    @pytest.mark.asyncio
    async def test_invoke_uses_default_model(self):
        """Test invoke uses default model when not specified."""
        provider = _provider(default_model="gpt-4o-mini")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _chat_response()
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await provider.invoke(prompt="test")

        call_args = instance.post.call_args
        body = call_args.kwargs["json"]
        assert body["model"] == "gpt-4o-mini"
        assert result.ok is True

    @pytest.mark.asyncio
    async def test_invoke_with_custom_temperature_and_max_tokens(self):
        """Test invoke respects temperature and max_tokens parameters."""
        provider = _provider()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _chat_response()
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await provider.invoke(
                prompt="test",
                temperature=0.5,
                max_tokens=2048,
            )

        call_args = instance.post.call_args
        body = call_args.kwargs["json"]
        assert body["temperature"] == 0.5
        assert body["max_tokens"] == 2048
        assert result.ok is True


# ---------------------------------------------------------------------------
# invoke — error cases
# ---------------------------------------------------------------------------


class TestInvokeErrors:
    @pytest.mark.asyncio
    async def test_invoke_no_api_key(self):
        """Test invoke fails gracefully when API key is missing."""
        provider = _provider(api_key="")
        result = await provider.invoke(prompt="test")

        assert result.ok is False
        assert "OPENAI_API_KEY not set" in result.error

    @pytest.mark.asyncio
    async def test_invoke_http_error(self):
        """Test invoke handles HTTP errors."""
        provider = _provider()
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized",
            request=MagicMock(),
            response=MagicMock(),
        )

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await provider.invoke(prompt="test")

        assert result.ok is False
        assert result.error is not None
        assert result.latency_ms > 0

    @pytest.mark.asyncio
    async def test_invoke_connection_error(self):
        """Test invoke handles connection errors."""
        provider = _provider()

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await provider.invoke(prompt="test")

        assert result.ok is False
        assert "Connection refused" in result.error

    @pytest.mark.asyncio
    async def test_invoke_timeout_error(self):
        """Test invoke handles timeout errors."""
        provider = _provider()

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post = AsyncMock(side_effect=httpx.TimeoutException("Request timed out"))
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await provider.invoke(prompt="test")

        assert result.ok is False
        assert "Request timed out" in result.error


# ---------------------------------------------------------------------------
# stream
# ---------------------------------------------------------------------------


class TestStream:
    @pytest.mark.asyncio
    async def test_stream_success(self):
        """Test successful streaming."""
        provider = _provider()
        stream_lines = _stream_response(["hello", " ", "world"])

        async def mock_aiter_lines():
            for line in stream_lines:
                yield line

        mock_resp = AsyncMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.aiter_lines = mock_aiter_lines

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            stream_ctx = AsyncMock()
            stream_ctx.__aenter__ = AsyncMock(return_value=mock_resp)
            stream_ctx.__aexit__ = AsyncMock(return_value=False)
            instance.stream = MagicMock(return_value=stream_ctx)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            chunks = []
            async for chunk in provider.stream(prompt="test"):
                chunks.append(chunk["text"])

        assert chunks == ["hello", " ", "world"]

    @pytest.mark.asyncio
    async def test_stream_with_model(self):
        """Test stream respects model parameter."""
        provider = _provider()
        mock_resp = AsyncMock()
        mock_resp.raise_for_status = MagicMock()

        async def mock_aiter_lines():
            yield "data: [DONE]"

        mock_resp.aiter_lines = mock_aiter_lines

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            stream_ctx = AsyncMock()
            stream_ctx.__aenter__ = AsyncMock(return_value=mock_resp)
            stream_ctx.__aexit__ = AsyncMock(return_value=False)
            instance.stream = MagicMock(return_value=stream_ctx)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            async for _ in provider.stream(prompt="test", model="gpt-4o"):
                pass

            call_kwargs = instance.stream.call_args.kwargs
            assert call_kwargs["json"]["model"] == "gpt-4o"
            assert call_kwargs["json"]["stream"] is True


# ---------------------------------------------------------------------------
# health_check
# ---------------------------------------------------------------------------


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check."""
        provider = _provider()
        mock_resp = MagicMock()
        mock_resp.status_code = 200

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            health = await provider.health_check()

        assert isinstance(health, ProviderHealth)
        assert health.healthy is True
        assert health.error is None
        assert health.latency_ms > 0

    @pytest.mark.asyncio
    async def test_health_check_no_api_key(self):
        """Test health check fails when API key is missing."""
        provider = _provider(api_key="")
        health = await provider.health_check()

        assert health.healthy is False
        assert "No API key" in health.error

    @pytest.mark.asyncio
    async def test_health_check_http_error(self):
        """Test health check handles HTTP errors."""
        provider = _provider()
        mock_resp = MagicMock()
        mock_resp.status_code = 403

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            health = await provider.health_check()

        assert health.healthy is False
        assert "HTTP 403" in health.error

    @pytest.mark.asyncio
    async def test_health_check_connection_error(self):
        """Test health check handles connection errors."""
        provider = _provider()

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            health = await provider.health_check()

        assert health.healthy is False
        assert "Connection refused" in health.error


# ---------------------------------------------------------------------------
# embed
# ---------------------------------------------------------------------------


class TestEmbed:
    @pytest.mark.asyncio
    async def test_embed_single_text(self):
        """Test embedding a single text string."""
        provider = _provider()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": [{"embedding": [0.1, 0.2, 0.3]}]}
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await provider.embed("hello world")

        assert result == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_embed_multiple_texts(self):
        """Test embedding multiple texts."""
        provider = _provider()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": [
                {"embedding": [0.1, 0.2, 0.3]},
                {"embedding": [0.4, 0.5, 0.6]},
            ]
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await provider.embed(["hello", "world"])

        assert len(result) == 2
        assert result[0] == [0.1, 0.2, 0.3]
        assert result[1] == [0.4, 0.5, 0.6]

    @pytest.mark.asyncio
    async def test_embed_no_api_key(self):
        """Test embed raises error when API key is missing."""
        provider = _provider(api_key="")

        with pytest.raises(ValueError, match="OPENAI_API_KEY not set"):
            await provider.embed("test")

    @pytest.mark.asyncio
    async def test_embed_with_custom_model(self):
        """Test embed respects custom model parameter."""
        provider = _provider()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": [{"embedding": [0.1]}]}
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            await provider.embed("test", model="text-embedding-3-large")

            call_args = instance.post.call_args
            body = call_args.kwargs["json"]
            assert body["model"] == "text-embedding-3-large"
