from pathlib import Path

from api.providers.openai_compatible import OpenAICompatibleProvider
from api.providers.provider_config_runtime import ProviderToml
from api.providers.provider_registry import DEFAULT_PROVIDER_CLASS_MAP

REPO_ROOT = Path(__file__).resolve().parents[5]


def test_aws_bedrock_registered(monkeypatch) -> None:
    monkeypatch.delenv("AWS_BEDROCK_API_KEY", raising=False)
    cfg = ProviderToml.load(REPO_ROOT / "config" / "providers.toml")
    bedrock = cfg.providers["aws_bedrock"]

    assert DEFAULT_PROVIDER_CLASS_MAP["aws_bedrock"] is OpenAICompatibleProvider
    assert bedrock.default_model == "openai.gpt-oss-20b"
    assert "qwen.qwen3-32b" in bedrock.models
    assert bedrock.endpoint == "https://bedrock-mantle.us-east-1.api.aws/v1"
    assert bedrock.api_key_env == "AWS_BEDROCK_API_KEY"


def test_aws_bedrock_openai_compatible_contract(monkeypatch) -> None:
    monkeypatch.setenv("AWS_BEDROCK_API_KEY", "test-bedrock-key")
    cfg = ProviderToml.load(REPO_ROOT / "config" / "providers.toml")
    raw = cfg.providers["aws_bedrock"].model_dump()
    provider = OpenAICompatibleProvider("aws_bedrock", raw)

    assert provider._request_url() == "https://bedrock-mantle.us-east-1.api.aws/v1/chat/completions"
    assert provider._health_path == "/models"
    assert provider._headers()["Authorization"] == "Bearer test-bedrock-key"
