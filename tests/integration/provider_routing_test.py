"""
Real integration tests for provider routing.

These tests exercise the ProviderDispatcher directly — no HTTP overhead,
no mocking of the dispatcher itself. The real routing pipeline runs:
candidate selection, alias resolution, circuit breaker updates,
dry-run mode, and error paths.

Unit tests mock invoke() and never reach this logic.
"""

import pytest

pytestmark = pytest.mark.asyncio

_MESSAGES = [{"role": "user", "content": "ping"}]


class TestDryRun:
    async def test_dry_run_returns_routing_decision_without_invoking(self):
        """dry_run=True must return a structured routing decision; no provider is called."""
        from api.providers.dispatcher import dispatcher

        result = await dispatcher.dispatch(
            pid="mock",
            model=None,
            payload={"messages": _MESSAGES},
            dry_run=True,
        )

        assert result["ok"] is True, f"dry_run failed: {result}"
        assert result["dry_run"] is True
        assert result["resolved_provider"] == "mock"
        assert isinstance(result["candidate_order"], list)
        assert len(result["candidate_order"]) > 0
        first = result["candidate_order"][0]
        assert "provider" in first
        assert "model" in first
        assert "configured" in first

    async def test_dry_run_reports_routing_mode(self):
        """Explicit provider must report routing_mode=explicit."""
        from api.providers.dispatcher import dispatcher

        result = await dispatcher.dispatch(
            pid="mock",
            model=None,
            payload={"messages": _MESSAGES},
            dry_run=True,
        )
        assert result["routing_mode"] == "explicit"

    async def test_auto_routing_dry_run_reports_auto_mode(self):
        """Auto routing (pid=None) must report routing_mode=auto."""
        from api.providers.dispatcher import dispatcher

        result = await dispatcher.dispatch(
            pid=None,
            model=None,
            payload={"messages": _MESSAGES},
            dry_run=True,
        )
        # May fail with no-configured-providers if no real keys are set — that is valid too
        if result["ok"]:
            assert result["routing_mode"] == "auto"
        else:
            assert "error" in result


class TestAliasResolution:
    async def test_provider_alias_resolves_to_canonical_id(self):
        """'azure' is a provider alias for 'azure_openai' per providers.toml."""
        from api.providers.dispatcher import dispatcher

        result = await dispatcher.dispatch(
            pid="azure",
            model=None,
            payload={"messages": _MESSAGES},
            dry_run=True,
        )
        assert result["ok"] is True, f"alias dispatch failed: {result}"
        assert result["resolved_provider"] == "azure_openai", (
            f"Expected azure_openai, got {result['resolved_provider']}"
        )

    async def test_model_alias_resolves_provider_and_model(self):
        """model='gpt-4o' resolves to provider=openai, model=gpt-4o."""
        from api.providers.dispatcher import dispatcher

        result = await dispatcher.dispatch(
            pid=None,
            model="gpt-4o",
            payload={"messages": _MESSAGES},
            dry_run=True,
        )
        # ok=True means alias was resolved; ok=False means provider not configured
        if result["ok"]:
            assert result["resolved_provider"] == "openai"
            assert result["resolved_model"] == "gpt-4o"
        else:
            # openai not configured (no API key) — alias was resolved but provider unavailable
            # The error should NOT be "unknown-provider"
            assert "unknown-provider" not in result.get("error", ""), (
                "Model alias was not resolved before routing: "
                f"got error={result.get('error')}"
            )

    async def test_google_alias_resolves_to_gemini(self):
        """'google' is a provider alias for 'gemini' per providers.toml."""
        from api.providers.dispatcher import dispatcher

        result = await dispatcher.dispatch(
            pid="google",
            model=None,
            payload={"messages": _MESSAGES},
            dry_run=True,
        )
        assert result["ok"] is True
        assert result["resolved_provider"] == "gemini"


class TestErrorPaths:
    async def test_unknown_provider_returns_structured_error(self):
        """Completely unknown provider ID must return ok=False with unknown-provider in error."""
        from api.providers.dispatcher import dispatcher

        result = await dispatcher.dispatch(
            pid="definitely_nonexistent_xyz_provider_12345",
            model=None,
            payload={"messages": _MESSAGES},
            dry_run=True,
        )
        assert result["ok"] is False
        assert "unknown-provider" in result["error"], (
            f"Expected 'unknown-provider' in error, got: {result['error']}"
        )

    async def test_unknown_provider_does_not_raise(self):
        """dispatch() must return a dict, never raise, for unknown providers."""
        from api.providers.dispatcher import dispatcher

        result = await dispatcher.dispatch(
            pid="__not_a_real_provider__",
            model=None,
            payload={"messages": _MESSAGES},
        )
        assert isinstance(result, dict)
        assert result["ok"] is False


class TestCircuitBreaker:
    async def test_successful_dispatch_updates_registry(self):
        """
        After a real mock provider dispatch, the routing registry must record
        a success. This proves record_success() is called with real latency data
        through the full dispatch path.
        """
        from api.providers.dispatcher import dispatcher
        from api.routing.router import registry

        result = await dispatcher.dispatch(
            pid="mock",
            model=None,
            payload={"messages": _MESSAGES},
        )

        assert result["ok"] is True, f"Mock dispatch failed: {result}"
        stats = registry.get("mock")
        assert stats is not None, "registry.get('mock') returned None after successful dispatch"
        assert stats.success_rate > 0.0, (
            f"success_rate is {stats.success_rate}, expected > 0 after successful dispatch"
        )

    async def test_mock_provider_invoke_returns_real_provider_result(self):
        """The mock provider must return a ProviderResult with ok=True."""
        from api.providers.dispatcher import dispatcher

        result = await dispatcher.dispatch(
            pid="mock",
            model=None,
            payload={"messages": _MESSAGES},
        )

        assert result["ok"] is True
        assert result.get("provider") or result.get("resolved_provider")
        assert isinstance(result.get("latency_ms", 0.0), float)
