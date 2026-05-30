"""Tests for AnthropicProvider — invoke, stream, health_check, errors."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from api.providers.anthropic_provider import AnthropicProvider


def _provider(
    api_key: str = "sk-ant-test-key",
    endpoint: str = "https://api.anthropic.com",
    default_model: str = "claude-3-5-haiku-latest",
) -> AnthropicProvider:
    """Build Anthropic provider instance."""
    config = {
        "api_key_env": "ANTHROPIC_API_KEY",
        "endpoint": endpoint,
        "default_model": default_model,
    }
    provider = AnthropicProvider("anthropic", config)
    provider._api_key = api_key
    provider._base_url = endpoint.rstrip("/")
    return provider


def _chat_response(
    text: str = "hello",
    model: str = "claude-3-5-haiku-latest",
    prompt_tokens: int = 5,
    completion_tokens: int = 3,
) -> dict:
    """Build mock Anthropic response."""
    return {
        "content": [{"type": "text", "text": text}],
        "model": model,
        "usage": {
            "input_tokens": prompt_tokens,
            "output_tokens": completion_tokens,
        },
    }


class TestAnthropicInvoke:
    @pytest.mark.asyncio
    async def test_successful_invoke(self):
        """Test successful invoke with messages."""
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

            result = await provider.invoke(
                messages=[{"role": "user", "content": "hi"}],
                model="claude-3-5-haiku-latest",
            )

        assert result.ok is True
        assert result.text == "response"
        assert result.provider == "anthropic"

    @pytest.mark.asyncio
    async def test_invoke_with_system_message(self):
        """Test invoke handles system message separation."""
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
                messages=[
                    {"role": "system", "content": "You are helpful"},
                    {"role": "user", "content": "hi"},
                ]
            )

        assert result.ok is True
        call_args = instance.post.call_args
        body = call_args.kwargs["json"]
        assert "system" in body

    @pytest.mark.asyncio
    async def test_invoke_cost_calculation(self):
        """Test cost calculation for Anthropic models."""
        provider = _provider()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _chat_response(
            model="claude-3-5-sonnet",
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

            result = await provider.invoke(model="claude-3-5-sonnet")

        # Cost = (1000 * 0.003 / 1000) + (1000 * 0.015 / 1000) = 0.018
        assert result.ok is True
        assert result.cost_usd == 0.018

    @pytest.mark.asyncio
    async def test_invoke_no_api_key(self):
        """Test invoke fails without API key."""
        provider = _provider(api_key="")
        result = await provider.invoke(prompt="test")
        assert result.ok is False
        assert "not set" in result.error or "API key" in result.error

    @pytest.mark.asyncio
    async def test_invoke_http_error(self):
        """Test invoke handles HTTP errors."""
        provider = _provider()
        mock_resp = MagicMock()
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


class TestAnthropicStream:
    @pytest.mark.asyncio
    async def test_stream_success(self):
        """Test streaming response."""
        provider = _provider()

        async def mock_aiter_lines():
            yield "data: [DONE]"

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

            chunks = [chunk async for chunk in provider.stream(prompt="test")]

        assert isinstance(chunks, list)


class TestAnthropicHealth:
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

        assert health.healthy is True

    @pytest.mark.asyncio
    async def test_health_check_no_api_key(self):
        """Test health check fails without API key."""
        provider = _provider(api_key="")
        health = await provider.health_check()
        assert health.healthy is False
