"""Error Handling tests for ProviderDispatcher routing."""

import asyncio

import pytest

from .conftest import _clean_env, _make_dispatcher


class TestErrorHandling:
    """Edge cases and defensive error handling in the dispatcher."""

    def test_candidate_order_unknown_provider_returns_empty(self):
        d = _make_dispatcher({"a": {}})
        assert d._candidate_order("nonexistent") == []
        _clean_env({"a": {}})

    def test_candidate_order_none_uses_hybrid(self):
        d = _make_dispatcher({"a": {}, "b": {}})
        none_order = d._candidate_order(None)
        auto_order = d._candidate_order("auto")
        assert none_order == auto_order
        _clean_env({"a": {}, "b": {}})

    def test_dispatcher_raises_key_error_for_missing_provider(self):
        d = _make_dispatcher({"exists": {}})
        with pytest.raises(KeyError, match="Unknown provider"):
            d.get_provider("does_not_exist")
        _clean_env({"exists": {}})

    def test_dry_run_dispatch_no_side_effects(self):
        """Dry-run dispatch does not invoke any provider."""
        d = _make_dispatcher({"p1": {"default_model": "m1"}})
        p1 = d.get_provider("p1")

        async def should_not_run(*args, **kwargs):
            raise AssertionError("provider should not be called during dry_run")

        p1._invoke_hook = should_not_run

        result = asyncio.run(d.dispatch("p1", None, {}, dry_run=True))
        assert result["ok"] is True
        assert result["dry_run"] is True
        assert result["resolved_provider"] == "p1"
        _clean_env({"p1": {}})

    def test_provider_error_category_classification(self):
        """classify_provider_error maps known error strings correctly."""
        from api.providers.base import ProviderErrorCategory, classify_provider_error

        assert classify_provider_error("401") == ProviderErrorCategory.AUTH
        assert classify_provider_error("rate limit exceeded") == ProviderErrorCategory.RATE_LIMIT
        assert classify_provider_error("timed out") == ProviderErrorCategory.TIMEOUT
        assert classify_provider_error("model not found") == ProviderErrorCategory.MODEL_ERROR
        assert classify_provider_error("502 Bad Gateway") == ProviderErrorCategory.SERVER_ERROR
        assert classify_provider_error("Connection refused") == ProviderErrorCategory.CONNECTION
        assert classify_provider_error("something else") == ProviderErrorCategory.UNKNOWN
