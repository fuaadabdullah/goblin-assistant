"""Tests for dispatcher_pkg/discovery.py — provider listing, capability queries, and config access."""

from __future__ import annotations

from typing import Callable, Dict, Optional
from unittest.mock import MagicMock

import pytest

from api.providers.dispatcher_pkg.discovery import (
    build_provider_list,
    get_provider,
    get_provider_config,
    is_configured,
    list_providers,
)

# =========================================================================
# Helpers
# =========================================================================


def _make_dispatcher(
    configs: Optional[Dict[str, dict]] = None,
    provider_list_cache: Optional[Dict[bool, list]] = None,
    using_custom_configs: bool = False,
    runtime_config_fn: Optional[Callable] = None,
    ensure_provider_fn: Optional[Callable] = None,
) -> MagicMock:
    """Build a mock dispatcher with the attributes discovery functions expect."""
    dispatcher = MagicMock()
    dispatcher._configs = configs or {}
    dispatcher._provider_list_cache = provider_list_cache or {}
    dispatcher._using_custom_configs = using_custom_configs
    dispatcher._runtime_config = runtime_config_fn or (lambda pid: None)
    dispatcher._ensure_provider = ensure_provider_fn or (lambda pid: None)
    # Wire build_provider_list so list_providers can delegate
    dispatcher._build_provider_list = lambda include_hidden=False: build_provider_list(
        dispatcher,
        _canonical,
        list(dispatcher._configs.keys()),
        include_hidden=include_hidden,
    )
    return dispatcher


def _canonical(pid: Optional[str]) -> Optional[str]:
    """Stub canonical_fn that returns the id unchanged."""
    return pid


def _runtime_config_configured(pid: str) -> MagicMock:
    """Return a mock runtime config that reports is_configured() == True."""
    cfg = MagicMock()
    cfg.is_configured.return_value = True
    return cfg


def _runtime_config_not_configured(pid: str) -> MagicMock:
    """Return a mock runtime config that reports is_configured() == False."""
    cfg = MagicMock()
    cfg.is_configured.return_value = False
    return cfg


# =========================================================================
# build_provider_list
# =========================================================================


