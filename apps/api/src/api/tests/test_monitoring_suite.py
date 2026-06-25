"""Test suite for monitoring.py"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from api.monitoring import (
    HEALTH_CHECK_INTERVAL,
    PROVIDER_HEALTH_KEY,
    ProviderMonitor,
)


@pytest.fixture
async def provider_monitor():
    """Create a ProviderMonitor instance for testing"""
    monitor = ProviderMonitor()
    yield monitor
    # Cleanup
    if monitor._running:
        await monitor.stop()


class TestProviderMonitor:
    """Tests for ProviderMonitor class"""

    @pytest.mark.asyncio
    async def test_provider_monitor_init(self, provider_monitor):
        """Test ProviderMonitor initialization"""
        assert provider_monitor._running is False
        assert provider_monitor._task is None
        assert provider_monitor._provider_status == {}

    @pytest.mark.asyncio
    async def test_provider_monitor_start(self, provider_monitor):
        """Test starting the provider monitor"""
        with patch.object(provider_monitor, "_monitor_loop", new_callable=AsyncMock):
            await provider_monitor.start()

            assert provider_monitor._running is True
            assert provider_monitor._task is not None

            await provider_monitor.stop()

    @pytest.mark.asyncio
    async def test_provider_monitor_start_already_running(self, provider_monitor):
        """Test that starting twice doesn't create duplicate tasks"""
        with patch.object(provider_monitor, "_monitor_loop", new_callable=AsyncMock):
            await provider_monitor.start()
            first_task = provider_monitor._task

            # Try to start again
            await provider_monitor.start()
            second_task = provider_monitor._task

            # Should be the same task
            assert first_task is second_task

            await provider_monitor.stop()

    @pytest.mark.asyncio
    async def test_provider_monitor_stop(self, provider_monitor):
        """Test stopping the provider monitor"""
        with patch.object(provider_monitor, "_monitor_loop", new_callable=AsyncMock):
            await provider_monitor.start()
            assert provider_monitor._running is True

            await provider_monitor.stop()
            assert provider_monitor._running is False

    @pytest.mark.asyncio
    async def test_provider_monitor_stop_when_not_running(self, provider_monitor):
        """Test stopping when not running doesn't raise error"""
        # Should not raise an exception
        await provider_monitor.stop()
        assert provider_monitor._running is False

    @pytest.mark.asyncio
    async def test_provider_monitor_check_connectivity_success(self, provider_monitor):
        """Test successful provider connectivity check"""
        with patch("api.monitoring.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = await provider_monitor._check_connectivity("http://example.com")

            assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_provider_monitor_check_connectivity_failure(self, provider_monitor):
        """Test failed provider connectivity check"""
        with patch("api.monitoring.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.side_effect = Exception("Connection failed")
            mock_client_class.return_value = mock_client

            result = await provider_monitor._check_connectivity("http://example.com")

            assert result["ok"] is False
            assert "error" in result

    @pytest.mark.asyncio
    async def test_provider_monitor_check_providers(self, provider_monitor):
        """Test checking multiple providers"""
        mock_providers = [
            {
                "enabled": True,
                "name": "provider_a",
                "base_url": "http://example1.com",
            },
            {
                "enabled": True,
                "name": "provider_b",
                "base_url": "http://example2.com",
            },
            {
                "enabled": False,
                "name": "provider_disabled",
                "base_url": "http://example3.com",
            },
        ]

        with (
            patch(
                "api.monitoring.get_provider_settings",
                return_value=mock_providers,
            ),
            patch.object(
                provider_monitor,
                "_check_connectivity",
                new_callable=AsyncMock,
            ) as mock_check,
        ):
            mock_check.return_value = {"ok": True, "latency_ms": 100}

            with patch("api.monitoring.cache.set", new_callable=AsyncMock):
                await provider_monitor._check_providers()

            # Should only check enabled providers
            assert mock_check.call_count == 2

    @pytest.mark.asyncio
    async def test_provider_monitor_check_providers_updates_status(self, provider_monitor):
        """Test that provider status is updated after checks"""
        mock_providers = [
            {
                "enabled": True,
                "name": "test_provider",
                "base_url": "http://example.com",
            },
        ]

        with (
            patch(
                "api.monitoring.get_provider_settings",
                return_value=mock_providers,
            ),
            patch.object(
                provider_monitor,
                "_check_connectivity",
                new_callable=AsyncMock,
            ) as mock_check,
        ):
            mock_check.return_value = {"ok": True, "latency_ms": 50}

            with patch("api.monitoring.cache.set", new_callable=AsyncMock):
                await provider_monitor._check_providers()

            assert "test_provider" in provider_monitor._provider_status
            status = provider_monitor._provider_status["test_provider"]
            assert status["status"] == "healthy"
            assert status["latency_ms"] == 50

    @pytest.mark.asyncio
    async def test_provider_monitor_check_providers_unhealthy_status(self, provider_monitor):
        """Test unhealthy provider status"""
        mock_providers = [
            {
                "enabled": True,
                "name": "unhealthy_provider",
                "base_url": "http://example.com",
            },
        ]

        with (
            patch(
                "api.monitoring.get_provider_settings",
                return_value=mock_providers,
            ),
            patch.object(
                provider_monitor,
                "_check_connectivity",
                new_callable=AsyncMock,
            ) as mock_check,
        ):
            mock_check.return_value = {
                "ok": False,
                "error": "Connection timeout",
            }

            with patch("api.monitoring.cache.set", new_callable=AsyncMock):
                await provider_monitor._check_providers()

            status = provider_monitor._provider_status["unhealthy_provider"]
            assert status["status"] == "unhealthy"
            assert status["error"] == "Connection timeout"

    @pytest.mark.asyncio
    async def test_provider_monitor_caches_status(self, provider_monitor):
        """Test that provider status is cached"""
        mock_providers = [
            {
                "enabled": True,
                "name": "provider_a",
                "base_url": "http://example.com",
            },
        ]

        with (
            patch(
                "api.monitoring.get_provider_settings",
                return_value=mock_providers,
            ),
            patch.object(
                provider_monitor,
                "_check_connectivity",
                new_callable=AsyncMock,
            ) as mock_check,
        ):
            mock_check.return_value = {"ok": True, "latency_ms": 100}

            with patch("api.monitoring.cache.set", new_callable=AsyncMock) as mock_cache_set:
                await provider_monitor._check_providers()

                mock_cache_set.assert_called_once()
                call_args = mock_cache_set.call_args
                assert call_args[0][0] == PROVIDER_HEALTH_KEY
                assert call_args[1]["expire"] == HEALTH_CHECK_INTERVAL * 2

    @pytest.mark.asyncio
    async def test_provider_monitor_monitor_loop(self, provider_monitor):
        """Test monitor loop runs and checks providers"""
        provider_monitor._running = True

        iteration_count = 0

        async def mock_check_providers():
            nonlocal iteration_count
            iteration_count += 1
            if iteration_count >= 2:
                # Stop after 2 iterations
                provider_monitor._running = False

        with (
            patch.object(
                provider_monitor,
                "_check_providers",
                side_effect=mock_check_providers,
            ),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            await provider_monitor._monitor_loop()

        assert iteration_count >= 1

    @pytest.mark.asyncio
    async def test_provider_monitor_loop_exception_handling(self, provider_monitor):
        """Test monitor loop exception handling"""
        provider_monitor._running = True

        call_count = 0

        async def mock_check_with_error():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                provider_monitor._running = False
                raise ValueError("Test error")
            raise asyncio.CancelledError()

        with (
            patch.object(
                provider_monitor,
                "_check_providers",
                side_effect=mock_check_with_error,
            ),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            await provider_monitor._monitor_loop()

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_provider_monitor_multiple_start_stop_cycles(self, provider_monitor):
        """Test multiple start/stop cycles work correctly"""
        with patch.object(provider_monitor, "_monitor_loop", new_callable=AsyncMock):
            for _ in range(3):
                await provider_monitor.start()
                assert provider_monitor._running is True

                await provider_monitor.stop()
                assert provider_monitor._running is False
