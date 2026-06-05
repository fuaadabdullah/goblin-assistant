from __future__ import annotations

import importlib
from pathlib import Path
from unittest.mock import MagicMock

import pytest

dispatcher_module = importlib.import_module("api.providers.dispatcher")
from api.providers.anthropic_provider import AnthropicProvider
from api.providers.openai_compatible import OpenAICompatibleProvider
from api.providers.openai_provider import OpenAIProvider
from api.providers.provider_config_runtime import ProviderToml


def test_provider_toml_parses_nested_costs_rate_limits_and_model_budgets(tmp_path: Path) -> None:
    config_path = tmp_path / "providers.toml"
    config_path.write_text(
        """
[providers.openai]
name = "OpenAI"
endpoint = "https://api.openai.com/v1"
api_key_env = "OPENAI_API_KEY"
default_model = "gpt-4o-mini"

[providers.openai.costs]
default = { input_per1k = 0.005, output_per1k = 0.015 }
"gpt-4o-mini" = { input_per1k = 0.00015, output_per1k = 0.0006 }

[providers.openai.rate_limits]
default = { requests_per_minute = 60, tokens_per_minute = 200000, concurrency = 0 }
"gpt-4o-mini" = { requests_per_minute = 500, tokens_per_minute = 200000, concurrency = 0 }

[model_budgets]
"gpt-4o-mini" = { requests_per_minute = 1000, tokens_per_minute = 400000, concurrency = 0 }

[load_balancing]
circuit_breaker_soft_threshold = 2
circuit_breaker_hard_categories = ["auth", "billing"]
circuit_breaker_canary_percent = 0.25
""".strip(),
        encoding="utf-8",
    )

    cfg = ProviderToml.load(config_path)

    provider = cfg.get_provider("openai")
    assert provider is not None
    assert provider.costs["gpt-4o-mini"].input_per1k == pytest.approx(0.00015)
    assert provider.rate_limits["gpt-4o-mini"].requests_per_minute == 500
    assert cfg.model_budgets["gpt-4o-mini"].tokens_per_minute == 400000
    assert cfg.load_balancing.circuit_breaker_soft_threshold == 2
    assert cfg.load_balancing.circuit_breaker_hard_categories == ["auth", "billing"]
    assert cfg.load_balancing.circuit_breaker_canary_percent == pytest.approx(0.25)


def test_provider_toml_keeps_legacy_flat_cost_fields(tmp_path: Path) -> None:
    config_path = tmp_path / "providers.toml"
    config_path.write_text(
        """
[providers.openai]
name = "OpenAI"
endpoint = "https://api.openai.com/v1"
api_key_env = "OPENAI_API_KEY"
default_model = "gpt-4o-mini"
cost_input_per1k = 0.005
cost_output_per1k = 0.015
rate_limit_per_min = 60
""".strip(),
        encoding="utf-8",
    )

    cfg = ProviderToml.load(config_path)
    provider = cfg.get_provider("openai")

    assert provider is not None
    assert provider.cost_input_per1k == pytest.approx(0.005)
    assert provider.cost_output_per1k == pytest.approx(0.015)
    assert provider.rate_limit_per_min == 60


def test_validate_model_alias_targets_accepts_valid_aliases(tmp_path: Path) -> None:
    config_path = tmp_path / "providers.toml"
    config_path.write_text(
        """
[providers.openai]
name = "OpenAI"
endpoint = "https://api.openai.com/v1"
api_key_env = "OPENAI_API_KEY"
default_model = "gpt-4o-mini"
models = ["gpt-4o", "gpt-4o-mini"]

[model_aliases]
"gpt-mini" = { provider = "openai", model = "gpt-4o-mini" }
""".strip(),
        encoding="utf-8",
    )

    provider_toml = ProviderToml.load(config_path)
    logger = MagicMock()

    dispatcher_module.validate_model_alias_targets(
        provider_toml=provider_toml,
        provider_configs={
            "openai": {
                "default_model": "gpt-4o-mini",
                "models": ["gpt-4o", "gpt-4o-mini"],
                "backends": [],
            },
        },
        logger=logger,
    )

    logger.warning.assert_not_called()


def test_validate_model_alias_targets_warns_for_invalid_alias_targets(tmp_path: Path) -> None:
    config_path = tmp_path / "providers.toml"
    config_path.write_text(
        """
[providers.openai]
name = "OpenAI"
endpoint = "https://api.openai.com/v1"
api_key_env = "OPENAI_API_KEY"
default_model = "gpt-4o-mini"
models = ["gpt-4o-mini"]

[model_aliases]
"missing-provider" = { provider = "anthropic", model = "claude-3-5-haiku-latest" }
"bad-model" = { provider = "openai", model = "gpt-4.1" }
""".strip(),
        encoding="utf-8",
    )

    provider_toml = ProviderToml.load(config_path)
    logger = MagicMock()

    dispatcher_module.validate_model_alias_targets(
        provider_toml=provider_toml,
        provider_configs={
            "openai": {
                "default_model": "gpt-4o-mini",
                "models": ["gpt-4o-mini"],
                "backends": [],
            }
        },
        logger=logger,
    )

    assert logger.warning.call_count == 2
    assert {call.kwargs["alias"] for call in logger.warning.call_args_list} == {
        "missing-provider",
        "bad-model",
    }


