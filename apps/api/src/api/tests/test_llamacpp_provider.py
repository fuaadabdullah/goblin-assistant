"""Tests for LlamaCPPProvider — invoke, stream, health_check, and error paths."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from api.providers.base import ProviderHealth, ProviderResult
from api.providers.llamacpp_provider import LlamaCPPProvider

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _provider(endpoint: str = "http://llama.test:8000") -> LlamaCPPProvider:
    """Build a provider instance with a deterministic endpoint."""
    return LlamaCPPProvider(
        "llamacpp_gcp",
        {
            "endpoint": endpoint,
            "endpoint_env": "LLAMACPP_GCP_ENDPOINT",
            "default_model": "qwen2.5-3b",
            "models": ["qwen2.5-3b"],
        },
    )


def _chat_response(text: str = "hello", model: str = "qwen2.5-3b") -> dict:
    return {
        "choices": [{"message": {"content": text}}],
        "model": model,
        "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
    }


# ---------------------------------------------------------------------------
# invoke
# ---------------------------------------------------------------------------


class TestInvoke:
    @pytest.mark.asyncio
    async def test_successful_invoke(self):
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
                model="qwen2.5-3b",
            )

        assert isinstance(result, ProviderResult)
        assert result.ok is True
        assert result.text == "world"
        assert result.model == "qwen2.5-3b"
        assert result.cost_usd == 0.0
        assert result.latency_ms > 0

    @pytest.mark.asyncio
    async def test_invoke_no_endpoint(self):
        provider = _provider(endpoint="")
        provider._base_url = ""
        result = await provider.invoke(prompt="test")
        assert result.ok is False
        assert "not configured" in result.error

    @pytest.mark.asyncio
    async def test_invoke_http_error(self):
        provider = _provider()

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "500 Internal Server Error",
                    request=MagicMock(),
                    response=MagicMock(status_code=500),
                )
            )
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await provider.invoke(prompt="test")

        assert result.ok is False
        assert "500" in result.error
        assert result.latency_ms > 0

    @pytest.mark.asyncio
    async def test_invoke_timeout(self):
        provider = _provider()

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post = AsyncMock(side_effect=httpx.ReadTimeout("read timed out"))
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await provider.invoke(prompt="test")

        assert result.ok is False
        assert "timed out" in result.error.lower()

    @pytest.mark.asyncio
    async def test_invoke_with_prompt_kwarg(self):
        """invoke() should accept prompt= and wrap it as messages."""
        provider = _provider()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _chat_response("from prompt")
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await provider.invoke(prompt="tell me a joke")

        assert result.ok is True
        assert result.text == "from prompt"


# ---------------------------------------------------------------------------
# stream
# ---------------------------------------------------------------------------


class TestStream:
    @pytest.mark.asyncio
    async def test_stream_yields_chunks(self):
        provider = _provider()

        lines = [
            'data: {"choices":[{"delta":{"content":"Hello"}}]}',
            'data: {"choices":[{"delta":{"content":" world"}}]}',
            "data: [DONE]",
        ]

        mock_resp = AsyncMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.aiter_lines = lambda: _async_iter(lines)
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_client = AsyncMock()
        mock_client.stream = MagicMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            chunks = []
            async for chunk in provider.stream(messages=[{"role": "user", "content": "hi"}]):
                chunks.append(chunk)

        assert len(chunks) == 2
        assert chunks[0]["text"] == "Hello"
        assert chunks[1]["text"] == " world"

    @pytest.mark.asyncio
    async def test_stream_skips_malformed_json(self):
        provider = _provider()

        lines = [
            "data: NOT_JSON",
            'data: {"choices":[{"delta":{"content":"ok"}}]}',
            "data: [DONE]",
        ]

        mock_resp = AsyncMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.aiter_lines = lambda: _async_iter(lines)
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_client = AsyncMock()
        mock_client.stream = MagicMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            chunks = []
            async for chunk in provider.stream(prompt="hi"):
                chunks.append(chunk)

        assert len(chunks) == 1
        assert chunks[0]["text"] == "ok"


# ---------------------------------------------------------------------------
# health_check
# ---------------------------------------------------------------------------


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_healthy_endpoint(self):
        provider = _provider()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "ok"}

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            health = await provider.health_check()

        assert isinstance(health, ProviderHealth)
        assert health.healthy is True
        assert health.latency_ms > 0

    @pytest.mark.asyncio
    async def test_unhealthy_status_code(self):
        provider = _provider()
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        mock_resp.json.return_value = {"status": "error"}

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            health = await provider.health_check()

        assert health.healthy is False
        assert "503" in health.error

    @pytest.mark.asyncio
    async def test_health_check_no_endpoint(self):
        provider = _provider(endpoint="")
        provider._base_url = ""
        health = await provider.health_check()
        assert health.healthy is False
        assert "No endpoint" in health.error

    @pytest.mark.asyncio
    async def test_health_check_connection_error(self):
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
# _resolve_model
# ---------------------------------------------------------------------------


class TestResolveModel:
    @pytest.mark.asyncio
    async def test_uses_default_model_when_set(self):
        provider = _provider()
        model = await provider._resolve_model()
        assert model == "qwen2.5-3b"

    @pytest.mark.asyncio
    async def test_falls_back_to_api_model_list(self):
        provider = LlamaCPPProvider(
            "llamacpp_gcp",
            {
                "endpoint": "http://llama.test:8000",
                "endpoint_env": "LLAMACPP_GCP_ENDPOINT",
            },
        )
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": [{"id": "remote-model"}]}

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            model = await provider._resolve_model()

        assert model == "remote-model"

    @pytest.mark.asyncio
    async def test_falls_back_to_default_string(self):
        provider = LlamaCPPProvider(
            "llamacpp_gcp",
            {
                "endpoint": "http://llama.test:8000",
                "endpoint_env": "LLAMACPP_GCP_ENDPOINT",
            },
        )

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.get = AsyncMock(side_effect=Exception("fail"))
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            model = await provider._resolve_model()

        assert model == "default"


class TestAuthHeaders:
    def test_no_auth_header_without_key(self, monkeypatch):
        monkeypatch.delenv("LLAMACPP_TEST_KEY", raising=False)
        provider = LlamaCPPProvider(
            "llamacpp",
            {"endpoint": "http://llama.test:8081", "api_key_env": "LLAMACPP_TEST_KEY"},
        )
        assert "Authorization" not in provider._headers()

    @pytest.mark.asyncio
    async def test_bearer_key_sent_on_invoke(self, monkeypatch):
        monkeypatch.setenv("LLAMACPP_TEST_KEY", "sekret")
        provider = LlamaCPPProvider(
            "llamacpp",
            {
                "endpoint": "http://llama.test:8081",
                "api_key_env": "LLAMACPP_TEST_KEY",
                "default_model": "goblin-core",
            },
        )
        mock_resp = MagicMock()
        mock_resp.json.return_value = _chat_response("hi", model="goblin-core")
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await provider.invoke(prompt="hello")

        assert result.ok is True
        sent_headers = instance.post.call_args.kwargs["headers"]
        assert sent_headers["Authorization"] == "Bearer sekret"


class TestAvailability:
    def test_unavailable_without_endpoint(self, monkeypatch):
        monkeypatch.delenv("LLAMACPP_TEST_ENDPOINT", raising=False)
        provider = LlamaCPPProvider("llamacpp", {"endpoint_env": "LLAMACPP_TEST_ENDPOINT"})
        assert provider.is_available() is False

    def test_available_with_endpoint_env(self, monkeypatch):
        monkeypatch.setenv("LLAMACPP_TEST_ENDPOINT", "http://100.64.0.1:8081")
        provider = LlamaCPPProvider("llamacpp", {"endpoint_env": "LLAMACPP_TEST_ENDPOINT"})
        assert provider.is_available() is True


class TestProxy:
    def test_proxy_from_env(self, monkeypatch):
        monkeypatch.setenv("LLAMACPP_TEST_PROXY", "http://localhost:1055")
        provider = LlamaCPPProvider(
            "llamacpp",
            {"endpoint": "http://100.64.0.1:8081", "proxy_env": "LLAMACPP_TEST_PROXY"},
        )
        with patch("httpx.AsyncClient") as MockClient:
            provider._http_client(timeout=5)
        MockClient.assert_called_once_with(timeout=5, proxy="http://localhost:1055")

    def test_no_proxy_when_env_unset(self, monkeypatch):
        monkeypatch.delenv("LLAMACPP_TEST_PROXY", raising=False)
        provider = LlamaCPPProvider(
            "llamacpp",
            {"endpoint": "http://llama.test:8081", "proxy_env": "LLAMACPP_TEST_PROXY"},
        )
        assert provider._proxy is None


# ---------------------------------------------------------------------------
# Async iter helper for stream mocking
# ---------------------------------------------------------------------------


async def _async_iter(items):
    for item in items:
        yield item
