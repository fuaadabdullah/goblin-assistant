"""Focused tests for quiet provider health behavior."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest

import api.providers.aliyun_provider as aliyun_provider_module
import api.providers.vertex_provider as vertex_provider_module
from api.providers.aliyun_provider import AliyunProvider
from api.providers.vertex_provider import VertexAIProvider


class _FakeAliyunClient:
    requested_urls: list[str] = []
    requested_bodies: list[dict] = []

    def __init__(self, *args, **kwargs) -> None: ...

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args) -> None:
        return None

    async def get(self, url, **kwargs):
        self.requested_urls.append(url)
        return SimpleNamespace(status_code=200)

    async def post(self, url, **kwargs):
        self.requested_urls.append(url)
        self.requested_bodies.append(kwargs.get("json") or {})

        class _Response:
            status_code = 200

            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "choices": [{"message": {"content": "ok"}}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1},
                }

        return _Response()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("endpoint", "expected_url"),
    [
        (
            "https://dashscope-intl.aliyuncs.com/compatible-mode",
            "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/models",
        ),
        (
            "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
            "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/models",
        ),
    ],
)
async def test_aliyun_health_normalizes_compatible_endpoint(
    monkeypatch,
    endpoint,
    expected_url,
):
    _FakeAliyunClient.requested_urls = []
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setenv("DASHSCOPE_ENDPOINT", endpoint)
    monkeypatch.setattr(aliyun_provider_module.httpx, "AsyncClient", _FakeAliyunClient)

    provider = AliyunProvider("aliyun", {"api_key_env": "DASHSCOPE_API_KEY"})
    health = await provider.health_check()

    assert health.healthy is True
    assert _FakeAliyunClient.requested_urls == [expected_url]


@pytest.mark.asyncio
async def test_aliyun_health_timeout_returns_structured_error_without_warning(
    monkeypatch,
):
    class TimeoutClient(_FakeAliyunClient):
        async def get(self, url, **kwargs):
            raise httpx.TimeoutException("timed out")

    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setenv(
        "DASHSCOPE_ENDPOINT",
        "https://dashscope-intl.aliyuncs.com/compatible-mode",
    )
    monkeypatch.setattr(aliyun_provider_module.httpx, "AsyncClient", TimeoutClient)

    provider = AliyunProvider("aliyun", {"api_key_env": "DASHSCOPE_API_KEY"})
    with patch.object(aliyun_provider_module.logger, "warning") as warning:
        health = await provider.health_check()

    assert health.healthy is False
    assert health.error == "Timeout"
    warning.assert_not_called()


@pytest.mark.asyncio
async def test_aliyun_invoke_applies_prompt_budget(monkeypatch):
    _FakeAliyunClient.requested_bodies = []
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setenv("DASHSCOPE_ENDPOINT", "https://dashscope-intl.aliyuncs.com/compatible-mode")
    monkeypatch.setenv("DASHSCOPE_PROMPT_TOKEN_BUDGET", "8")
    monkeypatch.setattr(aliyun_provider_module.httpx, "AsyncClient", _FakeAliyunClient)

    provider = AliyunProvider("aliyun", {"api_key_env": "DASHSCOPE_API_KEY"})
    result = await provider.invoke(
        messages=[
            {"role": "system", "content": "Always be concise and helpful."},
            {"role": "user", "content": "one two three four five six seven eight nine ten"},
        ],
    )

    assert result.ok is True
    assert _FakeAliyunClient.requested_bodies
    assert len(_FakeAliyunClient.requested_bodies[-1]["messages"]) == 2
    assert _FakeAliyunClient.requested_bodies[-1]["messages"][0]["role"] == "system"
    assert _FakeAliyunClient.requested_bodies[-1]["messages"][1]["role"] == "user"
    assert "content truncated" in _FakeAliyunClient.requested_bodies[-1]["messages"][1]["content"]


@pytest.mark.asyncio
async def test_vertex_health_404_returns_structured_error_without_warning(monkeypatch):
    requested_urls: list[str] = []

    class VertexClient:
        def __init__(self, *args, **kwargs) -> None: ...

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args) -> None:
            return None

        async def get(self, url, **kwargs):
            requested_urls.append(url)
            return SimpleNamespace(status_code=404)

    monkeypatch.setattr(vertex_provider_module, "_get_access_token", lambda: "token")
    monkeypatch.setattr(vertex_provider_module.httpx, "AsyncClient", VertexClient)
    monkeypatch.delenv("VERTEX_AI_PROJECT", raising=False)
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
    monkeypatch.delenv("VERTEX_AI_LOCATION", raising=False)
    monkeypatch.delenv("GCP_REGION", raising=False)
    monkeypatch.delenv("VERTEX_AI_MODEL", raising=False)

    provider = VertexAIProvider(
        "vertex_ai",
        {
            "project": "test-project",
            "location": "us-central1",
            "default_model": "gemini-2.0-flash",
        },
    )
    with patch.object(vertex_provider_module.logger, "warning") as warning:
        health = await provider.health_check()

    assert health.healthy is False
    assert health.error == "HTTP 404"
    assert requested_urls == [
        "https://us-central1-aiplatform.googleapis.com/v1/projects/test-project"
        "/locations/us-central1/publishers/google/models/gemini-2.0-flash"
    ]
    warning.assert_not_called()


@pytest.mark.asyncio
async def test_vertex_invoke_enables_batch_and_context_cache(monkeypatch):
    captured = {}

    class VertexResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "candidates": [{"content": {"parts": [{"text": "ok"}]}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            }

    class VertexClient:
        def __init__(self, *args, **kwargs) -> None: ...

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args) -> None:
            return None

        async def post(self, url, headers=None, json=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["body"] = json
            return VertexResponse()

    monkeypatch.setenv("VERTEX_AI_PROJECT", "test-project")
    monkeypatch.setenv("VERTEX_AI_LOCATION", "us-central1")
    monkeypatch.setenv("VERTEX_AGENT_BATCH_MODE", "true")
    monkeypatch.setenv("VERTEX_CONTEXT_CACHING_ENABLED", "true")
    monkeypatch.setenv("VERTEX_CONTEXT_CACHE_NAME", "cached-prefix")
    monkeypatch.setattr(vertex_provider_module, "_get_access_token", lambda: "token")
    monkeypatch.setattr(vertex_provider_module.httpx, "AsyncClient", VertexClient)

    provider = VertexAIProvider(
        "vertex_ai",
        {
            "project": "test-project",
            "location": "us-central1",
            "default_model": "gemini-2.0-flash",
        },
    )
    result = await provider.invoke(messages=[{"role": "user", "content": "hello"}])

    assert result.ok is True
    assert captured["body"]["batchMode"] is True
    assert captured["body"]["cachedContent"] == "cached-prefix"
