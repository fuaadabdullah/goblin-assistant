import pytest
from api.core.router import ModelRouter


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("RAPTOR_URL", "https://raptor.example/api")
    monkeypatch.setenv("RAPTOR_API_KEY", "raptor-key")
    monkeypatch.setenv("FALLBACK_MODEL_URL", "https://llm.example/api")
    monkeypatch.setenv("FALLBACK_MODEL_KEY", "llm-key")
    yield


def test_choose_raptor_for_quick_task():
    r = ModelRouter()
    route = r.choose_model("quick_fix", {})
    assert route.model_name == "raptor"


def test_choose_fallback_for_unknown_task():
    r = ModelRouter()
    route = r.choose_model("refactor_suggestion", {})
    assert route.model_name == "fallback"
