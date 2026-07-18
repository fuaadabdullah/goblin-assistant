"""Circuit Breakers tests for ProviderDispatcher routing."""

import time

from api.ops.circuit_breaker import CircuitBreaker

from .conftest import _clean_env, _make_dispatcher, _StubProvider


class TestBaseProviderCircuitBreaker:
    """Tests for the built-in circuit breaker on ``BaseProvider``."""

    def test_circuit_breaker_soft_opens_after_two_transient_failures(self):
        provider = _StubProvider("stub", {"default_model": "stub-model"})
        assert provider.is_available() is True

        provider.record_failure("timeout one", category="timeout")
        assert provider.circuit_state == "closed"

        provider.record_failure("timeout two", category="timeout")
        assert provider.circuit_state == "soft_open"
        assert provider.is_available() is True
        assert provider.should_attempt(canary=False) is False
        assert provider.should_attempt(canary=True) is False

    def test_circuit_breaker_backoff_duration(self):
        provider = _StubProvider("stub", {"default_model": "stub-model"})
        provider.record_failure("server error 1", backoff_seconds=30.0, category="server-error")
        provider.record_failure("server error 2", backoff_seconds=30.0, category="server-error")
        assert provider.circuit_state == "soft_open"
        # _circuit_open_until should be ~now + 30s
        assert provider._circuit_open_until > time.time() + 25

    def test_circuit_breaker_failed_probe_rearms_soft_open_window(self, monkeypatch):
        import api.providers.base as base_module

        now = 1_000.0
        monkeypatch.setattr(base_module.time, "time", lambda: now)

        provider = _StubProvider("stub", {"default_model": "stub-model"})
        provider.record_failure("timeout 1", category="timeout")
        provider.record_failure("timeout 2", category="timeout")
        assert provider.circuit_state == "soft_open"

        monkeypatch.setattr(base_module.time, "time", lambda: now + 31.0)
        assert provider.claim_soft_open_probe() is True

        provider.record_failure("timeout probe failed", category="timeout")
        assert provider.circuit_state == "soft_open"
        assert provider.soft_open_probe_available() is False
        assert provider._circuit_open_until > now + 31.0

    def test_circuit_breaker_success_resets_backoff(self):
        provider = _StubProvider("stub", {"default_model": "stub-model"})
        provider.record_failure("timeout 1", category="timeout")
        provider.record_failure("timeout 2", category="timeout")
        assert provider.circuit_state == "soft_open"

        provider.record_success()
        assert provider.is_available() is True
        assert provider.circuit_state == "closed"
        assert provider._failure_count == 0
        assert provider._circuit_open_until == 0.0

    def test_circuit_breaker_two_failures_still_available(self):
        provider = _StubProvider("stub", {"default_model": "stub-model"})
        provider.record_failure("f1")
        provider.record_failure("f2")
        assert provider.is_available() is True

    def test_circuit_breaker_record_failure_increments_count(self):
        provider = _StubProvider("stub", {"default_model": "stub-model"})
        assert provider._failure_count == 0
        provider.record_failure("err")
        assert provider._failure_count == 1
        provider.record_failure("err")
        assert provider._failure_count == 2

    def test_circuit_breaker_hard_opens_on_auth_failure(self):
        provider = _StubProvider("stub", {"default_model": "stub-model"})

        provider.record_failure("invalid api key", category="auth")

        assert provider.circuit_state == "hard_open"
        assert provider.is_available() is False
        assert provider.should_attempt(canary=True) is False

    def test_circuit_breaker_hard_opens_on_billing_failure(self):
        provider = _StubProvider("stub", {"default_model": "stub-model"})

        provider.record_failure("credit balance is too low", category="rate-limit")

        assert provider.circuit_state == "hard_open"
        assert provider.is_available() is False
        assert provider.should_attempt(canary=True) is False

    def test_dispatcher_probe_eligibility_uses_recovery_window(self, monkeypatch):
        import api.providers.base as base_module

        providers = {"alpha": {"default_model": "m1"}}
        d = _make_dispatcher(providers)
        try:
            provider = d.get_provider("alpha")

            now = 1_000.0
            monkeypatch.setattr(base_module.time, "time", lambda: now)
            provider.record_failure("timeout one", category="timeout")
            provider.record_failure("timeout two", category="timeout")

            assert d._is_canary_attempt("alpha", "m1") is False

            monkeypatch.setattr(base_module.time, "time", lambda: now + 31.0)
            assert d._is_canary_attempt("alpha", "m1") is True
        finally:
            _clean_env(providers)


class TestOpsCircuitBreaker:
    """Tests for the ops-domain ``CircuitBreaker``."""

    def test_closed_allows_execution(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
        assert cb.can_execute() is True
        assert cb.state == "CLOSED"

    def test_opens_after_threshold_failures(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "OPEN"
        assert cb.can_execute() is False

    def test_open_blocks_execution(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=60)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "OPEN"
        assert cb.can_execute() is False

    def test_recovery_timeout_transitions_to_half_open(self, monkeypatch):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.01)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "OPEN"
        assert cb.can_execute() is False

        # Advance time past recovery timeout
        monkeypatch.setattr(time, "time", lambda: cb.last_failure_time + 0.02)
        assert cb.can_execute() is True
        assert cb.state == "HALF_OPEN"

    def test_half_open_success_closes_circuit(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.01)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "OPEN"

        # Force into half-open by faking time
        cb.state = "HALF_OPEN"
        cb.can_execute()  # should return True for half-open

        cb.record_success()
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0

    def test_half_open_failure_reopens(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.01)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "OPEN"

        # Force into half-open
        cb.state = "HALF_OPEN"
        cb.record_failure()
        assert cb.state == "OPEN"

    def test_success_resets_from_any_state(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "OPEN"

        cb.record_success()
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0

    def test_get_status_fields(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
        status = cb.get_status()
        assert "state" in status
        assert "failure_count" in status
        assert "failure_threshold" in status
        assert "last_failure_time" in status
        assert "time_until_recovery" in status
        assert status["state"] == "CLOSED"

    def test_get_status_shows_time_until_recovery_when_open(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=30)
        cb.record_failure()
        status = cb.get_status()
        assert status["state"] == "OPEN"
        assert status["time_until_recovery"] > 0

    def test_initial_state_is_closed(self):
        cb = CircuitBreaker()
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0

    def test_failure_updates_last_failure_time(self):
        cb = CircuitBreaker()
        before = cb.last_failure_time
        cb.record_failure()
        assert cb.last_failure_time >= before
