"""Failure, cost and streaming semantics of the local-compute tier.

Complements test_node_registry.py. The contracts defended here:

* every eligible node is tried before falling back to the cloud;
* only genuine node faults feed the failure breaker;
* local work reports real token usage at $0.00;
* a stream is "served" only once the first token arrives, and a failure after
  that surfaces as an interruption rather than a silent cloud splice;
* the mTLS context is cached only after it was built successfully.
"""

from __future__ import annotations

import json
from dataclasses import replace

import httpx
import pytest

from api.nodes import client as node_client
from api.nodes.client import (
    NodeRequestRejectedError,
    NodeSaturatedError,
    NodeStreamInterruptedError,
    NodeUnavailableError,
    stream_node,
)
from api.nodes.config import node_settings
from api.nodes.dispatch import try_local_compute, try_local_compute_stream
from api.nodes.models import NodeHeartbeat
from api.nodes.registry import NodeRegistry


def heartbeat(node_id: str = "node-001", **overrides) -> NodeHeartbeat:
    payload = {
        "node_id": node_id,
        "status": "online",
        "backend": "ollama",
        "models": ["llama3.1:8b"],
        "active_jobs": 0,
        "max_concurrency": 1,
        "endpoint": "https://{}.tailnet:8090".format(node_id),
    }
    payload.update(overrides)
    return NodeHeartbeat(**payload)


@pytest.fixture
def registry() -> NodeRegistry:
    return NodeRegistry()


@pytest.fixture(autouse=True)
def local_tier_enabled(monkeypatch):
    monkeypatch.setattr(
        "api.nodes.dispatch.node_settings",
        replace(node_settings, enabled=True, streaming_enabled=True),
    )


def _inflight(registry: NodeRegistry, node_id: str) -> int:
    return len(registry._inflight.get(node_id, {}))


# --- non-streaming failure and cost semantics ------------------------------


@pytest.mark.asyncio
async def test_busy_first_node_falls_over_to_the_next_local_node(registry, monkeypatch):
    """Codex P2: a saturated first candidate must not send everything to cloud."""
    registry.upsert(heartbeat("node-001"))
    registry.upsert(heartbeat("node-002"))
    dialed: list[str] = []

    async def fake_invoke(**kwargs):
        dialed.append(kwargs["endpoint"])
        if "node-001" in kwargs["endpoint"]:
            raise NodeSaturatedError("node saturated (503)")
        return {"response": "from two", "eval_count": 3, "prompt_eval_count": 5}

    monkeypatch.setattr("api.nodes.dispatch.invoke_node", fake_invoke)

    result = await try_local_compute(
        "chat", {"prompt": "hi", "model": "llama3.1:8b"}, registry=registry
    )
    assert result is not None
    assert result["node_id"] == "node-002"
    assert len(dialed) == 2
    assert registry.get("node-001").consecutive_failures == 0
    assert _inflight(registry, "node-001") == 0
    assert _inflight(registry, "node-002") == 0


@pytest.mark.asyncio
async def test_all_nodes_failing_returns_none_and_records_each(registry, monkeypatch):
    registry.upsert(heartbeat("node-001"))
    registry.upsert(heartbeat("node-002"))

    async def dead(**kwargs):
        raise NodeUnavailableError("connection refused")

    monkeypatch.setattr("api.nodes.dispatch.invoke_node", dead)

    assert (
        await try_local_compute("chat", {"prompt": "hi", "model": "llama3.1:8b"}, registry=registry)
        is None
    )
    assert registry.get("node-001").consecutive_failures == 1
    assert registry.get("node-002").consecutive_failures == 1


@pytest.mark.asyncio
async def test_request_scoped_rejection_does_not_trip_the_breaker(registry, monkeypatch):
    registry.upsert(heartbeat())

    async def rejected(**kwargs):
        raise NodeRequestRejectedError("node rejected request (422)")

    monkeypatch.setattr("api.nodes.dispatch.invoke_node", rejected)

    assert (
        await try_local_compute("chat", {"prompt": "hi", "model": "llama3.1:8b"}, registry=registry)
        is None
    )
    assert registry.get("node-001").consecutive_failures == 0


@pytest.mark.asyncio
async def test_local_result_reports_usage_at_zero_cost(registry, monkeypatch):
    registry.upsert(heartbeat())

    async def ok(**kwargs):
        return {
            "response": "Interest on interest.",
            "eval_count": 4,
            "prompt_eval_count": 6,
            "tokens_per_second": 77.2,
        }

    monkeypatch.setattr("api.nodes.dispatch.invoke_node", ok)

    result = await try_local_compute(
        "chat", {"prompt": "hi", "model": "llama3.1:8b"}, registry=registry
    )
    assert result is not None
    assert result["cost_usd"] == 0.0
    assert result["usage"] == {"prompt_tokens": 6, "completion_tokens": 4, "total_tokens": 10}
    assert result["result"]["usage"] == result["usage"]
    assert result["result"]["cost_usd"] == 0.0


