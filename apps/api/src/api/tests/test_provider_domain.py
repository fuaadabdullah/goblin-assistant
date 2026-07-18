"""Tests for the shared provider domain types (providers/domain.py)."""

from __future__ import annotations

import pytest

from api.providers.base import ProviderErrorCategory, ProviderHealth, ProviderResult
from api.providers.dispatcher_pkg.execution import build_invoke_kwargs
from api.providers.domain import (
    ProviderCapability,
    ProviderExecutionRequest,
    ProviderHealthSnapshot,
    ProviderHealthStatus,
    capabilities_from_config_list,
    capabilities_from_matrix,
    from_payload_dict,
    from_provider_result,
    to_payload_dict,
)
from api.providers.provider_registry import (
    ProviderRuntimeConfig,
    provider_metadata_from_runtime_config,
)


class TestBaseProviderTypedInterface:
    """invoke_typed()/capabilities_typed() are concrete BaseProvider methods —
    every provider gets them via inheritance with zero per-provider changes.
    Exercised against two different concrete subclasses to prove the
    inheritance actually works end-to-end, not just for one provider."""

    @pytest.mark.asyncio
    async def test_mock_provider_invoke_typed(self):
        from api.providers.mock_provider import MockProvider

        provider = MockProvider("mock", {"default_model": "mock-gpt"})
        request = ProviderExecutionRequest(
            provider_id="mock",
            model="mock-gpt",
            messages=[{"role": "user", "content": "hello"}],
        )
        result = await provider.invoke_typed(request)

        assert result.ok is True
        assert result.provider_id == "mock"
        assert result.model == "mock-gpt"
        assert result.latency_ms > 0

    @pytest.mark.asyncio
    async def test_anthropic_provider_invoke_typed(self, monkeypatch):
        from api.providers.anthropic_provider import AnthropicProvider

        provider = AnthropicProvider("anthropic", {"default_model": "claude-3-5-haiku-latest"})

        async def fake_invoke(messages=None, model=None, **kwargs):
            return ProviderResult(
                ok=True,
                text="hi from anthropic",
                provider="anthropic",
                model=model or "claude-3-5-haiku-latest",
                usage={"input_tokens": 2, "output_tokens": 4},
                cost_usd=0.0005,
                latency_ms=8.0,
            )

        monkeypatch.setattr(provider, "invoke", fake_invoke)

        request = ProviderExecutionRequest(
            provider_id="anthropic",
            model="claude-3-5-haiku-latest",
            messages=[{"role": "user", "content": "hello"}],
        )
        result = await provider.invoke_typed(request)

        assert result.ok is True
        assert result.text == "hi from anthropic"
        assert result.provider_id == "anthropic"
        assert result.cost_usd == 0.0005

    def test_mock_provider_capabilities_typed(self):
        from api.providers.mock_provider import MockProvider

        provider = MockProvider("mock", {"capabilities": ["chat", "embeddings"]})
        caps = provider.capabilities_typed()
        assert ProviderCapability.CHAT in caps
        assert ProviderCapability.EMBEDDINGS in caps

    def test_google_cloud_provider_capabilities_typed_includes_reranking(self):
        # GoogleCloudProvider.capabilities() stuffs an undeclared "reranking"
        # key into the matrix (see providers/google_cloud_provider.py) — this
        # is exactly the case capabilities_typed()/capabilities_from_matrix()
        # was designed to formalize.
        from api.providers.google_cloud_provider import GoogleCloudProvider

        provider = GoogleCloudProvider("gcp_vllm", {"capabilities": ["chat"]})
        caps = provider.capabilities_typed()
        assert ProviderCapability.RERANKING in caps
        assert ProviderCapability.EMBEDDINGS in caps


class TestInvokeProviderTyped:
    """End-to-end smoke test for ProviderDispatcher.invoke_provider_typed()."""

    @pytest.mark.asyncio
    async def test_typed_facade_matches_dict_facade(self, monkeypatch):
        import asyncio

        from api.providers.dispatcher import ProviderDispatcher

        dispatcher = ProviderDispatcher()
        provider = dispatcher.get_provider("openai")

        async def fake_invoke(messages=None, model=None, **kwargs):
            _ = messages, kwargs
            await asyncio.sleep(0)
            return ProviderResult(
                ok=True,
                text="typed hello",
                provider="openai",
                model=model or "gpt-4o-mini",
                usage={"input_tokens": 1, "output_tokens": 1},
                cost_usd=0.01,
                latency_ms=5.0,
            )

        monkeypatch.setattr(provider, "invoke", fake_invoke)

        request = ProviderExecutionRequest(
            provider_id="openai",
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "hi"}],
        )
        typed_result = await dispatcher.invoke_provider_typed(request)

        assert typed_result.ok is True
        assert typed_result.provider_id == "openai"
        assert typed_result.model == "gpt-4o-mini"
        assert typed_result.text == "typed hello"
        assert typed_result.cost_usd == 0.01

        # The old dict-based path must still behave identically side by side.
        dict_result = await dispatcher.invoke_provider(
            provider_id="openai",
            model="gpt-4o-mini",
            payload={"messages": [{"role": "user", "content": "hi"}]},
        )
        assert dict_result["ok"] is True
        assert dict_result["provider"] == "openai"


