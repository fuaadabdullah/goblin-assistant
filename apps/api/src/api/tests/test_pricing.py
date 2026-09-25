"""Unit tests for api.providers.pricing — LiteLLM-first cost resolution.

resolve_model_pricing() prefers LiteLLM's upstream-maintained model cost map
over the local providers.toml table, falling back to providers.toml only when
LiteLLM doesn't recognize the model (self-hosted/custom backends). These tests
monkeypatch litellm.cost_per_token rather than relying on its real bundled
price data, so they stay deterministic across LiteLLM version bumps.
"""

from __future__ import annotations

import pytest

from api.providers import pricing


@pytest.fixture(autouse=True)
def _clear_litellm_pricing_cache():
    pricing._litellm_cost_lookup.cache_clear()
    yield
    pricing._litellm_cost_lookup.cache_clear()


def test_resolve_model_pricing_prefers_litellm_when_recognized(monkeypatch):
    import litellm

    def fake_cost_per_token(model, prompt_tokens, completion_tokens):
        assert model == "gpt-4o-mini-test"
        assert prompt_tokens == 1000
        assert completion_tokens == 1000
        return (0.00015, 0.0006)

    monkeypatch.setattr(litellm, "cost_per_token", fake_cost_per_token)

    result = pricing.resolve_model_pricing(
        "openai",
        "gpt-4o-mini-test",
        config={
            "default_model": "gpt-4o-mini-test",
            # Deliberately different from the LiteLLM values above, to prove
            # LiteLLM wins over a stale/incorrect TOML entry.
            "costs": {"gpt-4o-mini-test": {"input_per1k": 999.0, "output_per1k": 999.0}},
        },
    )

    assert result.input_per1k == pytest.approx(0.00015)
    assert result.output_per1k == pytest.approx(0.0006)


def test_resolve_model_pricing_falls_back_to_toml_when_litellm_unknown(monkeypatch):
    import litellm

    def raise_not_found(model, prompt_tokens, completion_tokens):
        raise Exception(f"model not mapped: {model}")

    monkeypatch.setattr(litellm, "cost_per_token", raise_not_found)

    result = pricing.resolve_model_pricing(
        "ollama_gcp",
        "llama3.1-self-hosted",
        config={
            "default_model": "llama3.1-self-hosted",
            "costs": {"llama3.1-self-hosted": {"input_per1k": 0.0, "output_per1k": 0.0}},
        },
    )

    assert result.input_per1k == pytest.approx(0.0)
    assert result.output_per1k == pytest.approx(0.0)


def test_litellm_cost_lookup_is_cached(monkeypatch):
    import litellm

    calls: list[str] = []

    def counting_cost_per_token(model, prompt_tokens, completion_tokens):
        calls.append(model)
        return (0.001, 0.002)

    monkeypatch.setattr(litellm, "cost_per_token", counting_cost_per_token)

    first = pricing._litellm_cost_lookup("cached-model-test")
    second = pricing._litellm_cost_lookup("cached-model-test")

    assert first == second
    assert calls == ["cached-model-test"]
