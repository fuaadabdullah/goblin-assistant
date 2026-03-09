"""Provider endpoint environment override tests."""

from api.providers.dispatcher import ProviderDispatcher


def test_dispatcher_uses_endpoint_env_from_provider_config(monkeypatch):
    monkeypatch.setenv("OPENAI_ENDPOINT", "https://env.example.openai.local/v1")

    dispatcher = ProviderDispatcher()
    openai_provider = dispatcher.get_provider("openai")

    assert openai_provider.endpoint == "https://env.example.openai.local/v1"


def test_dispatcher_uses_fallback_provider_endpoint_env_convention(monkeypatch):
    monkeypatch.delenv("OPENAI_ENDPOINT", raising=False)
    monkeypatch.setenv(
        "PROVIDER_OPENAI_ENDPOINT", "https://fallback.example.openai.local/v1"
    )

    dispatcher = ProviderDispatcher()
    openai_provider = dispatcher.get_provider("openai")

    assert openai_provider.endpoint == "https://fallback.example.openai.local/v1"


def test_dispatcher_reads_kamatera_llamacpp_endpoint_from_env(monkeypatch):
    monkeypatch.setenv(
        "KAMATERA_LLAMACPP_ENDPOINT", "http://10.0.0.7:8000"
    )

    dispatcher = ProviderDispatcher()
    llamacpp_provider = dispatcher.get_provider("llamacpp_kamatera")

    assert llamacpp_provider.endpoint == "http://10.0.0.7:8000"
