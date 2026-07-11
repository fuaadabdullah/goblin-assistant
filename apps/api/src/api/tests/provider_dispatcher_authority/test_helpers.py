"""Tests for standalone ProviderDispatcher helper functions."""

import pytest

from api.providers.base import ProviderHealth

dispatcher_module = __import__("api.providers.dispatcher", fromlist=["_"])


@pytest.mark.asyncio
async def test_select_provider_and_invoke_with_fallback_helpers():
    class _ProbeProvider:
        def __init__(
            self, provider_id: str, healthy: bool, latency_ms: float, result: str | None = None
        ):
            self.provider_id = provider_id
            self._healthy = healthy
            self._latency_ms = latency_ms
            self._result = result

        async def health_check(self):
            return ProviderHealth(
                provider_id=self.provider_id,
                healthy=self._healthy,
                latency_ms=self._latency_ms,
            )

        async def invoke(self, prompt):
            _ = prompt
            if self._result is None:
                raise RuntimeError(f"{self.provider_id} failed")
            return self._result

    preferred = _ProbeProvider("fast", True, 10.0, result="preferred")
    slower = _ProbeProvider("slow", True, 20.0, result="slow")
    unhealthy = _ProbeProvider("down", False, 5.0, result=None)

    assert (
        await dispatcher_module.select_provider([preferred, slower], preferred="fast") is preferred
    )
    assert await dispatcher_module.select_provider([preferred, slower]) is preferred
    assert await dispatcher_module.select_provider([unhealthy]) is unhealthy

    failing = _ProbeProvider("fail", True, 1.0, result=None)
    succeeding = _ProbeProvider("ok", True, 1.0, result="done")
    assert (
        await dispatcher_module.invoke_with_fallback("prompt", providers=[failing, succeeding])
        == "done"
    )

    with pytest.raises(RuntimeError, match="fail"):
        await dispatcher_module.invoke_with_fallback("prompt", providers=[failing])
