from __future__ import annotations

from pathlib import Path

from api.routing.router import RoutingRegistry, RoutingRegistryStore


def test_routing_registry_persists_stats_and_hourly_spend(tmp_path: Path):
    db_path = tmp_path / "routing-registry.db"
    store = RoutingRegistryStore(path=str(db_path))
    registry = RoutingRegistry(store=store)

    registry.record_success("openai", latency_ms=120.0, cost_usd=0.25)
    registry.record_failure("openai")
    registry.flush()

    reloaded = RoutingRegistry(store=RoutingRegistryStore(path=str(db_path)))

    stats = reloaded.get("openai")
    assert round(stats.ewma_latency_ms, 1) == 4024.0
    assert stats.success_count == 1
    assert stats.failure_count == 1
    assert round(stats.total_cost_usd, 2) == 0.25
    assert reloaded.current_hour_spend()["openai"] == 0.25


def test_routing_registry_periodic_flush_marks_dirty_until_flush(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "routing-registry.db"
    monkeypatch.setenv("ROUTING_REGISTRY_FLUSH_INTERVAL_SECONDS", "3600")
    registry = RoutingRegistry(store=RoutingRegistryStore(path=str(db_path)))

    registry.record_success("groq", latency_ms=50.0, cost_usd=0.0)

    assert registry.persistence_status()["dirty"] is True
    assert not db_path.exists()

    registry.close()

    assert registry.persistence_status()["dirty"] is False
    assert db_path.exists()


def test_routing_registry_persisted_snapshot_reads_from_store(tmp_path: Path):
    db_path = tmp_path / "routing-registry.db"
    registry = RoutingRegistry(store=RoutingRegistryStore(path=str(db_path)))
    registry.record_success("mock", latency_ms=5.0, cost_usd=0.0)
    registry.close()

    snapshot = registry.persisted_snapshot()

    assert "mock" in snapshot["stats"]
    assert snapshot["stats"]["mock"]["success_rate"] == 1.0
