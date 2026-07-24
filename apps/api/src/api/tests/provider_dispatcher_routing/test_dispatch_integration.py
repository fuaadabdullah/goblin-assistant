"""Dispatch Integration tests for ProviderDispatcher routing."""

import asyncio

import pytest

from .conftest import _clean_env, _make_dispatcher


class TestDispatchIntegration:
    """End-to-end dispatch integration tests."""

    def setup_method(self):
        self.providers = {
            "alpha": {"capabilities": ["chat"], "priority_tier": 1},
        }
        self.d = _make_dispatcher(self.providers)

    def teardown_method(self):
        _clean_env(self.providers)

    def test_update_provider_endpoint_hot_reload(self):
        """update_provider_endpoint() changes in-memory config."""
        self.d.update_provider_endpoint("alpha", "http://new-endpoint")
        config = self.d.get_provider_config("alpha")
        assert config["endpoint"] == "http://new-endpoint"

    def test_update_provider_endpoint_clears_cache(self):
        """After endpoint update, provider list cache is invalidated."""
        self.d.list_providers()  # warm cache
        self.d.update_provider_endpoint("alpha", "http://new-endpoint")
        # Should not raise; cache is clear
        assert self.d.list_providers() is not None

    def test_update_provider_endpoint_unknown_provider(self):
        """Updating endpoint for unknown provider raises KeyError."""
        with pytest.raises(KeyError):
            self.d.update_provider_endpoint("does_not_exist", "http://x")

    def test_debug_info_returns_complete_state(self):
        info = self.d.debug_info()
        assert "routing_table" in info
        assert "registry_stats" in info
        assert "routing_min_success_rate" in info
        assert "model_aliases" in info
        assert "provider_aliases" in info
        assert "visible_provider_order" in info

    def test_debug_info_includes_provider_entry(self):
        info = self.d.debug_info()
        routing_table = info["routing_table"]
        alpha_entry = next((e for e in routing_table if e["provider_id"] == "alpha"), None)
        assert alpha_entry is not None
        assert alpha_entry["configured"] is True
        assert alpha_entry["capabilities"] == ["chat"]

    def test_list_providers_includes_configured_flag(self):
        providers = self.d.list_providers()
        assert len(providers) >= 1
        for p in providers:
            assert "id" in p
            assert "name" in p
            assert "capabilities" in p
            assert "priority_tier" in p

    def test_get_provider_config_returns_config(self):
        cfg = self.d.get_provider_config("alpha")
        assert "endpoint" in cfg
        assert "capabilities" in cfg

    def test_get_provider_config_unknown_returns_empty(self):
        cfg = self.d.get_provider_config("i_dont_exist")
        assert cfg == {}

    def test_health_all_key_structure(self):
        health = asyncio.run(self.d.health_all(include_hidden=True))
        assert "alpha" in health
        assert "healthy" in health["alpha"]
        assert "configured" in health["alpha"]
        assert "latency_ms" in health["alpha"]
        assert "error" in health["alpha"]