# --- streaming --------------------------------------------------------------


def _fake_stream(events, *, fail_after=None, before_first=None):
    """Build a stream_node stand-in yielding agent events."""

    async def fake(**kwargs):
        if before_first is not None:
            raise before_first
        for index, event in enumerate(events):
            if fail_after is not None and index == fail_after:
                raise NodeStreamInterruptedError("node stream error: gpu fell over")
            yield event

    return fake


@pytest.mark.asyncio
async def test_stream_is_served_locally_with_final_usage_chunk(registry, monkeypatch):
    registry.upsert(heartbeat())
    events = [
        {"type": "token", "text": "Interest "},
        {"type": "token", "text": "on interest."},
        {"type": "done", "eval_count": 2, "prompt_eval_count": 3, "tokens_per_second": 50.0},
    ]
    monkeypatch.setattr("api.nodes.dispatch.stream_node", _fake_stream(events))

    result = await try_local_compute_stream(
        "chat", {"prompt": "hi", "model": "llama3.1:8b"}, registry=registry
    )
    assert result is not None
    assert result["compute_tier"] == "local"
    assert result["cost_usd"] == 0.0
    assert _inflight(registry, "node-001") == 1, "reservation held while streaming"

    chunks = [chunk async for chunk in result["stream"]]
    assert "".join(c["text"] for c in chunks) == "Interest on interest."
    assert chunks[-1]["done"] is True
    assert chunks[-1]["usage"] == {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5}
    assert chunks[-1]["cost_usd"] == 0.0
    assert _inflight(registry, "node-001") == 0


@pytest.mark.asyncio
async def test_stream_failure_before_first_token_tries_next_node(registry, monkeypatch):
    registry.upsert(heartbeat("node-001"))
    registry.upsert(heartbeat("node-002"))

    def pick(**kwargs):
        if "node-001" in kwargs["endpoint"]:
            return _fake_stream([], before_first=NodeUnavailableError("refused"))(**kwargs)
        return _fake_stream([{"type": "token", "text": "ok"}, {"type": "done"}])(**kwargs)

    monkeypatch.setattr("api.nodes.dispatch.stream_node", pick)

    result = await try_local_compute_stream(
        "chat", {"prompt": "hi", "model": "llama3.1:8b"}, registry=registry
    )
    assert result is not None
    assert result["node_id"] == "node-002"
    assert registry.get("node-001").consecutive_failures == 1
    assert _inflight(registry, "node-001") == 0
    await result["stream"].aclose()
    assert _inflight(registry, "node-002") == 0


@pytest.mark.asyncio
async def test_old_agent_without_stream_endpoint_falls_back_cleanly(registry, monkeypatch):
    registry.upsert(heartbeat())
    monkeypatch.setattr(
        "api.nodes.dispatch.stream_node",
        _fake_stream([], before_first=NodeRequestRejectedError("node rejected request (404)")),
    )

    assert (
        await try_local_compute_stream(
            "chat", {"prompt": "hi", "model": "llama3.1:8b"}, registry=registry
        )
        is None
    )
    assert registry.get("node-001").consecutive_failures == 0
    assert _inflight(registry, "node-001") == 0


@pytest.mark.asyncio
async def test_mid_stream_failure_surfaces_and_is_recorded(registry, monkeypatch):
    registry.upsert(heartbeat())
    events = [{"type": "token", "text": "half an "}, {"type": "token", "text": "answer"}]
    monkeypatch.setattr("api.nodes.dispatch.stream_node", _fake_stream(events, fail_after=1))

    result = await try_local_compute_stream(
        "chat", {"prompt": "hi", "model": "llama3.1:8b"}, registry=registry
    )
    assert result is not None

    received = []
    with pytest.raises(NodeStreamInterruptedError):
        async for chunk in result["stream"]:
            received.append(chunk["text"])
    assert received == ["half an "]
    assert registry.get("node-001").consecutive_failures == 1
    assert _inflight(registry, "node-001") == 0


@pytest.mark.asyncio
async def test_abandoned_stream_releases_its_reservation(registry, monkeypatch):
    registry.upsert(heartbeat())
    events = [{"type": "token", "text": "a"}, {"type": "token", "text": "b"}, {"type": "done"}]
    monkeypatch.setattr("api.nodes.dispatch.stream_node", _fake_stream(events))

    result = await try_local_compute_stream(
        "chat", {"prompt": "hi", "model": "llama3.1:8b"}, registry=registry
    )
    stream = result["stream"]
    assert (await stream.__anext__())["text"] == "a"
    await stream.aclose()
    assert _inflight(registry, "node-001") == 0


@pytest.mark.asyncio
async def test_streaming_is_off_unless_enabled(registry, monkeypatch):
    monkeypatch.setattr(
        "api.nodes.dispatch.node_settings",
        replace(node_settings, enabled=True, streaming_enabled=False),
    )
    registry.upsert(heartbeat())
    assert (
        await try_local_compute_stream(
            "chat", {"prompt": "hi", "model": "llama3.1:8b"}, registry=registry
        )
        is None
    )


