"""Tests for BaseProvider circuit breaker behavior."""

import api.providers.base as base_module
from api.providers.base import ProviderResult

from .conftest import StubProvider


def test_provider_result_to_dict_uses_compat_shape():
    result = ProviderResult(
        ok=True,
        text="hello",
        raw={"id": "raw-1"},
        provider="openai",
        model="gpt-4o-mini",
        usage={"total_tokens": 42},
        cost_usd=0.123,
        latency_ms=12.5,
    )

    assert result.to_dict() == {
        "ok": True,
        "result": {
            "text": "hello",
            "raw": {"id": "raw-1"},
            "usage": {"total_tokens": 42},
            "cost_usd": 0.123,
        },
        "provider": "openai",
        "model": "gpt-4o-mini",
        "latency_ms": 12.5,
        "error": None,
    }


def test_base_provider_circuit_breaker_soft_opens_after_transient_failures():
    provider = StubProvider("stub", {"default_model": "stub-model"})

    provider.record_failure("timeout one", category="timeout")
    assert provider.circuit_state == "closed"

    provider.record_failure("timeout two", category="timeout")
    assert provider.circuit_state == "soft_open"
    assert provider.is_available() is True
    assert provider.should_attempt(canary=False) is False
    assert provider.should_attempt(canary=True) is False


def test_base_provider_soft_open_probe_becomes_available_after_timeout(monkeypatch):
    now = 1_000.0
    monkeypatch.setattr(base_module.time, "time", lambda: now)

    provider = StubProvider("stub", {"default_model": "stub-model"})
    provider.record_failure("timeout one", category="timeout")
    provider.record_failure("timeout two", category="timeout")

    assert provider.soft_open_probe_available() is False

    monkeypatch.setattr(base_module.time, "time", lambda: now + 31.0)
    assert provider.soft_open_probe_available() is True
    assert provider.claim_soft_open_probe() is True
    assert provider.claim_soft_open_probe() is False


def test_base_provider_circuit_status_includes_cooldown_remaining_seconds(monkeypatch):
    now = 1_000.0
    monkeypatch.setattr(base_module.time, "time", lambda: now)

    provider = StubProvider("stub", {"default_model": "stub-model"})
    provider.record_failure("timeout one", category="timeout")
    provider.record_failure("timeout two", category="timeout")

    status = provider.circuit_status()

    assert status["state"] == "soft_open"
    assert status["cooldown_remaining_seconds"] > 0


def test_base_provider_hard_opens_on_billing_failure():
    provider = StubProvider("stub", {"default_model": "stub-model"})

    provider.record_failure("exceeded your current quota", category="rate-limit")

    assert provider.circuit_state == "hard_open"
    assert provider.is_available() is False
    assert provider.should_attempt(canary=True) is False

    provider.record_success()
    assert provider.circuit_state == "closed"
    assert provider.is_available() is True
