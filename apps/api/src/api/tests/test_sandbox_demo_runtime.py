"""Runtime checks for sandbox demo script auth key resolution."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest


def _load_sandbox_demo_module():
    repo_root = Path(__file__).resolve().parents[5]
    module_path = repo_root / "apps" / "api" / "scripts" / "root-tools" / "sandbox_demo.py"
    spec = importlib.util.spec_from_file_location("sandbox_demo_runtime_test", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_resolve_api_key_prefers_api_auth_key() -> None:
    module = _load_sandbox_demo_module()
    original_api_auth_key = os.environ.get("API_AUTH_KEY")
    original_sandbox_api_key = os.environ.get("SANDBOX_API_KEY")
    try:
        os.environ["API_AUTH_KEY"] = "primary-key"
        os.environ["SANDBOX_API_KEY"] = "secondary-key"
        assert module.resolve_api_key() == "primary-key"
    finally:
        if original_api_auth_key is None:
            os.environ.pop("API_AUTH_KEY", None)
        else:
            os.environ["API_AUTH_KEY"] = original_api_auth_key
        if original_sandbox_api_key is None:
            os.environ.pop("SANDBOX_API_KEY", None)
        else:
            os.environ["SANDBOX_API_KEY"] = original_sandbox_api_key


def test_resolve_api_key_uses_sandbox_api_key_fallback() -> None:
    module = _load_sandbox_demo_module()
    original_api_auth_key = os.environ.get("API_AUTH_KEY")
    original_sandbox_api_key = os.environ.get("SANDBOX_API_KEY")
    try:
        os.environ.pop("API_AUTH_KEY", None)
        os.environ["SANDBOX_API_KEY"] = "sandbox-key"
        assert module.resolve_api_key() == "sandbox-key"
    finally:
        if original_api_auth_key is None:
            os.environ.pop("API_AUTH_KEY", None)
        else:
            os.environ["API_AUTH_KEY"] = original_api_auth_key
        if original_sandbox_api_key is None:
            os.environ.pop("SANDBOX_API_KEY", None)
        else:
            os.environ["SANDBOX_API_KEY"] = original_sandbox_api_key


def test_resolve_api_key_exits_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_sandbox_demo_module()
    monkeypatch.delenv("API_AUTH_KEY", raising=False)
    monkeypatch.delenv("SANDBOX_API_KEY", raising=False)
    with pytest.raises(SystemExit) as exc:
        module.resolve_api_key()
    assert exc.value.code == 1
