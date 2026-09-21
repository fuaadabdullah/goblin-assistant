"""Node registry, eligibility, and local-compute fallback.

The behaviour under test is the promise the router makes to a user: local
compute when it is genuinely available, and the cloud ladder in every other
case, without the user ever seeing a failure.
"""

from __future__ import annotations

import pytest

from api.nodes.client import NodeUnavailableError
from api.nodes.config import node_settings
from api.nodes.dispatch import try_local_compute
from api.nodes.models import NodeHeartbeat
from api.nodes.registry import NodeRegistry

TTL = node_settings.heartbeat_ttl_seconds  # 90s by default


def make_heartbeat(**overrides) -> NodeHeartbeat:
    payload = {
        "node_id": "node-001",
        "node_type": "inference",
        "status": "online",
        "backend": "ollama",
        "gpu": "RTX 3060 12GB",
        "models": ["llama3.1:8b"],
        "active_jobs": 0,
        "max_concurrency": 1,
        "endpoint": "https://node-001.tailnet:8090",
    }
    payload.update(overrides)
    return NodeHeartbeat(**payload)


@pytest.fixture
def registry() -> NodeRegistry:
    return NodeRegistry()


@pytest.fixture(autouse=True)
def local_tier_enabled(monkeypatch):
    """The tier ships OFF, so dispatch tests must turn it on explicitly."""
    from dataclasses import replace

    monkeypatch.setattr("api.nodes.dispatch.node_settings", replace(node_settings, enabled=True))


# --- registration ---------------------------------------------------------


def test_first_heartbeat_registers_node(registry):
    record = registry.upsert(make_heartbeat(), now=1000.0)
    assert record.node_id == "node-001"
    assert record.heartbeat_count == 1
    assert record.first_seen == 1000.0
    assert registry.get("node-001") is not None


def test_registration_stores_the_full_contract(registry):
    record = registry.upsert(make_heartbeat(), now=1000.0)
    assert record.node_type == "inference"
    assert record.backend == "ollama"
    assert record.gpu == "RTX 3060 12GB"
    assert record.models == ["llama3.1:8b"]
    assert record.max_concurrency == 1
    assert record.endpoint == "https://node-001.tailnet:8090"
    assert record.last_heartbeat == 1000.0


# --- heartbeat refresh ----------------------------------------------------


def test_heartbeat_refresh_upserts_rather_than_duplicating(registry):
    registry.upsert(make_heartbeat(), now=1000.0)
    record = registry.upsert(make_heartbeat(active_jobs=1), now=1030.0)

    assert len(registry.all()) == 1, "upsert must key on node_id"
    assert record.heartbeat_count == 2
    assert record.last_heartbeat == 1030.0
    assert record.first_seen == 1000.0, "first_seen survives refreshes"
    assert record.active_jobs == 1, "refresh carries new capacity state"


def test_refresh_revives_a_node_that_had_expired(registry):
    registry.upsert(make_heartbeat(), now=1000.0)
    assert registry.eligible_nodes(model="llama3.1:8b", now=1000.0 + TTL + 1) == []

    registry.upsert(make_heartbeat(), now=2000.0)
    eligible = registry.eligible_nodes(model="llama3.1:8b", now=2000.0)
    assert [n.node_id for n in eligible] == ["node-001"]


# --- expiry ---------------------------------------------------------------


def test_node_is_online_within_ttl(registry):
    registry.upsert(make_heartbeat(), now=1000.0)
    record = registry.get("node-001")
    assert registry.effective_status(record, now=1000.0 + TTL - 1) == "online"


def test_stale_heartbeat_means_offline_regardless_of_last_claim(registry):
    """Silence is the only signal we get when a node is yanked from the wall."""
    registry.upsert(make_heartbeat(status="online"), now=1000.0)
    record = registry.get("node-001")

    assert registry.effective_status(record, now=1000.0 + TTL + 1) == "offline"
    assert registry.is_eligible(record, now=1000.0 + TTL + 1) is False


def test_expired_node_is_not_eligible(registry):
    registry.upsert(make_heartbeat(), now=1000.0)
    assert registry.eligible_nodes(now=1000.0 + TTL + 0.1) == []


# --- eligibility rules ----------------------------------------------------


def test_degraded_node_is_never_routed_to(registry):
    registry.upsert(make_heartbeat(status="degraded"), now=1000.0)
    assert registry.eligible_nodes(now=1000.0) == []


def test_offline_node_is_never_routed_to(registry):
    registry.upsert(make_heartbeat(status="offline"), now=1000.0)
    assert registry.eligible_nodes(now=1000.0) == []


def test_saturated_node_is_not_eligible(registry):
    registry.upsert(make_heartbeat(active_jobs=1, max_concurrency=1), now=1000.0)
    assert registry.eligible_nodes(now=1000.0) == []


def test_node_with_spare_capacity_is_eligible(registry):
    registry.upsert(make_heartbeat(active_jobs=1, max_concurrency=2), now=1000.0)
    assert [n.node_id for n in registry.eligible_nodes(now=1000.0)] == ["node-001"]


def test_unsupported_model_makes_node_ineligible(registry):
    registry.upsert(make_heartbeat(models=["llama3.1:8b"]), now=1000.0)
    assert registry.eligible_nodes(model="gpt-4o", now=1000.0) == []
    assert len(registry.eligible_nodes(model="llama3.1:8b", now=1000.0)) == 1


