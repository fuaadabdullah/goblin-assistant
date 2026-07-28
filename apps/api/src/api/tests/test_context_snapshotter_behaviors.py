from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from api.observability.context_snapshotter import ContextSnapshotter
from api.observability.context_snapshotter_redaction import (
    calculate_context_hash,
    redact_context_layers,
)


def _layers(text: str):
    return [{"name": "system", "content": text, "tokens": 10}]


def test_redact_context_layers_masks_email_and_ip():
    redacted_layers, details = redact_context_layers(
        _layers("email me at user@example.com from 127.0.0.1"),
        [],
    )

    assert "[REDACTED_EMAIL]" in redacted_layers[0]["content"]
    assert "XXX.XXX.XXX.XXX" in redacted_layers[0]["content"]
    assert details["items_redacted"] >= 2


def test_calculate_context_hash_is_stable():
    assert calculate_context_hash("same content") == calculate_context_hash("same content")


@pytest.mark.asyncio
async def test_capture_snapshot_caches_and_replays(monkeypatch):
    snapshotter = ContextSnapshotter()
    monkeypatch.setattr(snapshotter, "_log_snapshot_structured", lambda snapshot: None)
    monkeypatch.setattr(snapshotter, "_log_to_file", lambda snapshot: None)
    snapshotter.config["observability"]["log_snapshots_to_file"] = False

    snapshot = await snapshotter.capture_context_snapshot(
        request_id="req-1",
        user_id="user-1",
        context_layers=_layers("hello"),
        total_tokens=20,
        remaining_tokens=80,
        token_budget=100,
        model_target="model-a",
        assembly_time_ms=3.2,
    )

    assert snapshotter._snapshot_cache["req-1"] is snapshot
    replay = await snapshotter.replay_context("req-1")
    assert replay is not None
    assert replay["request_id"] == "req-1"


@pytest.mark.asyncio
async def test_history_stats_and_search_use_snapshot_cache(monkeypatch):
    snapshotter = ContextSnapshotter()
    monkeypatch.setattr(snapshotter, "_log_snapshot_structured", lambda snapshot: None)
    monkeypatch.setattr(snapshotter, "_log_to_file", lambda snapshot: None)
    snapshotter.config["observability"]["log_snapshots_to_file"] = False

    snapshot = await snapshotter.capture_context_snapshot(
        request_id="req-2",
        user_id="user-2",
        context_layers=_layers("needle content"),
        total_tokens=30,
        remaining_tokens=70,
        token_budget=100,
        model_target="model-b",
        assembly_time_ms=5.0,
    )
    snapshot.timestamp = datetime.utcnow() - timedelta(minutes=10)

    history = await snapshotter.get_context_history(user_id="user-2", limit=5)
    assert len(history) == 1

    stats = await snapshotter.get_context_assembly_stats(user_id="user-2", time_window_hours=1)
    assert stats["total_assemblies"] == 1

    health = await snapshotter.get_context_health_report(user_id="user-2")
    assert health["health_status"] in {"healthy", "warning", "critical"}

    results = await snapshotter.search_snapshots(query="needle", user_id="user-2")
    assert len(results) == 1
