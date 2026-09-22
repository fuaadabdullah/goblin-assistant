from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from ollama import ResponseError

from api.providers.ollama_provider import OllamaProvider


def _provider(client: MagicMock) -> OllamaProvider:
    with patch("api.providers.ollama_provider.AsyncClient", return_value=client):
        return OllamaProvider(
            "ollama_local",
            {
                "endpoint": "http://ollama.test:11434",
                "default_model": "llama3.1:8b",
            },
        )


@pytest.mark.asyncio
async def test_invoke_uses_native_chat_and_maps_usage() -> None:
    client = MagicMock()
    client.chat = AsyncMock(
        return_value={
            "message": {"content": "hello"},
            "prompt_eval_count": 3,
            "eval_count": 2,
        }
    )
    provider = _provider(client)

    result = await provider.invoke(
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=64,
        temperature=0.2,
    )

    assert result.ok is True
    assert result.text == "hello"
    assert result.usage == {
        "prompt_tokens": 3,
        "completion_tokens": 2,
        "total_tokens": 5,
    }
    client.chat.assert_awaited_once()
    kwargs = client.chat.await_args.kwargs
    assert kwargs["model"] == "llama3.1:8b"
    assert kwargs["stream"] is False
    assert kwargs["options"]["num_predict"] == 64
    assert kwargs["options"]["temperature"] == 0.2


@pytest.mark.asyncio
async def test_stream_uses_native_async_stream() -> None:
    async def chunks():
        yield {"message": {"content": "hel"}, "done": False}
        yield {"message": {"content": "lo"}, "done": True}

    client = MagicMock()
    client.chat = AsyncMock(return_value=chunks())
    provider = _provider(client)

    output = [
        item
        async for item in provider.stream(
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=32,
        )
    ]

    assert output == [{"text": "hel"}, {"text": "lo"}]
    assert client.chat.await_args.kwargs["stream"] is True


@pytest.mark.asyncio
async def test_health_check_uses_list() -> None:
    client = MagicMock()
    client.list = AsyncMock(return_value={"models": []})
    provider = _provider(client)

    health = await provider.health_check()

    assert health.healthy is True
    client.list.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_invoke_retries_server_errors() -> None:
    client = MagicMock()
    client.chat = AsyncMock(
        side_effect=[
            ResponseError("temporary failure", 503),
            {
                "message": {"content": "recovered"},
                "prompt_eval_count": 1,
                "eval_count": 1,
            },
        ]
    )
    provider = _provider(client)

    result = await provider.invoke(messages=[{"role": "user", "content": "hi"}])

    assert result.ok is True
    assert result.text == "recovered"
    assert client.chat.await_count == 2


@pytest.mark.asyncio
async def test_invoke_does_not_retry_auth_errors() -> None:
    client = MagicMock()
    client.chat = AsyncMock(side_effect=ResponseError("unauthorized", 401))
    provider = _provider(client)

    result = await provider.invoke(messages=[{"role": "user", "content": "hi"}])

    assert result.ok is False
    assert client.chat.await_count == 1