class TestProviderCapability:
    def test_parses_known_strings(self):
        result = capabilities_from_config_list(["chat", "embeddings"])
        assert result == frozenset({ProviderCapability.CHAT, ProviderCapability.EMBEDDINGS})

    def test_ignores_unknown_strings(self):
        result = capabilities_from_config_list(["chat", "not-a-real-capability"])
        assert result == frozenset({ProviderCapability.CHAT})

    def test_case_insensitive(self):
        result = capabilities_from_config_list(["CHAT", " Embeddings "])
        assert result == frozenset({ProviderCapability.CHAT, ProviderCapability.EMBEDDINGS})

    def test_from_matrix(self):
        matrix = {
            "chat": True,
            "stream_chat": True,
            "health": True,
            "capabilities": True,
            "embeddings": False,
            "limits": {},
        }
        result = capabilities_from_matrix(matrix)
        assert result == frozenset(
            {ProviderCapability.CHAT, ProviderCapability.STREAM_CHAT, ProviderCapability.HEALTH}
        )

    def test_from_matrix_undeclared_reranking_key(self):
        # Mirrors GoogleCloudProvider.capabilities() (google_cloud_provider.py),
        # which mutates super().capabilities()'s dict to add an undeclared
        # top-level "reranking": True key (not part of the ProviderCapabilityMatrix
        # TypedDict, and not nested under "capabilities" — a sibling key).
        matrix = {
            "chat": True,
            "stream_chat": True,
            "health": True,
            "capabilities": True,
            "embeddings": True,
            "reranking": True,
            "limits": {},
        }
        result = capabilities_from_matrix(matrix)
        assert ProviderCapability.RERANKING in result
        assert ProviderCapability.EMBEDDINGS in result


class TestProviderMetadata:
    def test_from_runtime_config(self):
        config = ProviderRuntimeConfig.from_source(
            "mock",
            {
                "name": "Mock Provider",
                "capabilities": ["chat", "embeddings"],
                "default_model": "mock-1",
                "models": ["mock-1", "mock-2"],
            },
        )
        meta = provider_metadata_from_runtime_config("mock", config)

        assert meta.provider_id == "mock"
        assert meta.display_name == "Mock Provider"
        assert meta.capabilities == frozenset(
            {ProviderCapability.CHAT, ProviderCapability.EMBEDDINGS}
        )
        assert meta.default_model == "mock-1"
        assert meta.models == ("mock-1", "mock-2")
        assert meta.configured is True

    def test_limits_pulled_from_raw_config(self):
        config = ProviderRuntimeConfig.from_source(
            "openai",
            {"max_input_tokens": 128_000, "max_output_tokens": 4096},
        )
        meta = provider_metadata_from_runtime_config("openai", config)
        assert meta.limits == {"max_input_tokens": 128_000, "max_output_tokens": 4096}


class TestProviderHealthSnapshot:
    def test_field_compatible_with_base_provider_health(self):
        base_health = ProviderHealth(
            provider_id="openai",
            healthy=True,
            latency_ms=42.0,
            error=None,
            billing_issue=False,
        )
        snapshot = ProviderHealthSnapshot(
            provider_id=base_health.provider_id,
            healthy=base_health.healthy,
            status=ProviderHealthStatus.HEALTHY,
            latency_ms=base_health.latency_ms,
            error=base_health.error,
            billing_issue=base_health.billing_issue,
            checked_at=base_health.checked_at,
        )
        assert snapshot.provider_id == base_health.provider_id
        assert snapshot.healthy == base_health.healthy
        assert snapshot.latency_ms == base_health.latency_ms
        assert snapshot.error == base_health.error
        assert snapshot.billing_issue == base_health.billing_issue
        assert snapshot.checked_at == base_health.checked_at

    def test_base_provider_health_is_the_same_class(self):
        # base.ProviderHealth is now an alias, not a subclass.
        assert ProviderHealth is ProviderHealthSnapshot

    def test_status_auto_derived_when_omitted(self):
        # Every one of the 17 concrete providers constructs ProviderHealth
        # with provider_id/healthy positional and never passes `status` —
        # this is the exact call shape that must keep working post-alias.
        healthy = ProviderHealth("openai", True, latency_ms=5.0)
        assert healthy.status == ProviderHealthStatus.HEALTHY

        unhealthy = ProviderHealth("openai", False, error="no api key")
        assert unhealthy.status == ProviderHealthStatus.UNHEALTHY

        billing = ProviderHealth("openai", False, error="quota", billing_issue=True)
        assert billing.status == ProviderHealthStatus.BILLING_ISSUE

    def test_status_explicit_value_respected(self):
        health = ProviderHealth(
            "openai", True, status=ProviderHealthStatus.DEGRADED, latency_ms=999.0
        )
        assert health.status == ProviderHealthStatus.DEGRADED


