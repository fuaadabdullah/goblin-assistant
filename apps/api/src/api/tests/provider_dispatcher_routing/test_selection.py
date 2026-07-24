"""Selection tests for ProviderDispatcher routing."""

from .conftest import (
    ProviderDispatcher,
    _clean_env,
    _make_dispatcher,
    _StubProvider,
)


class TestProviderSelection:
    """Tests for ``top_providers_for()`` and ``is_configured()``."""

    def setup_method(self):
        self.providers = {
            "openai": {"capabilities": ["chat", "code"], "priority_tier": 1},
            "anthropic": {"capabilities": ["chat"], "priority_tier": 2},
            "gemini": {"capabilities": ["chat", "vision"], "priority_tier": 3},
            "cohere": {"capabilities": ["embed"], "priority_tier": 4},
        }
        self.d = _make_dispatcher(self.providers)

    def teardown_method(self):
        _clean_env(self.providers)

    def test_top_providers_for_filters_by_capability(self):
        result = self.d.top_providers_for("chat")
        assert "cohere" not in result
        assert "openai" in result
        assert "anthropic" in result

    def test_top_providers_for_prefer_local_ranks_local_first(self):
        providers = {
            "cloud_a": {"capabilities": ["chat"], "local_routing": False, "tier": "cloud"},
            "edge_b": {"capabilities": ["chat"], "local_routing": True, "tier": "self_hosted"},
        }
        d = _make_dispatcher(providers)
        result = d.top_providers_for("chat", prefer_local=True)
        assert result[0] == "edge_b"
        _clean_env(providers)

    def test_top_providers_for_prefer_cost_ranks_cheapest_first(self):
        providers = {
            "expensive": {
                "capabilities": ["chat"],
                "cost_input_per_1k": 10.0,
                "cost_output_per_1k": 10.0,
            },
            "cheap": {
                "capabilities": ["chat"],
                "cost_input_per_1k": 0.1,
                "cost_output_per_1k": 0.1,
            },
        }
        d = _make_dispatcher(providers)
        result = d.top_providers_for("chat", prefer_cost=True)
        assert result[0] == "cheap"
        _clean_env(providers)

    def test_top_providers_for_respects_limit(self):
        result = self.d.top_providers_for("chat", limit=2)
        assert len(result) <= 2

    def test_top_providers_for_capability_case_insensitive(self):
        result = self.d.top_providers_for("CHAT")
        assert "openai" in result

    def test_top_providers_for_missing_capability_returns_empty(self):
        result = self.d.top_providers_for("audio")
        assert result == []

    def test_is_configured_true_when_api_key_present(self, monkeypatch):
        providers = {"testprov": {"capabilities": ["chat"]}}
        d = _make_dispatcher(providers)
        assert d.is_configured("testprov") is True
        _clean_env(providers)

    def test_is_configured_false_when_api_key_missing(self, monkeypatch):
        configs = {
            "missingkey": {
                "name": "missingkey",
                "endpoint": "http://stub",
                "capabilities": ["chat"],
                "api_key_env": "SOME_UNSET_KEY",
            }
        }
        class_map = {"missingkey": _StubProvider}
        d = ProviderDispatcher(configs=configs, class_map=class_map)
        assert d.is_configured("missingkey") is False

    def test_provider_ids_matches_list_providers(self):
        ids = self.d.provider_ids()
        listed = [p["id"] for p in self.d.list_providers()]
        assert ids == listed
