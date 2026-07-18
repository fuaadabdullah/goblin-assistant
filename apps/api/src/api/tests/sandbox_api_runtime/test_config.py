"""Config sandbox API runtime tests."""

import importlib
import os

from .conftest import sandbox_api


def test_sandbox_image_default_when_env_unset() -> None:
    expected_default = "goblin-assistant-sandbox:latest"
    original = os.environ.pop("SANDBOX_IMAGE", None)
    try:
        module = importlib.reload(sandbox_api)
        assert expected_default == module.SANDBOX_IMAGE
    finally:
        if original is None:
            os.environ.pop("SANDBOX_IMAGE", None)
        else:
            os.environ["SANDBOX_IMAGE"] = original
        importlib.reload(sandbox_api)


def test_sandbox_api_key_default_when_env_unset() -> None:
    original = os.environ.pop("API_AUTH_KEY", None)
    try:
        module = importlib.reload(sandbox_api)
        assert module.API_KEY is None
    finally:
        if original is None:
            os.environ.pop("API_AUTH_KEY", None)
        else:
            os.environ["API_AUTH_KEY"] = original
        importlib.reload(sandbox_api)


def test_sandbox_config_ignores_invalid_redis_url(monkeypatch) -> None:
    monkeypatch.setenv("REDIS_URL", "not-a-redis-url")

    from api import sandbox_config

    module = importlib.reload(sandbox_config)

    assert module.REDIS_URL == "not-a-redis-url"
    assert module._resolve_redis_url(module.REDIS_URL) == "redis://localhost:6379/0"
    assert module.r is not None
