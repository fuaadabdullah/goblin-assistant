"""Failover tests for ProviderDispatcher routing."""

import asyncio

import pytest

from .conftest import _clean_env, _make_dispatcher


class TestProviderFailover:
    """Tests for dispatch failover across multiple candidates."""

    def setup_method(self):
        self.providers = {
            "primary": {"capabilities": ["chat"], "priority_tier": 1},
            "secondary": {"capabilities": ["chat"], "priority_tier": 2},
            "tertiary": {"capabilities": ["chat"], "priority_tier": 3},
        }
        self.d = _make_dispatcher(self.providers)

    def teardown_method(self):
        _clean_env(self.providers)

    @pytest.mark.asyncio
    async def test_failover_when_primary_returns_failure(self):
        """When the primary provider returns ok=False, dispatch falls through."""
        primary = self.d.get_provider("primary")
        primary._fake_fail = True

        result = await self.d.dispatch(
            pid="auto",
            model="stub-model",
            payload={"messages": [{"role": "user", "content": "hello"}]},
        )

        assert result["ok"] is True
        assert result["provider"] == "secondary"

    @pytest.mark.asyncio
    async def test_failover_when_primary_raises_exception(self):
        """Exception thrown by a provider invoke → next provider is tried."""
        primary = self.d.get_provider("primary")

        async def boom(*args, **kwargs):
            raise RuntimeError("primary exploded")

        primary._invoke_hook = boom

        result = await self.d.dispatch(
            pid="auto",
            model="stub-model",
            payload={"messages": [{"role": "user", "content": "hello"}]},
        )

        assert result["ok"] is True
        assert result["provider"] == "secondary"

    @pytest.mark.asyncio
    async def test_failover_on_timeout_tries_next_provider(self):
        """asyncio.TimeoutError from a provider → next candidate is tried."""
        primary = self.d.get_provider("primary")

        async def hang(*args, **kwargs):
            await asyncio.sleep(600)

        primary._invoke_hook = hang

        result = await self.d.dispatch(
            pid="auto",
            model="stub-model",
            payload={"messages": [{"role": "user", "content": "hello"}]},
            timeout_ms=5,
        )

        assert result["ok"] is True
        assert result["provider"] == "secondary"

    @pytest.mark.asyncio
    async def test_failover_chain_exhaustion_returns_error(self):
        """All candidates fail → dispatch returns ok=False with last error."""
        for pid in ("primary", "secondary", "tertiary"):
            p = self.d.get_provider(pid)
            p._fake_fail = True

        result = await self.d.dispatch(
            pid="auto",
            model="stub-model",
            payload={"messages": [{"role": "user", "content": "hello"}]},
        )

        assert result["ok"] is False
        assert result["provider"] == "none"
        assert result["error"] == "stub failure"

    @pytest.mark.asyncio
    async def test_explicit_provider_no_fallback_does_not_fallback(self):
        """Explicit provider without force_fallback stays single even on failure."""
        primary = self.d.get_provider("primary")
        secondary = self.d.get_provider("secondary")
        primary._fake_fail = True

        secondary._invoke_hook = lambda *a, **kw: (
            None if False else (_ for _ in ()).throw(AssertionError("should not be called"))
        )

        result = await self.d.dispatch(
            pid="primary",
            model="stub-model",
            payload={"messages": [{"role": "user", "content": "hello"}]},
        )

        assert result["ok"] is False
        assert result["provider"] == "none"

    @pytest.mark.asyncio
    async def test_dispatch_unknown_provider_returns_error(self):
        """Unknown provider pid → ok=False with unknown-provider error."""
        result = await self.d.dispatch(
            pid="nonexistent_provider",
            model="stub-model",
            payload={"messages": [{"role": "user", "content": "hello"}]},
        )

        assert result["ok"] is False
        assert "unknown-provider" in result["error"]

    @pytest.mark.asyncio
    async def test_dispatch_with_prompt_not_messages(self):
        """Payload with 'prompt' key works (backward compat path)."""
        result = await self.d.dispatch(
            pid="primary",
            model="stub-model",
            payload={"prompt": "hello world"},
        )

        assert result["ok"] is True
        assert result["provider"] == "primary"

    @pytest.mark.asyncio
    async def test_dispatch_records_latency_in_registry(self):
        """After a successful dispatch, registry EWMA latency is updated."""
        from api.routing.router import registry

        before = registry.get("primary").ewma_latency_ms

        await self.d.dispatch(
            pid="primary",
            model="stub-model",
            payload={"messages": [{"role": "user", "content": "hello"}]},
        )

        after = registry.get("primary").ewma_latency_ms
        assert after != before  # registry was updated
