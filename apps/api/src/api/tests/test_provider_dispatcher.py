"""
Tests for provider dispatcher and fallback logic
Tests provider selection, fallback, and circuit breaker mechanisms
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from api.providers.base import ProviderHealth


@pytest.fixture
def mock_providers():
    """Create mock providers for testing"""
    openai = AsyncMock()
    openai.provider_id = "openai"
    openai.health_check = AsyncMock(
        return_value=ProviderHealth(provider_id="openai", healthy=True, latency_ms=50)
    )
    openai.invoke = AsyncMock()

    anthropic = AsyncMock()
    anthropic.provider_id = "anthropic"
    anthropic.health_check = AsyncMock(
        return_value=ProviderHealth(provider_id="anthropic", healthy=True, latency_ms=75)
    )

    azure = AsyncMock()
    azure.provider_id = "azure"
    azure.health_check = AsyncMock(
        return_value=ProviderHealth(provider_id="azure", healthy=False, latency_ms=100)
    )

    return {"openai": openai, "anthropic": anthropic, "azure": azure}


@pytest.fixture
def providers_mock(mock_providers):
    return mock_providers


class TestProviderDispatcherSelection:
    """Tests for provider selection logic"""

    def test_dispatcher_exposes_huggingface_provider(self):
        from api.providers.dispatcher import ProviderDispatcher

        dispatcher = ProviderDispatcher()
        provider = dispatcher.get_provider("huggingface")

        assert provider.provider_id == "huggingface"

    @pytest.mark.asyncio
    async def test_select_healthiest_provider(self, mock_providers):
        """Test selecting healthiest available provider"""
        from api.providers.dispatcher import (
            select_provider,
        )

        providers = [
            mock_providers["openai"],
            mock_providers["anthropic"],
        ]

        selected = await select_provider(providers)

        # OpenAI has lower latency (50ms vs 75ms)
        assert selected.provider_id == "openai"

    @pytest.mark.asyncio
    async def test_skip_unhealthy_providers(self, providers_mock):
        """Test skips unhealthy providers"""
        from api.providers.dispatcher import (
            select_provider,
        )

        providers = [
            providers_mock["azure"],  # unhealthy
            providers_mock["openai"],
        ]

        selected = await select_provider(providers)

        # Should skip Azure and select OpenAI
        assert selected.provider_id == "openai"

    @pytest.mark.asyncio
    async def test_fallback_if_no_healthy_providers(self, providers_mock):
        """Test fallback behavior when all unhealthy"""
        from api.providers.dispatcher import (
            select_provider,
        )

        # All providers unhealthy
        for provider in providers_mock.values():
            provider.health_check.return_value = ProviderHealth(
                provider_id=provider.provider_id,
                healthy=False,
                latency_ms=1000,
            )

        providers = list(providers_mock.values())

        # Should still select one (preferably by latency)
        selected = await select_provider(providers)

        assert selected is not None

    @pytest.mark.asyncio
    async def test_prefer_configured_provider(self, providers_mock):
        """Test prefers user-configured provider"""
        from api.providers.dispatcher import (
            select_provider,
        )

        providers = list(providers_mock.values())

        selected = await select_provider(providers, preferred="anthropic")

        if providers_mock["anthropic"].health_check.return_value.healthy:
            assert selected.provider_id == "anthropic"


class TestCircuitBreaker:
    """Tests for circuit breaker pattern"""

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_on_failures(self):
        """Test circuit breaker opens after threshold"""
        from api.providers.dispatcher import CircuitBreaker

        breaker = CircuitBreaker(failure_threshold=3, timeout=60)

        # Simulate failures
        for _ in range(3):
            breaker.record_failure()

        assert breaker.is_open()

    @pytest.mark.asyncio
    async def test_circuit_breaker_allows_successes(self):
        """Test circuit breaker resets on success"""
        from api.providers.dispatcher import CircuitBreaker

        breaker = CircuitBreaker(failure_threshold=3, timeout=60)

        # Record successes
        for _ in range(3):
            breaker.record_success()

        assert not breaker.is_open()

    @pytest.mark.asyncio
    async def test_circuit_breaker_timeout(self):
        """Test circuit breaker timeout mechanism"""
        import asyncio

        from api.providers.dispatcher import CircuitBreaker

        breaker = CircuitBreaker(failure_threshold=1, timeout=1)

        breaker.record_failure()
        assert breaker.is_open()

        # Wait for timeout
        await asyncio.sleep(1.1)

        # Should allow retry
        assert not breaker.is_open()

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_state(self):
        """Test half-open state during recovery"""
        from api.providers.dispatcher import CircuitBreaker

        breaker = CircuitBreaker(failure_threshold=2, timeout=1)

        for _ in range(2):
            breaker.record_failure()

        assert breaker.is_open()
        assert breaker.state == "OPEN"


class TestProviderFallback:
    """Tests for provider fallback mechanism"""

    def test_mock_provider_fallback_is_disabled_in_production(self, monkeypatch):
        from api.providers.dispatcher_pkg.execution import mock_fallback_enabled

        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.delenv("ALLOW_MOCK_PROVIDER_FALLBACK", raising=False)

        assert mock_fallback_enabled() is False

    def test_mock_provider_fallback_can_be_explicitly_enabled(self, monkeypatch):
        from api.providers.dispatcher_pkg.execution import mock_fallback_enabled

        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("ALLOW_MOCK_PROVIDER_FALLBACK", "true")

        assert mock_fallback_enabled() is True

    @pytest.mark.asyncio
    async def test_fallback_on_primary_failure(self):
        """Test fallback when primary provider fails"""
        from api.providers.dispatcher import (
            invoke_with_fallback,
        )

        primary = AsyncMock()
        primary.provider_id = "primary"
        primary.invoke = AsyncMock(side_effect=Exception("Primary failed"))

        fallback = AsyncMock()
        fallback.provider_id = "fallback"
        fallback.invoke = AsyncMock(return_value={"response": "fallback"})

        result = await invoke_with_fallback(
            "prompt",
            providers=[primary, fallback],
        )

        # Should get fallback result
        assert result == {"response": "fallback"}
        fallback.invoke.assert_called()

    @pytest.mark.asyncio
    async def test_multiple_fallback_chain(self):
        """Test chaining multiple fallbacks"""
        from api.providers.dispatcher import (
            invoke_with_fallback,
        )

        p1 = AsyncMock()
        p1.provider_id = "p1"
        p1.invoke = AsyncMock(side_effect=Exception("p1 failed"))

        p2 = AsyncMock()
        p2.provider_id = "p2"
        p2.invoke = AsyncMock(side_effect=Exception("p2 failed"))

        p3 = AsyncMock()
        p3.provider_id = "p3"
        p3.invoke = AsyncMock(return_value={"response": "p3"})

        result = await invoke_with_fallback(
            "prompt",
            providers=[p1, p2, p3],
        )

        assert result == {"response": "p3"}

    @pytest.mark.asyncio
    async def test_all_providers_fail_raises_error(self):
        """Test error when all providers fail"""
        from api.providers.dispatcher import (
            invoke_with_fallback,
        )

        providers = []
        for i in range(3):
            p = AsyncMock()
            p.provider_id = f"p{i}"
            p.invoke = AsyncMock(side_effect=Exception(f"Failed {i}"))
            providers.append(p)

        with pytest.raises(Exception):
            await invoke_with_fallback("prompt", providers=providers)


class TestProviderLoadBalancing:
    """Tests for load balancing across providers"""

    @pytest.mark.asyncio
    async def test_round_robin_distribution(self, providers_mock):
        """Test round-robin request distribution"""
        from api.providers.dispatcher import (
            LoadBalancer,
        )

        lb = LoadBalancer(
            providers=list(providers_mock.values()),
            strategy="round_robin",
        )

        selected_providers = [lb.select() for _ in range(6)]

        # Should rotate through providers
        assert len(set(p.provider_id for p in selected_providers)) > 1

    @pytest.mark.asyncio
    async def test_weighted_distribution(self, providers_mock):
        """Test weighted distribution based on health"""
        from api.providers.dispatcher import (
            LoadBalancer,
        )

        lb = LoadBalancer(
            providers=list(providers_mock.values()),
            strategy="weighted",
        )

        selected_providers = [lb.select() for _ in range(100)]

        openai_count = sum(1 for p in selected_providers if p.provider_id == "openai")

        # Healthy providers should get more requests
        assert openai_count >= 30


class TestProviderMetrics:
    """Tests for provider metrics collection"""

    @pytest.mark.asyncio
    async def test_collect_latency_metrics(self, providers_mock):
        """Test collecting latency metrics"""
        from api.providers.dispatcher import MetricsCollector

        collector = MetricsCollector()

        for provider in providers_mock.values():
            collector.record_latency(
                provider.provider_id,
                100,
            )

        metrics = collector.get_metrics("openai")

        assert metrics is not None
        assert "p99_latency" in metrics or "avg_latency" in metrics

    @pytest.mark.asyncio
    async def test_collect_error_metrics(self):
        """Test collecting error metrics"""
        from api.providers.dispatcher import MetricsCollector

        collector = MetricsCollector()

        collector.record_error("openai", "timeout")
        collector.record_error("openai", "auth_error")
        collector.record_error("anthropic", "timeout")

        openai_errors = collector.get_error_counts("openai")

        assert "timeout" in openai_errors

    @pytest.mark.asyncio
    async def test_metrics_reporting(self):
        """Test metrics can be reported"""
        from api.providers.dispatcher import MetricsCollector

        collector = MetricsCollector()

        report = collector.generate_report()

        assert report is not None


class TestDispatchRequestFallback:
    """Tests for dispatch_request fallback behavior."""

    @pytest.mark.asyncio
    async def test_falls_back_to_mock_provider_when_no_candidates(self, monkeypatch):
        from api.providers.dispatcher import ProviderDispatcher
        from api.providers.dispatcher_pkg.execution import dispatch_request

        dispatcher = ProviderDispatcher()

        monkeypatch.setattr(dispatcher, "_candidate_order", lambda _provider_id: [])
        monkeypatch.setattr(dispatcher, "_resolve_model_alias", lambda pid, model: (pid, model))
        monkeypatch.setattr(dispatcher, "_build_invoke_kwargs", lambda payload: {})
        monkeypatch.setattr(dispatcher, "_is_warmup_routing_blocked", lambda _provider_id: False)
        monkeypatch.setattr(dispatcher, "_is_canary_attempt", lambda _provider_id, _model: False)
        monkeypatch.setattr(
            dispatcher,
            "_invoke_with_test_mode",
            lambda provider_id, provider, messages, model, **kwargs: provider.invoke(
                messages=messages,
                model=model,
                **kwargs,
            ),
        )
        monkeypatch.setattr(dispatcher, "note_provider_result", lambda *args, **kwargs: None)
        monkeypatch.setattr(dispatcher, "is_configured", lambda provider_id: provider_id == "mock")

        monkeypatch.setattr(
            "api.providers.dispatcher_pkg.execution.quota_service.reserve",
            AsyncMock(
                return_value=SimpleNamespace(
                    estimated_input_tokens=1,
                    estimated_output_tokens=1,
                )
            ),
        )
        monkeypatch.setattr(
            "api.providers.dispatcher_pkg.execution.quota_service.commit",
            AsyncMock(),
        )
        monkeypatch.setattr(
            "api.providers.dispatcher_pkg.execution.quota_service.release",
            AsyncMock(),
        )
        monkeypatch.setattr(
            "api.providers.dispatcher_pkg.execution.quota_service.mark_rate_limited",
            AsyncMock(),
        )
        monkeypatch.setattr(
            "api.providers.dispatcher_pkg.execution.insert_routing_audit",
            lambda *args, **kwargs: None,
        )

        result = await dispatch_request(
            dispatcher,
            pid=None,
            model=None,
            payload={"messages": [{"role": "user", "content": "hi"}]},
            logger=SimpleNamespace(
                bind=lambda **kwargs: SimpleNamespace(
                    info=lambda *args, **kwargs: None,
                    warning=lambda *args, **kwargs: None,
                ),
                warning=lambda *args, **kwargs: None,
            ),
        )

        assert result["ok"] is True
        assert result["provider"] == "mock"
        assert "Hello!" in result["result"]["text"]