def test_dispatcher_reload_config_refreshes_provider_pricing(monkeypatch):
    original_state = {
        "_provider_toml": dispatcher_module._provider_toml,
        "_PROVIDER_CONFIGS": dispatcher_module._PROVIDER_CONFIGS,
        "_PROVIDER_ALIASES": dispatcher_module._PROVIDER_ALIASES,
        "_MODEL_ALIASES": dispatcher_module._MODEL_ALIASES,
        "_MODEL_ALIAS_PATTERNS": dispatcher_module._MODEL_ALIAS_PATTERNS,
        "_VISIBLE_PROVIDER_IDS": dispatcher_module._VISIBLE_PROVIDER_IDS,
    }
    first = {
        "openai": {
            "name": "OpenAI",
            "endpoint": "https://api.openai.com/v1",
            "api_key_env": "OPENAI_API_KEY",
            "default_model": "gpt-4o-mini",
            "costs": {
                "gpt-4o-mini": {"input_per1k": 0.001, "output_per1k": 0.002},
            },
        }
    }
    second = {
        "openai": {
            "name": "OpenAI",
            "endpoint": "https://api.openai.com/v1",
            "api_key_env": "OPENAI_API_KEY",
            "default_model": "gpt-4o-mini",
            "costs": {
                "gpt-4o-mini": {"input_per1k": 0.01, "output_per1k": 0.02},
            },
        }
    }

    monkeypatch.setattr(dispatcher_module, "_load_provider_toml", lambda logger=None: object())
    monkeypatch.setattr(
        dispatcher_module,
        "_load_toml_providers",
        lambda _toml, logger=None: second,
    )
    monkeypatch.setattr(dispatcher_module, "_load_aliases", lambda _toml: {})
    monkeypatch.setattr(dispatcher_module, "_load_model_aliases", lambda _toml: ({}, []))
    monkeypatch.setattr(dispatcher_module, "_load_visible_providers", lambda _toml: ["openai"])
    validation_calls = []
    monkeypatch.setattr(
        dispatcher_module,
        "validate_model_alias_targets",
        lambda **kwargs: validation_calls.append(kwargs),
    )

    dispatcher = dispatcher_module.ProviderDispatcher(
        configs=first,
        class_map={"openai": OpenAIProvider},
    )

    try:
        before = dispatcher.get_provider("openai").estimate_cost(
            1000,
            1000,
            model="gpt-4o-mini",
        )
        assert before == pytest.approx(0.003)

        dispatcher.reload_config()
        assert validation_calls
        assert validation_calls[-1]["provider_configs"] == second

        after = dispatcher.get_provider("openai").estimate_cost(
            1000,
            1000,
            model="gpt-4o-mini",
        )
        assert after == pytest.approx(0.03)
    finally:
        for name, value in original_state.items():
            setattr(dispatcher_module, name, value)


def test_provider_adapters_resolve_costs_from_nested_config() -> None:
    openai = OpenAIProvider(
        "openai",
        {
            "default_model": "gpt-4o-mini",
            "costs": {
                "gpt-4o-mini": {"input_per1k": 0.001, "output_per1k": 0.002},
            },
        },
    )
    anthropic = AnthropicProvider(
        "anthropic",
        {
            "default_model": "claude-3-5-haiku-latest",
            "costs": {
                "claude-3-5-haiku-latest": {
                    "input_per1k": 0.003,
                    "output_per1k": 0.004,
                },
            },
        },
    )
    compatible = OpenAICompatibleProvider(
        "groq",
        {
            "default_model": "llama-3.3-70b-versatile",
            "endpoint": "https://example.invalid/v1",
            "costs": {
                "llama-3.3-70b-versatile": {
                    "input_per1k": 0.005,
                    "output_per1k": 0.006,
                },
            },
        },
    )

    assert openai.estimate_cost(1000, 1000, model="gpt-4o-mini") == pytest.approx(0.003)
    assert anthropic.estimate_cost(
        1000,
        1000,
        model="claude-3-5-haiku-latest",
    ) == pytest.approx(0.007)
    assert compatible.estimate_cost(
        1000,
        1000,
        model="llama-3.3-70b-versatile",
    ) == pytest.approx(0.011)