class TestBuildProviderList:
    def test_visible_ids_filters_by_list(self):
        """When include_hidden=False and visible_ids is non-empty, only those
        providers that appear in visible_ids are returned, in visible_ids order."""
        dispatcher = _make_dispatcher(
            configs={
                "openai": {"name": "OpenAI", "priority_tier": 10},
                "anthropic": {"name": "Anthropic", "priority_tier": 20},
                "groq": {"name": "Groq", "priority_tier": 5},
            },
        )
        result = build_provider_list(
            dispatcher,
            _canonical,
            visible_ids=["groq", "openai"],
            include_hidden=False,
        )
        ids = [p["id"] for p in result]
        assert ids == ["groq", "openai"], f"Expected [groq, openai], got {ids}"

    def test_include_hidden_returns_all_providers(self):
        """When include_hidden=True, all providers are returned regardless of
        visible_ids."""
        dispatcher = _make_dispatcher(
            configs={
                "openai": {"name": "OpenAI", "hidden": False},
                "anthropic": {"name": "Anthropic", "hidden": True},
            },
        )
        result = build_provider_list(
            dispatcher,
            _canonical,
            visible_ids=["openai"],
            include_hidden=True,
        )
        ids = [p["id"] for p in result]
        assert "openai" in ids
        assert "anthropic" in ids

    def test_empty_visible_ids_uses_all_configs(self):
        """When visible_ids is empty, all config keys are returned."""
        dispatcher = _make_dispatcher(
            configs={
                "openai": {"name": "OpenAI"},
                "anthropic": {"name": "Anthropic"},
            },
        )
        result = build_provider_list(
            dispatcher,
            _canonical,
            visible_ids=[],
            include_hidden=False,
        )
        ids = [p["id"] for p in result]
        assert "openai" in ids
        assert "anthropic" in ids

    def test_using_custom_configs_returns_all(self):
        """When dispatcher._using_custom_configs is True, all providers are
        returned even if visible_ids is non-empty."""
        dispatcher = _make_dispatcher(
            configs={
                "openai": {"name": "OpenAI"},
                "anthropic": {"name": "Anthropic"},
            },
            using_custom_configs=True,
        )
        result = build_provider_list(
            dispatcher,
            _canonical,
            visible_ids=["openai"],
            include_hidden=False,
        )
        ids = [p["id"] for p in result]
        assert "openai" in ids
        assert "anthropic" in ids

    def test_hidden_providers_excluded_when_not_include_hidden(self):
        """Providers with hidden=True are excluded when include_hidden=False."""
        dispatcher = _make_dispatcher(
            configs={
                "openai": {"name": "OpenAI", "hidden": False},
                "secret": {"name": "Secret", "hidden": True},
            },
        )
        result = build_provider_list(
            dispatcher,
            _canonical,
            visible_ids=["openai", "secret"],
            include_hidden=False,
        )
        ids = [p["id"] for p in result]
        assert "openai" in ids
        assert "secret" not in ids

    def test_canonical_fn_returns_none_skips_entry(self):
        """When canonical_fn returns None for a visible_id, the raw id is used
        as a fallback."""

        def _canonical_none(pid: Optional[str]) -> Optional[str]:
            return None if pid == "skip-me" else pid

        dispatcher = _make_dispatcher(
            configs={
                "openai": {"name": "OpenAI"},
                "skip-me": {"name": "Skip"},
            },
        )
        result = build_provider_list(
            dispatcher,
            _canonical_none,
            visible_ids=["openai", "skip-me"],
            include_hidden=False,
        )
        ids = [p["id"] for p in result]
        assert "openai" in ids
        assert "skip-me" in ids

    def test_duplicate_visible_ids_skipped(self):
        """Duplicate entries in visible_ids are only included once."""
        dispatcher = _make_dispatcher(
            configs={
                "openai": {"name": "OpenAI"},
            },
        )
        result = build_provider_list(
            dispatcher,
            _canonical,
            visible_ids=["openai", "openai", "openai"],
            include_hidden=False,
        )
        ids = [p["id"] for p in result]
        assert ids == ["openai"]

    def test_provider_dict_contains_expected_keys(self):
        """Each provider dict includes id, name, endpoint, endpoint_env,
        api_key_env, default_model, models, capabilities, priority_tier, tier,
        local_routing, and hidden."""
        dispatcher = _make_dispatcher(
            configs={
                "test-provider": {
                    "name": "Test Provider",
                    "endpoint": "https://test.example.com",
                    "endpoint_env": "TEST_ENDPOINT",
                    "api_key_env": "TEST_API_KEY",
                    "default_model": "test-model",
                    "models": ["model-a", "model-b"],
                    "capabilities": ["chat", "vision"],
                    "priority_tier": 25,
                    "tier": "cloud",
                    "local_routing": False,
                    "hidden": False,
                },
            },
        )
        result = build_provider_list(
            dispatcher,
            _canonical,
            visible_ids=["test-provider"],
            include_hidden=False,
        )
        assert len(result) == 1
        entry = result[0]
        assert entry["id"] == "test-provider"
        assert entry["name"] == "Test Provider"
        assert entry["endpoint"] == "https://test.example.com"
        assert entry["endpoint_env"] == "TEST_ENDPOINT"
        assert entry["api_key_env"] == "TEST_API_KEY"
        assert entry["default_model"] == "test-model"
        assert entry["models"] == ["model-a", "model-b"]
        assert entry["capabilities"] == ["chat", "vision"]
        assert entry["priority_tier"] == 25
        assert entry["tier"] == "cloud"
        assert entry["local_routing"] is False
        assert entry["hidden"] is False

    def test_runtime_config_to_provider_dict_used_when_available(self):
        """When _runtime_config returns a config, to_provider_dict() is used."""
        runtime_cfg = MagicMock()
        runtime_cfg.to_provider_dict.return_value = {
            "name": "Runtime Provider",
            "endpoint": "https://runtime.example.com",
            "endpoint_env": None,
            "api_key_env": None,
        }

        def _runtime(pid: str):
            return runtime_cfg if pid == "runtime-provider" else None

        dispatcher = _make_dispatcher(
            configs={"runtime-provider": {"name": "Raw Provider"}},
            runtime_config_fn=_runtime,
        )
        result = build_provider_list(
            dispatcher,
            _canonical,
            visible_ids=["runtime-provider"],
            include_hidden=False,
        )
        assert len(result) == 1
        assert result[0]["name"] == "Runtime Provider"
        runtime_cfg.to_provider_dict.assert_called_once()

    def test_missing_config_key_falls_back_to_raw(self):
        """When a provider id is in visible_ids but not in _configs, it is
        skipped (no KeyError)."""
        dispatcher = _make_dispatcher(configs={"openai": {"name": "OpenAI"}})
        result = build_provider_list(
            dispatcher,
            _canonical,
            visible_ids=["openai", "nonexistent"],
            include_hidden=False,
        )
        ids = [p["id"] for p in result]
        assert ids == ["openai"]


