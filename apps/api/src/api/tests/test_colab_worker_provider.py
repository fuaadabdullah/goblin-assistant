"""Tests for ColabWorkerProvider."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from api.providers.colab_worker_provider import ColabWorkerProvider


def _provider(**config_overrides) -> ColabWorkerProvider:
    config = {
        "endpoint": "https://colab.test",
        "endpoint_env": "TEST_COLAB_WORKER_ENDPOINT",
        "api_key_env": "TEST_COLAB_WORKER_API_KEY",
        "default_model": "gemma-3-12b",
    }
    config.update(config_overrides)
    return ColabWorkerProvider("colab_worker", config)


def _ok_openai_response(text: str = "hello") -> MagicMock:
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "choices": [{"message": {"content": text}}],
        "usage": {"prompt_tokens": 4, "completion_tokens": 2, "total_tokens": 6},
    }
    response.raise_for_status = MagicMock()
    return response


def _ok_custom_response(text: str = "hello") -> MagicMock:
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "response": text,
        "usage": {"prompt_tokens": 3, "completion_tokens": 1, "total_tokens": 4},
    }
    response.raise_for_status = MagicMock()
    return response


def _http_error_response(status_code: int = 404) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.text = '{"detail":"not found"}'
    response.raise_for_status.side_effect = httpx.HTTPStatusError(
        f"{status_code} Error",
        request=MagicMock(),
        response=response,
    )
    return response


@pytest.mark.asyncio
async def test_openai_compatible_success_path():
    provider = _provider()
    success = _ok_openai_response("from-openai-shape")

    with patch("api.providers.colab_worker_provider.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post = AsyncMock(return_value=success)
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await provider.invoke(
            messages=[{"role": "user", "content": "hello"}],
            model="gemma-3-12b",
        )

    assert result.ok is True
    assert result.text == "from-openai-shape"
    assert result.model == "gemma-3-12b"


@pytest.mark.asyncio
async def test_custom_chat_success_after_openai_unsupported_fallback():
    provider = _provider()
    openai_unsupported = _http_error_response(404)
    custom_success = _ok_custom_response("from-custom-chat")

    with patch("api.providers.colab_worker_provider.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post = AsyncMock(side_effect=[openai_unsupported, custom_success])
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await provider.invoke(
            messages=[{"role": "user", "content": "hello"}],
            model="qwen3-14b",
        )

    assert result.ok is True
    assert result.text == "from-custom-chat"
    assert result.model == "qwen3-14b"
    assert instance.post.await_count == 2


@pytest.mark.asyncio
async def test_invoke_sends_bearer_header():
    provider = _provider()
    success = _ok_openai_response("secured")

    with (
        patch.dict("os.environ", {"TEST_COLAB_WORKER_API_KEY": "top-secret"}, clear=False),
        patch("api.providers.colab_worker_provider.httpx.AsyncClient") as MockClient,
    ):
        instance = AsyncMock()
        instance.post = AsyncMock(return_value=success)
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        provider = _provider()
        result = await provider.invoke(prompt="hello")

    assert result.ok is True
    sent_headers = instance.post.await_args.kwargs["headers"]
    assert sent_headers["Authorization"] == "Bearer top-secret"


@pytest.mark.asyncio
async def test_health_probe_falls_back_to_models_endpoint():
    provider = _provider()
    health_bad = MagicMock(status_code=500)
    health_bad.raise_for_status = MagicMock()
    models_ok = MagicMock(status_code=200)
    models_ok.raise_for_status = MagicMock()

    with patch("api.providers.colab_worker_provider.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.get = AsyncMock(side_effect=[health_bad, models_ok])
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        health = await provider.health_check()

    assert health.healthy is True
    requested_urls = [call.args[0] for call in instance.get.await_args_list]
    assert requested_urls == [
        "https://colab.test/health",
        "https://colab.test/v1/models",
    ]


@pytest.mark.asyncio
async def test_health_probe_reports_unhealthy_when_both_fail():
    provider = _provider()

    with patch("api.providers.colab_worker_provider.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.get = AsyncMock(side_effect=httpx.ConnectError("connection refused"))
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        health = await provider.health_check()

    assert health.healthy is False
    assert "connection refused" in str(health.error).lower()
