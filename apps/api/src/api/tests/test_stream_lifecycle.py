"""Regression tests for completion, failure, cancellation, and stream accounting."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from api.providers.dispatcher_pkg import execution


@pytest.fixture
def stream_context(monkeypatch):
    provider = Mock(circuit_state="closed")
    provider.estimate_cost.return_value = 0.25
    dispatcher = SimpleNamespace(
        _apply_test_mode_delay=AsyncMock(),
        _maybe_inject_test_failure=AsyncMock(return_value=None),
        _sanitize_error=str,
        record_routing_outcome=Mock(),
        note_provider_result=Mock(),
    )
    monkeypatch.setattr(execution, "record_dispatch", Mock())
    return dispatcher, provider


async def wrap(context, source, **kwargs):
    dispatcher, provider = context
    provider.stream = source
    return await execution.stream_wrap(
        dispatcher, "stub", provider, [{"content": "hello"}], "model", logger=Mock(), **kwargs
    )


@pytest.mark.asyncio
async def test_success_requires_exhaustion_and_emits_estimated_usage(stream_context):
    async def source(*args, **kwargs):
        yield {"text": "hello"}
        yield {"text": " world"}

    dispatcher, provider = stream_context
    result = await wrap(stream_context, source)
    provider.record_success.assert_not_called()
    chunks = [chunk async for chunk in result.raw["stream_gen"]]
    provider.record_success.assert_called_once()
    assert chunks[-1]["usage"] == {"prompt_tokens": 2, "completion_tokens": 3}
    assert chunks[-1]["cost_usd"] == 0.25
    assert chunks[-1]["usage_estimated"] is True
    assert dispatcher.record_routing_outcome.call_args.kwargs["ok"] is True


@pytest.mark.asyncio
async def test_midstream_failure_records_failure_once_and_closes_source(stream_context):
    closed = []

    async def source(*args, **kwargs):
        try:
            yield {"text": "partial"}
            raise RuntimeError("upstream unavailable")
        finally:
            closed.append(True)

    dispatcher, provider = stream_context
    result = await wrap(stream_context, source)
    with pytest.raises(RuntimeError, match="upstream unavailable"):
        _ = [chunk async for chunk in result.raw["stream_gen"]]
    provider.record_success.assert_not_called()
    provider.record_failure.assert_called_once()
    assert dispatcher.record_routing_outcome.call_args.kwargs["ok"] is False
    assert closed == [True]


@pytest.mark.asyncio
async def test_startup_failure_is_left_to_attempt_owner(stream_context):
    async def source(*args, **kwargs):
        raise RuntimeError("429 rate limit")
        yield

    result = await wrap(stream_context, source)
    assert result.ok is False
    stream_context[1].record_failure.assert_not_called()


@pytest.mark.asyncio
async def test_stream_deadline_covers_later_chunks(stream_context):
    async def source(*args, **kwargs):
        yield {"text": "first"}
        await asyncio.Event().wait()

    result = await wrap(stream_context, source, _stream_timeout_ms=20)
    with pytest.raises(TimeoutError):
        _ = [chunk async for chunk in result.raw["stream_gen"]]
    stream_context[1].record_success.assert_not_called()
    stream_context[1].record_failure.assert_called_once()


@pytest.mark.asyncio
async def test_cancel_closes_provider_without_false_success(stream_context, monkeypatch):
    closed = []

    async def source(*args, **kwargs):
        try:
            yield {"text": "partial"}
            await asyncio.Event().wait()
        finally:
            closed.append(True)

    commit = AsyncMock()
    monkeypatch.setattr(execution.quota_service, "commit", commit)
    result = await wrap(stream_context, source)
    reservation = object()
    stream = execution._settle_stream_quota(
        result.raw["stream_gen"], reservation, [{"content": "hello"}], ""
    )
    await anext(stream)
    commit.assert_not_awaited()
    await stream.aclose()
    commit.assert_awaited_once_with(reservation, actual_input_tokens=2, actual_output_tokens=2)
    stream_context[1].record_success.assert_not_called()
    stream_context[1].record_failure.assert_not_called()
    assert closed == [True]


@pytest.mark.asyncio
async def test_coroutine_stream_factory_and_reported_usage(stream_context):
    async def source(*args, **kwargs):
        async def chunks():
            yield {"text": "hello"}
            yield {"usage": {"prompt_tokens": 12, "completion_tokens": 8}, "cost_usd": 0.04}

        return chunks()

    result = await wrap(stream_context, source)
    chunks = [chunk async for chunk in result.raw["stream_gen"]]
    assert chunks[-1]["usage"] == {"prompt_tokens": 12, "completion_tokens": 8}
    assert chunks[-1]["cost_usd"] == 0.04
    assert chunks[-1]["cost_estimated"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize("compatible", [False, True])
async def test_provider_preserves_usage_only_sse_chunks(monkeypatch, compatible):
    import inspect

    from api.providers.openai_compatible import OpenAICompatibleProvider
    from api.providers.openai_provider import OpenAIProvider

    async def lines():
        yield 'data: {"choices":[{"delta":{"content":"hello"}}]}'
        yield 'data: {"choices":[],"usage":{"prompt_tokens":9,"completion_tokens":3}}'
        yield "data: [DONE]"

    response = Mock(aiter_lines=lines)
    stream_context = AsyncMock()
    stream_context.__aenter__.return_value = response
    client = Mock(stream=Mock(return_value=stream_context))
    client_context = AsyncMock()
    client_context.__aenter__.return_value = client
    monkeypatch.setattr("httpx.AsyncClient", Mock(return_value=client_context))
    provider_class = OpenAICompatibleProvider if compatible else OpenAIProvider
    provider = provider_class(
        "stub", {"endpoint": "https://example.invalid", "default_model": "stub"}
    )
    generator = provider.stream([{"role": "user", "content": "hi"}], "stub")
    if inspect.isawaitable(generator):
        generator = await generator
    chunks = [chunk async for chunk in generator]
    assert chunks == [{"text": "hello"}, {"usage": {"prompt_tokens": 9, "completion_tokens": 3}}]
