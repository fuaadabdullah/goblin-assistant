"""Provider-specific timeout propagation for the chat dispatch stage.

Regression tests for the defect where the ordinary chat dispatcher always
passed a fixed 30s timeout to ``invoke_provider``, cancelling slow providers
(e.g. the Oracle llama.cpp backend declaring ``invoke_timeout_s=600``) long
before the provider's own timeout could take effect.
"""

import pytest

from api.chat_router.messages import dispatch as dispatch_module
from api.chat_router.messages.dispatch import (
    PROVIDER_TIMEOUT_MS,
    _timeout_for_provider,
    dispatch_with_fallback,
)
from api.providers.base import BaseProvider
from api.providers.google_cloud_selfhosted_provider import (
    GoogleCloudSelfhostedProvider,
)


class _ConcreteProvider(BaseProvider):
    async def invoke(self, *args, **kwargs):  # pragma: no cover - never called
        raise NotImplementedError

    async def stream(self, *args, **kwargs):  # pragma: no cover - never called
        raise NotImplementedError
        yield {}

    async def health_check(self, *args, **kwargs):  # pragma: no cover - never called
        raise NotImplementedError


class TestInvokeTimeoutMs:
    def test_declared_timeout_converted_to_ms(self):
        provider = _ConcreteProvider("p", {"invoke_timeout_s": 600})
        assert provider.invoke_timeout_ms() == 600_000

    def test_no_declaration_returns_none(self):
        provider = _ConcreteProvider("p", {})
        assert provider.invoke_timeout_ms() is None

    def test_invalid_declaration_returns_none(self):
        provider = _ConcreteProvider("p", {"invoke_timeout_s": "soon"})
        assert provider.invoke_timeout_ms() is None

    def test_zero_or_negative_returns_none(self):
        assert _ConcreteProvider("p", {"invoke_timeout_s": 0}).invoke_timeout_ms() is None
        assert _ConcreteProvider("p", {"invoke_timeout_s": -5}).invoke_timeout_ms() is None


class TestSelfHostedAggregateTimeout:
    def _backend(self, timeout_s):
        return _ConcreteProvider("gcp_vm.llamacpp", {"invoke_timeout_s": timeout_s})

    def test_slowest_backend_wins(self):
        provider = GoogleCloudSelfhostedProvider.__new__(GoogleCloudSelfhostedProvider)
        BaseProvider.__init__(provider, "gcp_vm", {})
        provider._backends = [self._backend(120), self._backend(600)]
        assert provider.invoke_timeout_ms() == 600_000

    def test_no_backends_returns_none(self):
        provider = GoogleCloudSelfhostedProvider.__new__(GoogleCloudSelfhostedProvider)
        BaseProvider.__init__(provider, "gcp_vm", {})
        provider._backends = []
        assert provider.invoke_timeout_ms() is None


class TestTimeoutForProvider:
    def test_honors_declared_timeout_above_default(self, monkeypatch):
        monkeypatch.setattr(
            dispatch_module._provider_dispatcher,
            "provider_invoke_timeout_ms",
            lambda pid: 600_000,
        )
        assert _timeout_for_provider("gcp_vm") == 600_000

    def test_declared_timeout_below_default_keeps_default(self, monkeypatch):
        monkeypatch.setattr(
            dispatch_module._provider_dispatcher,
            "provider_invoke_timeout_ms",
            lambda pid: 5_000,
        )
        assert _timeout_for_provider("openai") == PROVIDER_TIMEOUT_MS

    def test_unknown_provider_falls_back_to_default(self, monkeypatch):
        monkeypatch.setattr(
            dispatch_module._provider_dispatcher,
            "provider_invoke_timeout_ms",
            lambda pid: None,
        )
        assert _timeout_for_provider("nope") == PROVIDER_TIMEOUT_MS

    def test_lookup_failure_falls_back_to_default(self, monkeypatch):
        def _boom(pid):
            raise RuntimeError("catalog exploded")

        monkeypatch.setattr(
            dispatch_module._provider_dispatcher, "provider_invoke_timeout_ms", _boom
        )
        assert _timeout_for_provider("gcp_vm") == PROVIDER_TIMEOUT_MS