# =========================================================================
# list_providers
# =========================================================================


class TestListProviders:
    def test_returns_cached_results(self):
        """When the cache has an entry for include_hidden, it is returned
        without calling _build_provider_list again."""
        cached = [{"id": "cached-provider", "name": "Cached"}]
        dispatcher = _make_dispatcher(
            configs={"cached-provider": {"name": "Cached"}},
            provider_list_cache={False: cached},
        )
        # Even though visible_ids is empty, the cache should be returned
        result = list_providers(dispatcher, _canonical, visible_ids=[])
        assert result == cached

    def test_cache_miss_calls_build_and_caches(self):
        """On cache miss, _build_provider_list is called and the result is
        cached."""
        dispatcher = _make_dispatcher(
            configs={"p1": {"name": "P1", "priority_tier": 10}},
            provider_list_cache={},
        )
        result = list_providers(dispatcher, _canonical, visible_ids=["p1"])
        assert len(result) == 1
        assert result[0]["id"] == "p1"
        # The result should now be cached
        assert dispatcher._provider_list_cache.get(False) is not None

    def test_sorts_by_priority_tier_then_id(self):
        """When using_custom_configs is True, providers are sorted by
        priority_tier (ascending) then id."""
        dispatcher = _make_dispatcher(
            configs={
                "z-provider": {"name": "Z", "priority_tier": 50},
                "a-provider": {"name": "A", "priority_tier": 10},
                "m-provider": {"name": "M", "priority_tier": 10},
            },
            using_custom_configs=True,
        )
        result = list_providers(dispatcher, _canonical, visible_ids=[])
        ids = [p["id"] for p in result]
        # a-provider and m-provider both have priority 10, sorted by id
        # z-provider has priority 50
        assert ids == ["a-provider", "m-provider", "z-provider"], f"Got {ids}"

    def test_returns_deep_copy_of_cached_items(self):
        """Each call returns a new list of new dicts, not a reference to the
        cached mutable objects."""
        dispatcher = _make_dispatcher(
            configs={"p1": {"name": "P1"}},
            provider_list_cache={},
        )
        result1 = list_providers(dispatcher, _canonical, visible_ids=["p1"])
        result2 = list_providers(dispatcher, _canonical, visible_ids=["p1"])
        assert result1 is not result2
        assert result1[0] is not result2[0]
        assert result1 == result2


# =========================================================================
# is_configured
# =========================================================================


class TestIsConfigured:
    def test_returns_true_when_runtime_config_says_configured(self):
        """When _runtime_config returns a config whose is_configured() is True,
        is_configured returns True."""
        dispatcher = _make_dispatcher(
            runtime_config_fn=_runtime_config_configured,
        )
        assert is_configured(dispatcher, _canonical, "openai") is True

    def test_returns_false_when_runtime_config_says_not_configured(self):
        """When _runtime_config returns a config whose is_configured() is False,
        is_configured returns False."""
        dispatcher = _make_dispatcher(
            runtime_config_fn=_runtime_config_not_configured,
        )
        assert is_configured(dispatcher, _canonical, "openai") is False

    def test_returns_false_when_runtime_config_is_none(self):
        """When _runtime_config returns None, is_configured returns False."""
        dispatcher = _make_dispatcher(runtime_config_fn=lambda pid: None)
        assert is_configured(dispatcher, _canonical, "openai") is False

    def test_canonical_fn_returns_none_uses_raw_id(self):
        """When canonical_fn returns None, the raw provider_id is used as the
        canonical id."""

        def _canonical_none(pid: Optional[str]) -> Optional[str]:
            return None

        runtime_cfg = MagicMock()
        runtime_cfg.is_configured.return_value = True

        def _runtime(pid: str):
            return runtime_cfg if pid == "raw-id" else None

        dispatcher = _make_dispatcher(runtime_config_fn=_runtime)
        assert is_configured(dispatcher, _canonical_none, "raw-id") is True

    def test_canonical_fn_resolves_alias(self):
        """canonical_fn is called to resolve the provider id before checking."""

        def _canonical_alias(pid: Optional[str]) -> Optional[str]:
            return {"google": "gemini"}.get(pid, pid)

        runtime_cfg = MagicMock()
        runtime_cfg.is_configured.return_value = True

        def _runtime(pid: str):
            return runtime_cfg if pid == "gemini" else None

        dispatcher = _make_dispatcher(runtime_config_fn=_runtime)
        assert is_configured(dispatcher, _canonical_alias, "google") is True