# --- client wire behaviour ---------------------------------------------------


@pytest.fixture
def transport(monkeypatch):
    """Route the node client's httpx calls through a MockTransport."""
    holder: dict = {}
    real_client = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs.pop("verify", None)
        return real_client(*args, transport=httpx.MockTransport(holder["handler"]), **kwargs)

    monkeypatch.setattr(node_client.httpx, "AsyncClient", factory)
    monkeypatch.setattr(node_client, "build_ssl_context", lambda: True)
    return holder


def _ndjson(*events) -> bytes:
    return b"".join(json.dumps(e).encode() + b"\n" for e in events)


async def _drain(**overrides):
    kwargs = {"endpoint": "https://node-001.tailnet:8090", "model": "m", "prompt": "p"}
    kwargs.update(overrides)
    return [event async for event in stream_node(**kwargs)]


@pytest.mark.asyncio
async def test_stream_node_parses_ndjson(transport):
    def handler(request):
        assert request.url.path == "/inference/stream"
        return httpx.Response(
            200,
            content=_ndjson(
                {"type": "token", "text": "hi"},
                {"type": "done", "eval_count": 1},
            ),
        )

    transport["handler"] = handler
    events = await _drain()
    assert [e["type"] for e in events] == ["token", "done"]


@pytest.mark.parametrize(
    "status,expected",
    [
        (503, NodeSaturatedError),
        (429, NodeSaturatedError),
        (404, NodeRequestRejectedError),
        (422, NodeRequestRejectedError),
        (502, NodeUnavailableError),
        (401, NodeUnavailableError),
    ],
)
@pytest.mark.asyncio
async def test_stream_node_classifies_http_errors(transport, status, expected):
    transport["handler"] = lambda request: httpx.Response(status, text="nope")
    with pytest.raises(expected) as info:
        await _drain()
    assert not isinstance(info.value, NodeStreamInterruptedError)
    if expected is NodeUnavailableError:
        assert not isinstance(info.value, (NodeSaturatedError, NodeRequestRejectedError))


@pytest.mark.asyncio
async def test_stream_error_event_after_token_is_an_interruption(transport):
    transport["handler"] = lambda request: httpx.Response(
        200,
        content=_ndjson({"type": "token", "text": "par"}, {"type": "error", "error": "oom"}),
    )
    with pytest.raises(NodeStreamInterruptedError):
        await _drain()


@pytest.mark.asyncio
async def test_stream_error_event_before_token_is_recoverable(transport):
    transport["handler"] = lambda request: httpx.Response(
        200, content=_ndjson({"type": "error", "error": "model not loaded"})
    )
    with pytest.raises(NodeUnavailableError) as info:
        await _drain()
    assert not isinstance(info.value, NodeStreamInterruptedError)


@pytest.mark.asyncio
async def test_stream_truncated_without_done_is_an_interruption(transport):
    transport["handler"] = lambda request: httpx.Response(
        200, content=_ndjson({"type": "token", "text": "cut"})
    )
    with pytest.raises(NodeStreamInterruptedError):
        await _drain()


@pytest.mark.asyncio
async def test_stream_malformed_line_is_rejected(transport):
    transport["handler"] = lambda request: httpx.Response(200, content=b"not json\n")
    with pytest.raises(NodeUnavailableError):
        await _drain()


@pytest.mark.asyncio
async def test_invoke_node_classifies_request_rejection(transport):
    transport["handler"] = lambda request: httpx.Response(422, text="bad options")
    with pytest.raises(NodeRequestRejectedError):
        await node_client.invoke_node(endpoint="https://n:1", model="m", prompt="p")


# --- TLS context caching ----------------------------------------------------


def test_tls_context_failure_is_not_cached(monkeypatch, tmp_path):
    """Codex P2: a broken cert must fail closed on every call, not just the first."""
    missing = str(tmp_path / "missing-ca.pem")
    monkeypatch.setattr(node_client, "node_settings", replace(node_settings, ca_certfile=missing))
    node_client.reset_ssl_context()
    try:
        for _ in range(2):
            with pytest.raises(OSError):
                node_client.build_ssl_context()
        assert node_client._ssl_context_built is False
    finally:
        node_client.reset_ssl_context()


@pytest.mark.asyncio
async def test_tls_failure_surfaces_as_node_unavailable(monkeypatch, tmp_path):
    missing = str(tmp_path / "missing-ca.pem")
    monkeypatch.setattr(node_client, "node_settings", replace(node_settings, ca_certfile=missing))
    node_client.reset_ssl_context()
    try:
        for _ in range(2):
            with pytest.raises(NodeUnavailableError):
                await node_client.invoke_node(endpoint="https://n:1", model="m", prompt="p")
    finally:
        node_client.reset_ssl_context()
