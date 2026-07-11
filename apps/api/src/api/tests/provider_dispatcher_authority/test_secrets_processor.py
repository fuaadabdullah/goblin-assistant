"""Tests for provider secrets processor and error redaction."""

import pytest

from api.providers.dispatcher import ProviderDispatcher
from api.providers.dispatcher_pkg.sanitization import provider_secrets_processor


@pytest.mark.asyncio
async def test_dispatcher_redacts_secrets_in_errors(monkeypatch):
    secret = "sk-secret-value-123456"
    monkeypatch.setenv("OPENAI_API_KEY", secret)

    dispatcher = ProviderDispatcher()
    openai = dispatcher.get_provider("openai")

    async def boom(messages=None, model=None, **kwargs):
        _ = messages, model, kwargs
        raise RuntimeError(f"provider failed with key={secret}")

    monkeypatch.setattr(openai, "invoke", boom)

    result = await dispatcher.dispatch(
        pid="openai",
        model="gpt-4o-mini",
        payload={"messages": [{"role": "user", "content": "hi"}]},
    )

    assert result["ok"] is False
    assert "[REDACTED]" in result["error"]
    assert secret not in result["error"]


def test_provider_secrets_processor_redacts_nested_sensitive_fields():
    processor = provider_secrets_processor(lambda: ["sk-live-secret-12345678"])

    event = processor(
        None,
        "warning",
        {
            "event": "provider_failure",
            "provider": "openai",
            "headers": {"Authorization": "Bearer sk-live-secret-12345678"},
            "error": "failed with sk-live-secret-12345678",
        },
    )

    assert event["provider"] == "openai"
    assert event["headers"]["Authorization"] == "[REDACTED]"
    assert event["error"] == "failed with [REDACTED]"
