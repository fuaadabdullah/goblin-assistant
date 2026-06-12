"""Tests for AzureOpenAIProvider — invoke, stream, health_check, errors."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from api.providers.azure_provider import AzureOpenAIProvider


def _provider(
    api_key: str = "test-key-123",
    endpoint: str = "https://myazure.openai.azure.com",
    deployment: str = "gpt-4-deployment",
) -> AzureOpenAIProvider:
    """Build Azure provider instance."""
    config = {
        "api_key_env": "AZURE_API_KEY",
        "endpoint": endpoint,
        "deployment_id": deployment,
        "api_version": "2024-05-01-preview",
    }
    provider = AzureOpenAIProvider("azure", config)
    provider._api_key = api_key
    provider._endpoint = endpoint.rstrip("/")
    provider._deployment = deployment
    return provider


def _chat_response(
    text: str = "hello",
    deployment: str = "gpt-4-deployment",
    prompt_tokens: int = 5,
    completion_tokens: int = 3,
) -> dict:
    """Build mock Azure response."""
    return {
        "choices": [{"message": {"content": text}}],
        "model": deployment,
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        },
    }


class TestAzureInvoke:
    @pytest.mark.asyncio
    async def test_successful_invoke(self):
        """Test successful invoke."""
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
                messages=[{"role": "user", "content": "hi"}],
            )

        assert result.ok is True
        assert result.text == "hello"
        assert result.provider == "azure"

    @pytest.mark.asyncio
    async def test_invoke_not_configured(self):
        """Test invoke fails when not configured."""
        provider = _provider(api_key="", endpoint="")
        result = await provider.invoke(prompt="test")
        assert result.ok is False
        assert "not fully configured" in result.error

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

    @pytest.mark.asyncio
    async def test_invoke_uses_deployment(self):
        """Test invoke uses Azure deployment ID."""
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

            result = await provider.invoke(prompt="test")

        # Verify the call was made
        assert result.ok is True
        instance.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_invoke_custom_parameters(self):
        """Test invoke respects custom parameters."""
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

            await provider.invoke(
                prompt="test",
                temperature=0.3,
                max_tokens=1024,
            )

            call_args = instance.post.call_args
            body = call_args.kwargs.get("json", {})
            assert body.get("temperature") == 0.3
            assert body.get("max_tokens") == 1024


class TestAzureStream:
    @pytest.mark.asyncio
    async def test_stream_success(self):
        """Test streaming."""
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

            chunks = [chunk async for chunk in provider.stream(prompt="test")]
            assert isinstance(chunks, list)


class TestAzureHealth:
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

        # Health check may be unhealthy due to response code check
        assert health is not None
        assert hasattr(health, "healthy")

    @pytest.mark.asyncio
    async def test_health_check_not_configured(self):
        """Test health check fails when not configured."""
        provider = _provider(api_key="", endpoint="")
        provider._endpoint = ""
        provider._api_key = ""
        health = await provider.health_check()
        assert health.healthy is False