def test_repeated_dispatch_failures_shed_the_node(registry):
    """A broken node must stop being chosen before its heartbeat lapses."""
    registry.upsert(make_heartbeat(), now=1000.0)
    for _ in range(node_settings.max_consecutive_failures):
        registry.record_failure("node-001")
    assert registry.eligible_nodes(now=1000.0) == []

    # A fresh heartbeat is evidence of recovery.
    registry.upsert(make_heartbeat(), now=1001.0)
    assert len(registry.eligible_nodes(now=1001.0)) == 1


# --- local dispatch and cloud fallback ------------------------------------


@pytest.mark.asyncio
async def test_local_compute_serves_an_eligible_node(registry, monkeypatch):
    registry.upsert(make_heartbeat(), now=None)

    async def fake_invoke(**kwargs):
        assert kwargs["model"] == "llama3.1:8b"
        assert kwargs["prompt"] == "Explain compound interest."
        return {"response": "Interest on interest.", "eval_count": 4, "tokens_per_second": 77.2}

    monkeypatch.setattr("api.nodes.dispatch.invoke_node", fake_invoke)

    result = await try_local_compute(
        "chat",
        {"prompt": "Explain compound interest.", "model": "llama3.1:8b"},
        registry=registry,
    )
    assert result is not None
    assert result["ok"] is True
    assert result["text"] == "Interest on interest."
    assert result["result"]["text"] == "Interest on interest."
    assert result["compute_tier"] == "local"
    assert result["node_id"] == "node-001"


@pytest.mark.asyncio
async def test_no_registered_node_falls_through(registry):
    result = await try_local_compute("chat", {"prompt": "hi"}, registry=registry)
    assert result is None, "None is the signal to use the cloud ladder"


@pytest.mark.asyncio
async def test_unsupported_model_falls_through(registry):
    registry.upsert(make_heartbeat(models=["llama3.1:8b"]))
    result = await try_local_compute("chat", {"prompt": "hi", "model": "gpt-4o"}, registry=registry)
    assert result is None


@pytest.mark.asyncio
async def test_saturated_node_falls_through(registry):
    registry.upsert(make_heartbeat(active_jobs=1, max_concurrency=1))
    result = await try_local_compute(
        "chat", {"prompt": "hi", "model": "llama3.1:8b"}, registry=registry
    )
    assert result is None


@pytest.mark.asyncio
async def test_node_failure_falls_through_and_is_recorded(registry, monkeypatch):
    registry.upsert(make_heartbeat())

    async def boom(**kwargs):
        raise NodeUnavailableError("connection refused")

    monkeypatch.setattr("api.nodes.dispatch.invoke_node", boom)

    result = await try_local_compute(
        "chat", {"prompt": "hi", "model": "llama3.1:8b"}, registry=registry
    )
    assert result is None
    assert registry.get("node-001").consecutive_failures == 1


@pytest.mark.asyncio
async def test_node_timeout_falls_through(registry, monkeypatch):
    registry.upsert(make_heartbeat())

    async def timeout(**kwargs):
        raise NodeUnavailableError("node timed out after 60s")

    monkeypatch.setattr("api.nodes.dispatch.invoke_node", timeout)
    assert (
        await try_local_compute("chat", {"prompt": "hi", "model": "llama3.1:8b"}, registry=registry)
        is None
    )


@pytest.mark.asyncio
async def test_node_503_falls_through(registry, monkeypatch):
    """The agent's own concurrency gate refusing us is not an error."""
    registry.upsert(make_heartbeat())

    async def saturated(**kwargs):
        raise NodeUnavailableError("node saturated (503)")

    monkeypatch.setattr("api.nodes.dispatch.invoke_node", saturated)
    assert (
        await try_local_compute("chat", {"prompt": "hi", "model": "llama3.1:8b"}, registry=registry)
        is None
    )


@pytest.mark.asyncio
async def test_node_without_endpoint_falls_through(registry):
    registry.upsert(make_heartbeat(endpoint=None))
    assert (
        await try_local_compute("chat", {"prompt": "hi", "model": "llama3.1:8b"}, registry=registry)
        is None
    )


@pytest.mark.asyncio
async def test_non_chat_task_falls_through(registry):
    registry.upsert(make_heartbeat())
    assert (
        await try_local_compute(
            "embedding", {"prompt": "hi", "model": "llama3.1:8b"}, registry=registry
        )
        is None
    )


@pytest.mark.asyncio
async def test_messages_payload_is_flattened_to_a_prompt(registry, monkeypatch):
    registry.upsert(make_heartbeat())
    seen = {}

    async def capture(**kwargs):
        seen.update(kwargs)
        return {"response": "ok"}

    monkeypatch.setattr("api.nodes.dispatch.invoke_node", capture)
    await try_local_compute(
        "chat",
        {
            "messages": [{"role": "user", "content": "Explain compound interest."}],
            "model": "llama3.1:8b",
        },
        registry=registry,
    )
    assert seen["prompt"] == "Explain compound interest."


@pytest.mark.asyncio
async def test_disabled_flag_bypasses_local_entirely(registry, monkeypatch):
    from dataclasses import replace

    registry.upsert(make_heartbeat())
    monkeypatch.setattr("api.nodes.dispatch.node_settings", replace(node_settings, enabled=False))
    assert (
        await try_local_compute("chat", {"prompt": "hi", "model": "llama3.1:8b"}, registry=registry)
        is None
    )
