import types
from pathlib import Path

from api.services.context_assembly_service import ContextBudget
from api.services.context_assembly_service import budget_manager as bm


def _set_fake_budget_manager_file(monkeypatch, tmp_path: Path, create_providers: bool) -> Path:
    fake_file = (
        tmp_path
        / "src"
        / "api"
        / "services"
        / "context_assembly_service"
        / "budget_manager.py"
    )
    fake_file.parent.mkdir(parents=True, exist_ok=True)
    fake_file.write_text("# fake", encoding="utf-8")

    providers_path = tmp_path / "src" / "config" / "providers.toml"
    if create_providers:
        providers_path.parent.mkdir(parents=True, exist_ok=True)
        providers_path.write_text("[providers]\n", encoding="utf-8")

    monkeypatch.setattr(bm, "__file__", str(fake_file))
    return providers_path


def test_load_budget_config_reads_env(monkeypatch):
    monkeypatch.setenv("CONTEXT_WINDOW_SIZE", "9000")
    monkeypatch.setenv("SYSTEM_TOKENS", "400")
    monkeypatch.setenv("LONG_TERM_TOKENS", "500")
    monkeypatch.setenv("WORKING_MEMORY_TOKENS", "600")
    monkeypatch.setenv("SEMANTIC_RETRIEVAL_TOKENS", "700")

    budget = bm.load_budget_config()

    assert budget.total_tokens == 9000
    assert budget.system_tokens == 400
    assert budget.long_term_tokens == 500
    assert budget.working_memory_tokens == 600
    assert budget.semantic_retrieval_tokens == 700


def test_load_budget_config_invalid_env_falls_back(monkeypatch):
    monkeypatch.setenv("CONTEXT_WINDOW_SIZE", "invalid")

    budget = bm.load_budget_config()

    assert budget == ContextBudget()


def test_load_model_context_windows_missing_file(monkeypatch, tmp_path):
    _set_fake_budget_manager_file(monkeypatch, tmp_path, create_providers=False)

    windows = bm.load_model_context_windows()

    assert windows == {}


def test_load_model_context_windows_schema_unavailable(monkeypatch, tmp_path):
    _set_fake_budget_manager_file(monkeypatch, tmp_path, create_providers=True)
    monkeypatch.setattr(bm, "ProviderToml", None)

    windows = bm.load_model_context_windows()

    assert windows == {}


def test_load_model_context_windows_load_failure(monkeypatch, tmp_path):
    _set_fake_budget_manager_file(monkeypatch, tmp_path, create_providers=True)

    class _BrokenProviderToml:
        @staticmethod
        def load(_path):
            raise RuntimeError("boom")

    monkeypatch.setattr(bm, "ProviderToml", _BrokenProviderToml)

    windows = bm.load_model_context_windows()

    assert windows == {}


def test_load_model_context_windows_success(monkeypatch, tmp_path):
    providers_path = _set_fake_budget_manager_file(monkeypatch, tmp_path, create_providers=True)

    class _ProviderToml:
        @staticmethod
        def load(path):
            assert path == providers_path
            return types.SimpleNamespace(model_context_windows={"gpt-4o-mini": 128000})

    monkeypatch.setattr(bm, "ProviderToml", _ProviderToml)

    windows = bm.load_model_context_windows()

    assert windows == {"gpt-4o-mini": 128000}


def test_get_model_context_window_prefers_explicit_model_map(monkeypatch):
    monkeypatch.setattr(bm, "get_model_config", lambda _model: {"max_tokens": 999})

    value = bm.get_model_context_window(
        model="gpt-4o-mini",
        model_context_windows={"gpt-4o-mini": 64000},
        default_total=8000,
    )

    assert value == 64000


def test_get_model_context_window_uses_fallback_config(monkeypatch):
    monkeypatch.setattr(bm, "get_model_config", lambda _model: {"max_tokens": "32000"})

    value = bm.get_model_context_window(
        model="unknown",
        model_context_windows={},
        default_total=8000,
    )

    assert value == 32000


def test_get_model_context_window_invalid_fallback_uses_default(monkeypatch):
    monkeypatch.setattr(bm, "get_model_config", lambda _model: {"max_tokens": "oops"})

    value = bm.get_model_context_window(
        model="unknown",
        model_context_windows={},
        default_total=8000,
    )

    assert value == 8000


def test_get_model_context_window_no_model_uses_default():
    value = bm.get_model_context_window(
        model=None,
        model_context_windows={"gpt-4o-mini": 64000},
        default_total=8000,
    )

    assert value == 8000


def test_derive_budget_scales_up_and_respects_reserve():
    default = ContextBudget(
        total_tokens=8000,
        system_tokens=300,
        long_term_tokens=300,
        working_memory_tokens=700,
        semantic_retrieval_tokens=1200,
        ephemeral_tokens=5500,
    )

    derived = bm.derive_budget(
        default_budget=default,
        model_context_windows={"gpt-4o-mini": 16000},
        response_reserve_tokens=1000,
        model="gpt-4o-mini",
    )

    assert derived.total_tokens == 15000
    assert derived.system_tokens >= 80
    assert derived.long_term_tokens >= 80
    assert derived.working_memory_tokens >= 120
    assert derived.semantic_retrieval_tokens >= 240
    assert derived.ephemeral_tokens >= 0
    assert (
        derived.system_tokens
        + derived.long_term_tokens
        + derived.working_memory_tokens
        + derived.semantic_retrieval_tokens
        + derived.ephemeral_tokens
        == derived.total_tokens
    )


def test_derive_budget_uses_minimum_usable_tokens_floor():
    derived = bm.derive_budget(
        default_budget=ContextBudget(total_tokens=8000),
        model_context_windows={},
        response_reserve_tokens=10_000,
        max_context_tokens=600,
    )

    assert derived.total_tokens == 512


def test_derive_budget_shrink_branch_and_minimums():
    default = ContextBudget(
        total_tokens=1000,
        system_tokens=500,
        long_term_tokens=500,
        working_memory_tokens=900,
        semantic_retrieval_tokens=1200,
        ephemeral_tokens=0,
    )

    derived = bm.derive_budget(
        default_budget=default,
        model_context_windows={},
        response_reserve_tokens=0,
        max_context_tokens=1000,
    )

    fixed = (
        derived.system_tokens
        + derived.long_term_tokens
        + derived.working_memory_tokens
        + derived.semantic_retrieval_tokens
    )

    assert derived.system_tokens >= 64
    assert derived.long_term_tokens >= 64
    assert derived.working_memory_tokens >= 96
    assert derived.semantic_retrieval_tokens >= 128
    assert fixed <= derived.total_tokens
    assert derived.ephemeral_tokens == derived.total_tokens - fixed
