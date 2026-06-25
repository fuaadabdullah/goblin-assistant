import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

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


@pytest.mark.asyncio
async def test_generate_stream_events_marks_completed_when_stream_exhausts(monkeypatch):
    calls = {"statuses": []}

    class FakeStore:
        async def create_stream(self, stream_id, metadata):
            calls["created"] = (stream_id, metadata)

        async def append_chunk(self, stream_id, chunk):
            calls.setdefault("chunks", []).append((stream_id, chunk))

        async def mark_status(self, stream_id, *, status, done, updates=None):
            calls["statuses"].append((stream_id, status, done, updates))

    async def fake_iter_task_stream_chunks(**kwargs):
        del kwargs
        yield {"content": "partial", "done": False}

    monkeypatch.setattr(stream, "get_stream_state_store", FakeStore)
    monkeypatch.setattr(stream, "iter_task_stream_chunks", fake_iter_task_stream_chunks)

    events = []
    async for event in stream.generate_stream_events(
        task_id="task-exhausted",
        messages=[{"role": "user", "content": "hi"}],
        provider="p",
        model="m",
    ):
        events.append(event)

    parsed = [_parse_sse(event) for event in events]
    assert any(item.get("content") == "partial" for item in parsed)
    assert calls["statuses"] == [("task-exhausted", "completed", True, None)]


@pytest.mark.asyncio
async def test_generate_stream_events_emits_failure_event_on_iteration_error(monkeypatch):
    calls = {"statuses": [], "chunks": []}

    class FakeStore:
        async def create_stream(self, stream_id, metadata):
            calls["created"] = (stream_id, metadata)

        async def append_chunk(self, stream_id, chunk):
            calls["chunks"].append((stream_id, chunk))

        async def mark_status(self, stream_id, *, status, done, updates=None):
            calls["statuses"].append((stream_id, status, done, updates))

    async def fake_iter_task_stream_chunks(**kwargs):
        del kwargs
        raise RuntimeError("boom")
        yield  # pragma: no cover

    monkeypatch.setattr(stream, "get_stream_state_store", FakeStore)
    monkeypatch.setattr(stream, "iter_task_stream_chunks", fake_iter_task_stream_chunks)

    events = []
    async for event in stream.generate_stream_events(
        task_id="task-exception",
        messages=[{"role": "user", "content": "hi"}],
        provider="p",
        model="m",
    ):
        events.append(event)

    parsed = [_parse_sse(event) for event in events]
    assert parsed[-1]["error"] == "Streaming failed"
    assert calls["chunks"][-1] == (
        "task-exception",
        {"error": "Streaming failed", "done": True},
    )
    assert calls["statuses"][-1] == (
        "task-exception",
        "failed",
        True,
        {"error": "boom"},
    )


def test_stream_task_returns_sse_response_defaults(monkeypatch):
    async def fake_generate_stream_events(**kwargs):
        del kwargs
        yield "data: {}\n\n"

    monkeypatch.setattr(stream, "generate_stream_events", fake_generate_stream_events)

    app = FastAPI()
    app.include_router(stream.router, prefix="/api/v1")
    client = TestClient(app)

    response = client.post(
        "/api/v1/stream",
        json={"task_id": "task-1", "messages": [{"role": "user", "content": "hi"}]},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache"


@pytest.mark.asyncio
async def test_stream_task_raises_http_500_when_response_construction_fails(monkeypatch):
    def broken_streaming_response(*args, **kwargs):
        del args, kwargs
        raise RuntimeError("cannot-stream")

    monkeypatch.setattr(stream, "StreamingResponse", broken_streaming_response)

    with pytest.raises(Exception) as exc_info:
        await stream.stream_task(
            stream.StreamTaskRequest(
                task_id="task-2",
                messages=[{"role": "user", "content": "hi"}],
            )
        )

    error = exc_info.value
    assert getattr(error, "status_code", None) == 500
    assert getattr(error, "detail", None) == "Task streaming failed"