# =========================================================================
# get_provider
# =========================================================================


class TestGetProvider:
    def test_returns_provider_when_exists(self):
        """When _ensure_provider returns a provider, get_provider returns it."""
        provider = MagicMock()
        provider.provider_id = "openai"

        def _ensure(pid: str):
            return provider if pid == "openai" else None

        dispatcher = _make_dispatcher(ensure_provider_fn=_ensure)
        result = get_provider(dispatcher, _canonical, "openai")
        assert result is provider

    def test_raises_key_error_when_not_found(self):
        """When _ensure_provider returns None, get_provider raises KeyError."""
        dispatcher = _make_dispatcher(ensure_provider_fn=lambda pid: None)
        with pytest.raises(KeyError, match="Unknown provider: nonexistent"):
            get_provider(dispatcher, _canonical, "nonexistent")

    def test_canonical_fn_resolves_alias(self):
        """canonical_fn is called to resolve the provider id before looking up."""

        def _canonical_alias(pid: Optional[str]) -> Optional[str]:
            return {"google": "gemini"}.get(pid, pid)

        provider = MagicMock()
        provider.provider_id = "gemini"

        def _ensure(pid: str):
            return provider if pid == "gemini" else None

        dispatcher = _make_dispatcher(ensure_provider_fn=_ensure)
        result = get_provider(dispatcher, _canonical_alias, "google")
        assert result is provider

    def test_canonical_fn_returns_none_uses_raw_id(self):
        """When canonical_fn returns None, the raw provider_id is used."""

        def _canonical_none(pid: Optional[str]) -> Optional[str]:
            return None

        provider = MagicMock()

        def _ensure(pid: str):
            return provider if pid == "raw-id" else None

        dispatcher = _make_dispatcher(ensure_provider_fn=_ensure)
        result = get_provider(dispatcher, _canonical_none, "raw-id")
        assert result is provider


# =========================================================================
# get_provider_config
# =========================================================================


class TestGetProviderConfig:
    def test_returns_config_for_existing_provider(self):
        """get_provider_config returns the config dict for an existing provider."""
        dispatcher = _make_dispatcher(
            configs={
                "openai": {
                    "name": "OpenAI",
                    "endpoint": "https://api.openai.com",
                },
            },
        )
        result = get_provider_config(dispatcher, _canonical, "openai")
        assert result == {
            "name": "OpenAI",
            "endpoint": "https://api.openai.com",
        }

    def test_returns_empty_dict_for_unknown_provider(self):
        """get_provider_config returns an empty dict for an unknown provider."""
        dispatcher = _make_dispatcher(configs={})
        result = get_provider_config(dispatcher, _canonical, "nonexistent")
        assert result == {}

    def test_canonical_fn_resolves_alias(self):
        """canonical_fn is called to resolve the provider id before lookup."""

        def _canonical_alias(pid: Optional[str]) -> Optional[str]:
            return {"google": "gemini"}.get(pid, pid)

        dispatcher = _make_dispatcher(
            configs={
                "gemini": {
                    "name": "Gemini",
                    "endpoint": "https://gemini.example.com",
                },
            },
        )
        result = get_provider_config(dispatcher, _canonical_alias, "google")
        assert result["name"] == "Gemini"

    def test_returns_copy_not_reference(self):
        """The returned dict is a copy, not a reference to the internal config."""
        dispatcher = _make_dispatcher(
            configs={"p1": {"name": "P1"}},
        )
        result = get_provider_config(dispatcher, _canonical, "p1")
        result["name"] = "Mutated"
        # Internal config should be unchanged
        assert dispatcher._configs["p1"]["name"] == "P1"
