"""Runtime checks for sandbox worker configuration defaults."""

from __future__ import annotations

import importlib.util
import os
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock


def test_sandbox_worker_image_default_when_env_unset() -> None:
    repo_root = Path(__file__).resolve().parents[5]
    module_path = repo_root / "apps" / "api" / "scripts" / "root-tools" / "sandbox_worker.py"
    assert module_path.exists()

    original = os.environ.pop("SANDBOX_IMAGE", None)
    docker_mod = types.ModuleType("docker")
    docker_errors_mod = types.ModuleType("docker.errors")
    docker_mod.DockerClient = MagicMock(return_value=object())  # type: ignore[attr-defined]
    docker_errors_mod.DockerException = RuntimeError  # type: ignore[attr-defined]
    docker_errors_mod.APIError = RuntimeError  # type: ignore[attr-defined]
    docker_errors_mod.ContainerError = RuntimeError  # type: ignore[attr-defined]
    redis_mod = types.ModuleType("redis")
    redis_mod.from_url = MagicMock(return_value=object())  # type: ignore[attr-defined]

    original_docker = sys.modules.get("docker")
    original_docker_errors = sys.modules.get("docker.errors")
    original_redis = sys.modules.get("redis")

    try:
        sys.modules["docker"] = docker_mod
        sys.modules["docker.errors"] = docker_errors_mod
        sys.modules["redis"] = redis_mod
        spec = importlib.util.spec_from_file_location("sandbox_worker_runtime_test", module_path)
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert module.SANDBOX_IMAGE == "goblin-assistant-sandbox:latest"
    finally:
        if original is None:
            os.environ.pop("SANDBOX_IMAGE", None)
        else:
            os.environ["SANDBOX_IMAGE"] = original
        if original_docker is None:
            sys.modules.pop("docker", None)
        else:
            sys.modules["docker"] = original_docker
        if original_docker_errors is None:
            sys.modules.pop("docker.errors", None)
        else:
            sys.modules["docker.errors"] = original_docker_errors
        if original_redis is None:
            sys.modules.pop("redis", None)
        else:
            sys.modules["redis"] = original_redis
