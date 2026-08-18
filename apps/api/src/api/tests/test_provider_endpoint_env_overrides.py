"""Provider endpoint environment override tests."""

from importlib import import_module, reload


def _dispatcher_module():
    return reload(import_module("api.providers.dispatcher"))


def _dispatcher():
    return _dispatcher_module().ProviderDispatcher()


def test_dispatcher_uses_endpoint_env_from_provider_config(monkeypatch):
    monkeypatch.setenv(
        "OPENAI_ENDPOINT",
        "https://env.example.openai.local/v1",
    )

    dispatcher = _dispatcher()
    openai_provider = dispatcher.get_provider("openai")

    assert openai_provider.endpoint == "https://env.example.openai.local/v1"


def test_dispatcher_uses_fallback_provider_endpoint_env_convention(
    monkeypatch,
):
    monkeypatch.delenv("OPENAI_ENDPOINT", raising=False)
    monkeypatch.setenv("PROVIDER_OPENAI_ENDPOINT", "https://fallback.example.openai.local/v1")

    dispatcher = _dispatcher()
    openai_provider = dispatcher.get_provider("openai")

    assert openai_provider.endpoint == ("https://fallback.example.openai.local/v1")


def test_dispatcher_reads_llamacpp_gcp_endpoint_from_env(monkeypatch):
    monkeypatch.setenv("LLAMACPP_GCP_ENDPOINT", "http://10.0.0.7:8000")

    dispatcher = _dispatcher()
    llamacpp_provider = dispatcher.get_provider("llamacpp_gcp")

    assert llamacpp_provider.endpoint == "http://10.0.0.7:8000"


def test_dispatcher_uses_huggingface_endpoint_from_env(monkeypatch):
    monkeypatch.setenv("HUGGINGFACE_ENDPOINT", "https://hf.example.local")

    dispatcher = _dispatcher()
    huggingface_provider = dispatcher.get_provider("huggingface")

    assert huggingface_provider.endpoint == "https://hf.example.local"
