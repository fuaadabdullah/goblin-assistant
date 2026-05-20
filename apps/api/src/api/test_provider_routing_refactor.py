import asyncio
import pytest

from api.services.provider_health import HealthStatus, ProviderHealth
from api.services.smart_router import ProviderSelection, RoutingStrategy, SmartRouter


def test_provider_health_status_transitions():
    health = ProviderHealth(provider_id="openai")
    health.record_success(42.0)

    assert health.status == HealthStatus.HEALTHY
    assert health.consecutive_failures == 0
    assert health.last_error is None

    health.record_failure("Timeout")
    assert health.status == HealthStatus.DEGRADED


@pytest.mark.asyncio
async def test_smart_router_fallback_continues_after_runtime_error():
    router = SmartRouter(strategy=RoutingStrategy.COST_OPTIMIZED)

    def fake_select_provider(*_args, **_kwargs):
        return ProviderSelection(
            provider_id="openai",
            model="gpt-4o-mini",
            reason="test",
            fallback_chain=["groq"],
            estimated_cost=0.0,
            expected_latency_ms=0.0,
        )

    router.select_provider = fake_select_provider  # type: ignore[assignment]

    async def fake_invoke(provider_id, _model, _payload, _timeout_ms):
        await asyncio.sleep(0)
        if provider_id == "openai":
            raise RuntimeError("provider failure")
        return {"ok": True, "usage": {"prompt_tokens": 10, "completion_tokens": 10}}

    result = await router.invoke_with_fallback(fake_invoke, [{"role": "user", "content": "hi"}])

    assert result["ok"] is True
    assert result["routing"]["provider"] == "groq"
    assert result["routing"]["tried_providers"] == ["openai", "groq"]
