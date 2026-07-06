"""Tests for ProviderDispatcher configuration, aliases, and reload."""

import asyncio
import importlib
import os
import re
from unittest.mock import MagicMock

import pytest

from api.providers.base import ProviderResult
from api.providers.dispatcher import ProviderDispatcher

dispatcher_module = importlib.import_module("api.providers.dispatcher")


def test_dispatcher_resolves_provider_aliases():
    dispatcher = ProviderDispatcher()

    assert dispatcher.get_provider("google").provider_id == "gemini"
    assert dispatcher.get_provider("azure-openai").provider_id == "azure_openai"
    assert dispatcher.get_provider("vertex").provider_id == "gcp_vm"


def test_dispatcher_visible_provider_ids_include_together():
    dispatcher = ProviderDispatcher()

    visible_ids = dispatcher.provider_ids(include_hidden=False)

    assert "together" in visible_ids


def test_dispatcher_visible_order_siliconeflow_before_together():
    # siliconeflow (priority 25) is cheaper and faster than together (priority 45)
    dispatcher = ProviderDispatcher()

    visible_ids = dispatcher.provider_ids(include_hidden=False)

    assert visible_ids.index("siliconeflow") < visible_ids.index("together")


def test_dispatcher_reload_and_endpoint_update_paths(monkeypatch):
    dispatcher = ProviderDispatcher()
    original_provider_toml = dispatcher_module._provider_toml
    original_provider_configs = dispatcher_module._PROVIDER_CONFIGS
    original_provider_aliases = dispatcher_module._PROVIDER_ALIASES
    original_model_aliases = dispatcher_module._MODEL_ALIASES
    original_model_alias_patterns = dispatcher_module._MODEL_ALIAS_PATTERNS
    original_visible_provider_ids = dispatcher_module._VISIBLE_PROVIDER_IDS
    dispatcher._configs["openai"] = {
        "endpoint": "https://old.example.com",
        "endpoint_env": "OPENAI_ENDPOINT",
        "backends": [
            {
                "engine": "chat",
                "endpoint": "https://old-backend.example.com",
                "endpoint_env": "OPENAI_BACKEND_ENDPOINT",
            }
        ],
    }
    dispatcher._configs["broken"] = "oops"  # type: ignore[assignment]

    warning = MagicMock()
    monkeypatch.setattr(dispatcher_module.logger, "warning", warning)

    monkeypatch.setattr(dispatcher._registry, "runtime_config", lambda *_: {"ok": True})
    assert dispatcher._runtime_config("broken") is None

    def _raise_runtime_config(*_args, **_kwargs):
        raise ValueError("bad runtime config")

    monkeypatch.setattr(dispatcher._registry, "runtime_config", _raise_runtime_config)
    assert dispatcher._runtime_config("openai") is None
    warning.assert_called()

    monkeypatch.setattr(dispatcher._registry, "runtime_config", lambda _canonical_id, raw: raw)
    assert dispatcher._runtime_config("openai") == dispatcher._configs["openai"]

    dispatcher.update_backend_endpoint("openai", "chat", "https://new-backend.example.com")
    assert (
        dispatcher._configs["openai"]["backends"][0]["endpoint"]
        == "https://new-backend.example.com"
    )
    assert os.environ["OPENAI_BACKEND_ENDPOINT"] == "https://new-backend.example.com"

    dispatcher.update_provider_endpoint("openai", "https://new.example.com")
    assert dispatcher._configs["openai"]["endpoint"] == "https://new.example.com"
    assert os.environ["OPENAI_ENDPOINT"] == "https://new.example.com"

    monkeypatch.setattr(
        dispatcher_module, "_load_provider_toml", lambda logger: {"providers": True}
    )
    monkeypatch.setattr(
        dispatcher_module,
        "_load_toml_providers",
        lambda _toml, logger: {"openai": {"endpoint": "https://reload.example.com"}},
    )
    monkeypatch.setattr(dispatcher_module, "_load_aliases", lambda _toml: {"google": "gemini"})
    monkeypatch.setattr(
        dispatcher_module,
        "_load_model_aliases",
        lambda _toml: ({"claude-haiku": ("anthropic", "claude-3-5-haiku-latest")}, []),
    )
    monkeypatch.setattr(dispatcher_module, "_load_visible_providers", lambda _toml: ["openai"])
    validate_mock = MagicMock()
    monkeypatch.setattr(dispatcher_module, "validate_model_alias_targets", validate_mock)

    dispatcher_module.reload_provider_catalog()
    assert dispatcher_module._PROVIDER_CONFIGS == {
        "openai": {"endpoint": "https://reload.example.com"}
    }
    validate_mock.assert_called_once()
    assert dispatcher_module.canonical_provider_id(None) is None
    assert dispatcher_module.canonical_provider_id("   ") is None

    start_background_tasks = MagicMock()
    monkeypatch.setattr(dispatcher, "start_background_tasks", start_background_tasks)
    monkeypatch.setattr(dispatcher_module, "reload_provider_catalog", lambda: None)
    dispatcher.reload_config()
    start_background_tasks.assert_called_once()

    dispatcher_module._provider_toml = original_provider_toml
    dispatcher_module._PROVIDER_CONFIGS = original_provider_configs
    dispatcher_module._PROVIDER_ALIASES = original_provider_aliases
    dispatcher_module._MODEL_ALIASES = original_model_aliases
    dispatcher_module._MODEL_ALIAS_PATTERNS = original_model_alias_patterns
    dispatcher_module._VISIBLE_PROVIDER_IDS = original_visible_provider_ids


@pytest.mark.asyncio
async def test_dispatcher_routes_model_alias_to_matching_provider(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    dispatcher = ProviderDispatcher()
    anthropic = dispatcher.get_provider("anthropic")

    async def fake_invoke(messages=None, model=None, **kwargs):
        _ = messages, kwargs
        await asyncio.sleep(0)
        return ProviderResult(
            ok=True,
            text="hi",
            provider="anthropic",
            model=model or "",
            usage={"input_tokens": 1, "output_tokens": 1},
            cost_usd=0.0,
            latency_ms=1.0,
        )

    monkeypatch.setattr(anthropic, "invoke", fake_invoke)

    result = await dispatcher.dispatch(
        pid=None,
        model="claude-haiku",
        payload={"messages": [{"role": "user", "content": "hello"}]},
    )

    assert result["ok"] is True
    assert result["provider"] == "anthropic"
    assert result["model"] == "claude-3-5-haiku-latest"


@pytest.mark.asyncio
async def test_dispatcher_routes_wildcard_model_alias(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        dispatcher_module,
        "_MODEL_ALIAS_PATTERNS",
        [(re.compile(r"^gpt-mini-(.+)$"), "openai", "gpt-4o-mini-{1}")],
    )

    dispatcher = ProviderDispatcher()
    openai = dispatcher.get_provider("openai")

    async def fake_invoke(messages=None, model=None, **kwargs):
        _ = messages, kwargs
        await asyncio.sleep(0)
        return ProviderResult(
            ok=True,
            text="ok",
            provider="openai",
            model=model or "",
            latency_ms=1.0,
        )

    monkeypatch.setattr(openai, "invoke", fake_invoke)

    result = await dispatcher.dispatch(
        pid=None,
        model="gpt-mini-coder",
        payload={"messages": [{"role": "user", "content": "hello"}]},
    )

    assert result["ok"] is True
    assert result["provider"] == "openai"
    assert result["model"] == "gpt-4o-mini-coder"