class TestProviderExecutionRequest:
    def test_to_payload_dict_compatible_with_build_invoke_kwargs(self):
        req = ProviderExecutionRequest(
            provider_id="mock",
            model="mock-1",
            messages=[{"role": "user", "content": "hi"}],
            stream=True,
            max_tokens=256,
            temperature=0.5,
            timeout_ms=15_000,
        )
        payload = to_payload_dict(req)
        # build_invoke_kwargs is what dispatcher_pkg/execution.py actually calls
        # before invoking BaseProvider.invoke(messages=..., model=..., **kwargs).
        kwargs = build_invoke_kwargs(payload)

        assert "messages" not in kwargs
        assert "model" not in kwargs
        assert "prompt" not in kwargs
        # "stream" must never land in the payload dict: dispatcher_pkg/test_mode.py
        # hardcodes stream=False when calling provider.invoke(**kwargs) on the
        # non-streaming path, so a "stream" key surviving into kwargs is a
        # duplicate-keyword crash. It flows as invoke_provider_typed's separate
        # `stream=` argument instead (see dispatcher.invoke_provider_typed).
        assert "stream" not in kwargs
        assert kwargs["max_tokens"] == 256
        assert kwargs["temperature"] == 0.5
        assert kwargs["timeout_ms"] == 15_000

    def test_round_trip(self):
        req = ProviderExecutionRequest(
            provider_id="mock",
            model="mock-1",
            messages=[{"role": "user", "content": "hi"}],
            stream=False,
            max_tokens=100,
            temperature=0.2,
            timeout_ms=20_000,
            extra={"user_id": "u1"},
        )
        payload = to_payload_dict(req)
        rebuilt = from_payload_dict(payload, provider_id=req.provider_id, model=req.model)

        assert rebuilt.messages == req.messages
        assert rebuilt.stream == req.stream
        assert rebuilt.max_tokens == req.max_tokens
        assert rebuilt.temperature == req.temperature
        assert rebuilt.timeout_ms == req.timeout_ms
        assert rebuilt.extra == req.extra

    def test_from_payload_dict_defaults(self):
        req = from_payload_dict({}, provider_id="mock", model="mock-1")
        assert req.messages == []
        assert req.stream is False
        assert req.timeout_ms == 30_000


class TestProviderExecutionResult:
    def test_from_provider_result_ok(self):
        pr = ProviderResult(
            ok=True,
            text="hello",
            provider="mock",
            model="mock-1",
            usage={"prompt_tokens": 5, "completion_tokens": 3},
            cost_usd=0.001,
            latency_ms=12.5,
        )
        result = from_provider_result(pr, provider_id="mock", model="mock-1")

        assert result.ok is True
        assert result.provider_id == "mock"
        assert result.model == "mock-1"
        assert result.text == "hello"
        assert result.usage == {"prompt_tokens": 5, "completion_tokens": 3}
        assert result.cost_usd == 0.001
        assert result.latency_ms == 12.5
        assert result.error_category is None

    def test_from_provider_result_error_branch(self):
        pr = ProviderResult(
            ok=False,
            provider="openai",
            model="gpt-4o-mini",
            error="401 unauthorized",
            error_category=ProviderErrorCategory.AUTH.value,
        )
        result = from_provider_result(pr, provider_id="openai", model="gpt-4o-mini")

        assert result.ok is False
        assert result.error == "401 unauthorized"
        assert result.error_category == ProviderErrorCategory.AUTH

    def test_from_provider_result_unrecognized_error_category(self):
        pr = ProviderResult(
            ok=False,
            provider="openai",
            model="gpt-4o-mini",
            error="boom",
            error_category="totally-made-up",
        )
        result = from_provider_result(pr, provider_id="openai", model="gpt-4o-mini")
        assert result.error_category is None
