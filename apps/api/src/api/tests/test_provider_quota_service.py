from __future__ import annotations

import pytest

import api.providers.quota_service as quota_module
from api.providers.pricing import RateLimitConfig
from api.providers.quota_service import ProviderQuotaService, QuotaReservation


@pytest.mark.asyncio
async def test_quota_service_shares_canonical_model_budget(monkeypatch):
    service = ProviderQuotaService()

    monkeypatch.setattr(
        quota_module,
        "resolve_rate_limit",
        lambda provider_id, model=None, config=None: RateLimitConfig(
            requests_per_minute=10,
            tokens_per_minute=1000,
            concurrency=2,
        ),
    )
    monkeypatch.setattr(
        quota_module,
        "resolve_model_budget",
        lambda model: RateLimitConfig(
            requests_per_minute=1,
            tokens_per_minute=100,
            concurrency=1,
        ),
    )
    monkeypatch.setattr(quota_module, "resolve_canonical_model", lambda model: "gpt-4o-mini")

    first = await service.reserve(
        "openai",
        "gpt-4o-mini",
        messages=[{"role": "user", "content": "hello there"}],
    )
    assert first is not None

    second = await service.reserve(
        "azure_openai",
        "gpt-4o-mini",
        messages=[{"role": "user", "content": "hello there"}],
    )
    assert second is None

    await service.release(first)

    third = await service.reserve(
        "azure_openai",
        "gpt-4o-mini",
        messages=[{"role": "user", "content": "hello there"}],
    )
    assert third is not None


@pytest.mark.asyncio
async def test_quota_service_cooldown_blocks_then_expires(monkeypatch):
    service = ProviderQuotaService()
    clock = {"now": 100.0}
    monkeypatch.setattr(quota_module.time, "time", lambda: clock["now"])
    monkeypatch.setattr(
        quota_module,
        "resolve_rate_limit",
        lambda provider_id, model=None, config=None: RateLimitConfig(
            requests_per_minute=10,
            tokens_per_minute=1000,
            concurrency=1,
        ),
    )
    monkeypatch.setattr(
        quota_module,
        "resolve_model_budget",
        lambda model: RateLimitConfig(
            requests_per_minute=10,
            tokens_per_minute=1000,
            concurrency=1,
        ),
    )
    monkeypatch.setattr(quota_module, "resolve_canonical_model", lambda model: model)

    await service.mark_rate_limited("openai", "gpt-4o-mini", cooldown_seconds=1)
    assert await service.can_attempt("openai", "gpt-4o-mini") is False
    assert await service.reserve("openai", "gpt-4o-mini", messages=[]) is None
    assert service.last_skip_reason == "cooldown"

    clock["now"] = 102.0
    assert await service.can_attempt("openai", "gpt-4o-mini") is True
    assert await service.reserve("openai", "gpt-4o-mini", messages=[]) is not None


@pytest.mark.asyncio
async def test_quota_service_records_model_capacity_skip_reason(monkeypatch):
    service = ProviderQuotaService()
    monkeypatch.setattr(
        quota_module,
        "resolve_rate_limit",
        lambda provider_id, model=None, config=None: RateLimitConfig(
            requests_per_minute=10,
            tokens_per_minute=1000,
            concurrency=10,
        ),
    )
    monkeypatch.setattr(
        quota_module,
        "resolve_model_budget",
        lambda model: RateLimitConfig(
            requests_per_minute=1,
            tokens_per_minute=1000,
            concurrency=1,
        ),
    )
    monkeypatch.setattr(quota_module, "resolve_canonical_model", lambda model: model)

    first = await service.reserve("openai", "gpt-4o-mini", messages=[])
    assert first is not None

    second = await service.reserve("azure_openai", "gpt-4o-mini", messages=[])
    assert second is None
    assert service.last_skip_reason == "model-capacity"


@pytest.mark.asyncio
async def test_quota_service_redis_reservation_uses_atomic_eval():
    class FakeRedis:
        def __init__(self) -> None:
            self.eval_calls = 0

        async def exists(self, _key):
            return False

        async def eval(self, *_args):
            self.eval_calls += 1
            return 1

    redis = FakeRedis()
    service = ProviderQuotaService()
    reservation = QuotaReservation(
        reservation_id="reservation-1",
        provider_id="openai",
        model="gpt-4o-mini",
        canonical_model="gpt-4o-mini",
        window_key="202606050101",
        estimated_input_tokens=10,
        estimated_output_tokens=20,
        provider_scope="provider:openai:model:gpt-4o-mini",
        model_scope="model:gpt-4o-mini",
        created_at=1.0,
    )

    ok = await service._reserve_with_redis(
        redis,
        reservation,
        RateLimitConfig(requests_per_minute=10, tokens_per_minute=1000, concurrency=10),
        RateLimitConfig(requests_per_minute=10, tokens_per_minute=1000, concurrency=10),
    )

    assert ok is True
    assert redis.eval_calls == 1