def _dispatch_kwargs(**overrides):
    kwargs = {
        "resolved_provider": "gcp_vm",
        "resolved_department": "general",
        "pinned_provider": None,
        "model": "goblin-core",
        "payload": {"messages": [{"role": "user", "content": "hi"}]},
        "fallback_chain": [],
        "sanitized_message": "hi",
        "conversation_id": "conv-1",
        "user_id": "user-1",
        "complexity_score": 0.1,
        "intent_meta": {},
        "registered_tools": [],
        "messages": [{"role": "user", "content": "hi"}],
    }
    kwargs.update(overrides)
    return kwargs


class TestDispatchWithFallbackTimeout:
    @pytest.mark.asyncio
    async def test_primary_invoke_uses_provider_timeout(self, monkeypatch):
        seen = {}

        async def fake_invoke_provider(**kwargs):
            seen.update(kwargs)
            return {
                "ok": True,
                "result": {
                    "text": "hello",
                    "raw": {"choices": [{"message": {"content": "hello"}}]},
                    "usage": {},
                    "cost_usd": 0.0,
                },
                "provider": kwargs.get("pid"),
            }

        monkeypatch.setattr("api.chat_router.invoke_provider", fake_invoke_provider)
        monkeypatch.setattr(
            dispatch_module._provider_dispatcher,
            "provider_invoke_timeout_ms",
            lambda pid: 600_000,
        )

        response, provider = await dispatch_with_fallback(**_dispatch_kwargs())

        assert provider == "gcp_vm"
        assert response["ok"] is True
        assert seen["timeout_ms"] == 600_000

    @pytest.mark.asyncio
    async def test_fallback_attempt_uses_fallback_provider_timeout(self, monkeypatch):
        seen_timeouts = []

        async def fake_invoke_provider(**kwargs):
            seen_timeouts.append((kwargs["pid"], kwargs["timeout_ms"]))
            if kwargs["pid"] == "gcp_vm":
                return {"ok": False, "error": "boom"}
            return {
                "ok": True,
                "result": {
                    "text": "fallback hello",
                    "raw": {"choices": [{"message": {"content": "fallback hello"}}]},
                    "usage": {},
                    "cost_usd": 0.0,
                },
                "provider": kwargs.get("pid"),
            }

        declared = {"gcp_vm": 600_000, "openai": None}
        monkeypatch.setattr("api.chat_router.invoke_provider", fake_invoke_provider)
        monkeypatch.setattr(
            dispatch_module._provider_dispatcher,
            "provider_invoke_timeout_ms",
            declared.get,
        )

        response, provider = await dispatch_with_fallback(
            **_dispatch_kwargs(fallback_chain=["openai"])
        )

        assert provider == "openai"
        assert response["ok"] is True
        assert seen_timeouts == [
            ("gcp_vm", 600_000),
            ("openai", PROVIDER_TIMEOUT_MS),
        ]

    @pytest.mark.asyncio
    async def test_tool_loop_uses_resolved_provider_timeout(self, monkeypatch):
        seen = {}

        async def fake_invoke_provider(**kwargs):
            return {
                "ok": True,
                "result": {
                    "text": "",
                    "raw": {
                        "choices": [
                            {
                                "message": {
                                    "content": "",
                                    "tool_calls": [
                                        {
                                            "id": "call-1",
                                            "type": "function",
                                            "function": {
                                                "name": "get_time",
                                                "arguments": "{}",
                                            },
                                        }
                                    ],
                                }
                            }
                        ]
                    },
                    "usage": {},
                    "cost_usd": 0.0,
                },
                "provider": kwargs.get("pid"),
            }

        async def fake_run_tool_loop(**kwargs):
            seen.update(kwargs)
            return {"ok": True, "text": "done"}

        monkeypatch.setattr("api.chat_router.invoke_provider", fake_invoke_provider)
        monkeypatch.setattr(dispatch_module, "run_tool_loop", fake_run_tool_loop)
        monkeypatch.setattr(
            dispatch_module._provider_dispatcher,
            "provider_invoke_timeout_ms",
            lambda pid: 600_000,
        )

        await dispatch_with_fallback(**_dispatch_kwargs(registered_tools=[{"name": "get_time"}]))

        assert seen["timeout_ms"] == 600_000
        assert seen["provider"] == "gcp_vm"
