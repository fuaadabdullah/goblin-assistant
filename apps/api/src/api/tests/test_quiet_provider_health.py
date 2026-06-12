"""Focused tests for quiet provider health behavior."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest

from api.providers.aliyun_provider import AliyunProvider
from api.providers.vertex_provider import VertexAIProvider


class _FakeAliyunClient:
    requested_urls: list[str] = []

    def __init__(self, *args, **kwargs) -> None: ...

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args) -> None:
        return None

    async def get(self, url, **kwargs):
        self.requested_urls.append(url)
        return SimpleNamespace(status_code=200)


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
    monkeypatch.setattr(
        "api.providers.aliyun_provider.httpx.AsyncClient",
        _FakeAliyunClient,
    )

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
    monkeypatch.setattr(
        "api.providers.aliyun_provider.httpx.AsyncClient",
        TimeoutClient,
    )

    provider = AliyunProvider("aliyun", {"api_key_env": "DASHSCOPE_API_KEY"})
    with patch("api.providers.aliyun_provider.logger.warning") as warning:
        health = await provider.health_check()

    assert health.healthy is False
    assert health.error == "Timeout"
    warning.assert_not_called()


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

    monkeypatch.setattr(
        "api.providers.vertex_provider._get_access_token",
        lambda: "token",
    )
    monkeypatch.setattr("api.providers.vertex_provider.httpx.AsyncClient", VertexClient)
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
    with patch("api.providers.vertex_provider.logger.warning") as warning:
        health = await provider.health_check()

    assert health.healthy is False
    assert health.error == "HTTP 404"
    assert requested_urls == [
        "https://us-central1-aiplatform.googleapis.com/v1/projects/test-project"
        "/locations/us-central1/publishers/google/models/gemini-2.0-flash"
    ]
    warning.assert_not_called()
