from __future__ import annotations

import asyncio
import time

import pytest

from api.providers.base import ProviderHealth
from api.providers.google_cloud_selfhosted_provider import GoogleCloudSelfhostedProvider


class _FastHealthyBackend:
    provider_id = "gcp_vm.llamacpp"

    async def health_check(self) -> ProviderHealth:
        await asyncio.sleep(0.01)
        return ProviderHealth(self.provider_id, True, latency_ms=10)


class _SlowBackend:
    provider_id = "gcp_vm.vertex"

    async def health_check(self) -> ProviderHealth:
        await asyncio.sleep(2)
        return ProviderHealth(self.provider_id, False, error="unreachable")


@pytest.mark.asyncio
async def test_health_check_returns_when_any_backend_is_healthy() -> None:
    provider = GoogleCloudSelfhostedProvider("gcp_vm", {"backends": []})
    provider._backends = [_FastHealthyBackend(), _SlowBackend()]

    started = time.perf_counter()
    health = await provider.health_check()
    elapsed = time.perf_counter() - started

    assert health.healthy is True
    assert elapsed < 0.5
