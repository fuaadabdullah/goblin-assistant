import json

import pytest

import api.stream_router as stream


def _parse_sse(event: str) -> dict:
    if event.startswith("data: "):
        return json.loads(event.removeprefix("data: "))
    return {}


@pytest.mark.asyncio
async def test_generate_stream_events_streaming(monkeypatch):
    async def fake_stream():
        yield {"text": "Hello "}
        yield {"text": "world"}

    async def fake_invoke_provider(**kwargs):
        if kwargs.get("stream"):
            return {"ok": True, "stream": fake_stream()}
        return {
            "ok": True,
            "result": {"text": "Hello world"},
            "provider": "test-provider",
            "model": "test-model",
        }

    monkeypatch.setattr("api.services.task_streaming.invoke_provider", fake_invoke_provider)

    events = []
    async for event in stream.generate_stream_events(
        task_id="task-stream",
        messages=[{"role": "user", "content": "hi"}],
        provider="p",
        model="m",
    ):
        events.append(event)

    parsed = [_parse_sse(event) for event in events]
    assert any(item.get("status") == "started" for item in parsed)
    assert any(item.get("content") == "Hello " for item in parsed)
    assert any(item.get("content") == "world" for item in parsed)
    assert any(item.get("done") is True for item in parsed)


@pytest.mark.asyncio
async def test_generate_stream_events_fallback(monkeypatch):
    calls = {"count": 0}

    async def fake_invoke_provider(**kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            return {"ok": False, "error": "stream-failed"}
        return {
            "ok": True,
            "result": {"text": "fallback text"},
            "provider": "fallback-provider",
            "model": "fallback-model",
        }

    monkeypatch.setattr("api.services.task_streaming.invoke_provider", fake_invoke_provider)

    events = []
    async for event in stream.generate_stream_events(
        task_id="task-fallback",
        messages=[{"role": "user", "content": "hi"}],
        provider="p",
        model="m",
    ):
        events.append(event)

    parsed = [_parse_sse(event) for event in events]
    assert any(item.get("content") == "fallback text" for item in parsed)
    assert any(item.get("done") is True for item in parsed)


@pytest.mark.asyncio
async def test_generate_stream_events_error(monkeypatch):
    async def fake_invoke_provider(**kwargs):
        return {"ok": False, "error": "bad-provider"}

    monkeypatch.setattr("api.services.task_streaming.invoke_provider", fake_invoke_provider)

    events = []
    async for event in stream.generate_stream_events(
        task_id="task-error",
        messages=[{"role": "user", "content": "hi"}],
        provider="p",
        model="m",
    ):
        events.append(event)

    parsed = [_parse_sse(event) for event in events]
    assert any(item.get("error") == "bad-provider" for item in parsed)
    assert parsed[-1].get("done") is True
