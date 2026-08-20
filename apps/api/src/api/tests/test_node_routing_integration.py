"""route_task with the local-compute tier in front of the cloud ladder.

The contract these tests defend: adding local compute must not change what
happens when local compute is unavailable. Every fallback path has to land on
exactly the provider ladder that existed before.
"""

from __future__ import annotations

import pytest

from api.nodes.client import NodeUnavailable
from api.routing import selection


@pytest.fixture
def cloud(monkeypatch):
    """Stub the provider ladder and record whether it was used."""
    calls: list[str] = []

    class FakeDispatcher:
        def top_providers_for(self, capability, **kwargs):
            return ["groq", "gemini"]

        async def invoke_provider(self, provider_id, **kwargs):
            calls.append(provider_id)
            return {"ok": True, "text": "cloud answer", "provider": provider_id}

    monkeypatch.setattr(selection, "_dispatcher", lambda: FakeDispatcher())
    monkeypatch.setattr(selection, "top_providers_for", lambda **kwargs: ["groq", "gemini"])
    return calls


@pytest.mark.asyncio
async def test_local_node_serves_and_cloud_is_untouched(cloud, monkeypatch):
    async def local_hit(task_type, payload):
        return {"ok": True, "text": "local answer", "compute_tier": "local",
                "node_id": "node-001"}

    monkeypatch.setattr(selection, "_local_compute", lambda: local_hit)

    result = await selection.route_task("chat", {"prompt": "Explain compound interest."})
    assert result["text"] == "local answer"
    assert result["compute_tier"] == "local"
    assert cloud == [], "no cloud provider should have been called"


@pytest.mark.asyncio
async def test_no_local_node_falls_back_to_cloud(cloud, monkeypatch):
    async def local_miss(task_type, payload):
        return None

    monkeypatch.setattr(selection, "_local_compute", lambda: local_miss)

    result = await selection.route_task("chat", {"prompt": "hi"})
    assert result["ok"] is True
    assert result["text"] == "cloud answer"
    assert cloud == ["groq"], "the existing ladder must run unchanged"


@pytest.mark.asyncio
async def test_node_failure_falls_back_to_cloud(cloud, monkeypatch):
    """The headline acceptance test: pull the node, same prompt still answers."""

    async def local_dead(task_type, payload):
        return None  # dispatch swallowed NodeUnavailable and told us to move on

    monkeypatch.setattr(selection, "_local_compute", lambda: local_dead)

    result = await selection.route_task("chat", {"prompt": "Explain compound interest."})
    assert result["ok"] is True
    assert result["text"] == "cloud answer"
    assert cloud == ["groq"]


@pytest.mark.asyncio
async def test_local_tier_exception_never_breaks_routing(cloud, monkeypatch):
    """A bug in local compute must degrade to cloud, not 500 the request."""

    async def local_explodes(task_type, payload):
        raise RuntimeError("registry corrupted")

    monkeypatch.setattr(selection, "_local_compute", lambda: local_explodes)

    result = await selection.route_task("chat", {"prompt": "hi"})
    assert result["ok"] is True
    assert result["text"] == "cloud answer"
    assert cloud == ["groq"]


@pytest.mark.asyncio
async def test_streaming_requests_skip_local_entirely(cloud, monkeypatch):
    """The node agent forces stream:false, so streaming must not go local."""
    consulted = []

    async def local(task_type, payload):
        consulted.append(task_type)
        return {"ok": True, "text": "local answer"}

    monkeypatch.setattr(selection, "_local_compute", lambda: local)

    result = await selection.route_task("chat", {"prompt": "hi"}, stream=True)
    assert consulted == [], "local tier must not be consulted for streaming"
    assert result["text"] == "cloud answer"


@pytest.mark.asyncio
async def test_cloud_ladder_still_retries_next_provider(monkeypatch):
    """Provider-level fallback behaviour is preserved."""
    calls: list[str] = []

    class FlakyDispatcher:
        async def invoke_provider(self, provider_id, **kwargs):
            calls.append(provider_id)
            if provider_id == "groq":
                return {"ok": False, "error": "groq exploded"}
            return {"ok": True, "text": "gemini answer"}

    async def local_miss(task_type, payload):
        return None

    monkeypatch.setattr(selection, "_local_compute", lambda: local_miss)
    monkeypatch.setattr(selection, "_dispatcher", lambda: FlakyDispatcher())
    monkeypatch.setattr(selection, "top_providers_for", lambda **kwargs: ["groq", "gemini"])

    result = await selection.route_task("chat", {"prompt": "hi"})
    assert result["ok"] is True
    assert result["text"] == "gemini answer"
    assert calls == ["groq", "gemini"]


@pytest.mark.asyncio
async def test_total_failure_still_reports_providers_tried(monkeypatch):
    class DeadDispatcher:
        async def invoke_provider(self, provider_id, **kwargs):
            return {"ok": False, "error": "everything is down"}

    async def local_miss(task_type, payload):
        return None

    monkeypatch.setattr(selection, "_local_compute", lambda: local_miss)
    monkeypatch.setattr(selection, "_dispatcher", lambda: DeadDispatcher())
    monkeypatch.setattr(selection, "top_providers_for", lambda **kwargs: ["groq", "gemini"])

    result = await selection.route_task("chat", {"prompt": "hi"})
    assert result["ok"] is False
    assert result["providers_tried"] == ["groq", "gemini"]
