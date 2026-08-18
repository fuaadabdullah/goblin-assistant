"""Runtime checks for sandbox worker configuration defaults."""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
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


def test_start_worker_container_hardening_defaults() -> None:
    repo_root = Path(__file__).resolve().parents[5]
    module_path = repo_root / "scripts" / "ops" / "start_worker.py"
    assert module_path.exists()

    docker_mod = types.ModuleType("docker")
    docker_errors_mod = types.ModuleType("docker.errors")
    rq_mod = types.ModuleType("rq")
    redis_mod = types.ModuleType("redis")

    fake_container = MagicMock(id="container-123")
    fake_container.wait.return_value = {"StatusCode": 0}
    fake_container.logs.return_value = b"ok\n"

    fake_docker_client = MagicMock()
    fake_docker_client.containers.run.return_value = fake_container
    docker_mod.DockerClient = MagicMock(return_value=fake_docker_client)  # type: ignore[attr-defined]
    docker_errors_mod.DockerException = RuntimeError  # type: ignore[attr-defined]
    rq_mod.Worker = MagicMock(return_value=MagicMock(work=MagicMock()))  # type: ignore[attr-defined]
    rq_mod.Queue = MagicMock(return_value=MagicMock())  # type: ignore[attr-defined]
    fake_redis = MagicMock()
    redis_mod.from_url = MagicMock(return_value=fake_redis)  # type: ignore[attr-defined]

    original_docker = sys.modules.get("docker")
    original_docker_errors = sys.modules.get("docker.errors")
    original_rq = sys.modules.get("rq")
    original_redis = sys.modules.get("redis")
    # Ensure cosign verification is skipped (key path unset = skip + return True)
    original_cosign_key = os.environ.pop("COSIGN_PUBLIC_KEY_PATH", None)

    try:
        sys.modules["docker"] = docker_mod
        sys.modules["docker.errors"] = docker_errors_mod
        sys.modules["rq"] = rq_mod
        sys.modules["redis"] = redis_mod
        spec = importlib.util.spec_from_file_location("start_worker_runtime_test", module_path)
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as job_dir:
            (Path(job_dir) / "main.py").write_text("print('ok')", encoding="utf-8")
            module.run_job("job-1", "python", 10, "", job_dir)

        container_config = fake_docker_client.containers.run.call_args.kwargs
        assert container_config["network_disabled"] is True
        assert container_config["mem_limit"] == "256m"
        assert container_config["memswap_limit"] == "256m"
        assert container_config["cpu_quota"] == 25000
        assert container_config["pids_limit"] == 32
        assert container_config["read_only"] is True
        assert "/home/runner" in container_config["tmpfs"]
        assert container_config["volumes"][job_dir]["mode"] == "ro"
        assert "no-new-privileges" in container_config["security_opt"]
    finally:
        if original_cosign_key is not None:
            os.environ["COSIGN_PUBLIC_KEY_PATH"] = original_cosign_key
        if original_docker is None:
            sys.modules.pop("docker", None)
        else:
            sys.modules["docker"] = original_docker
        if original_docker_errors is None:
            sys.modules.pop("docker.errors", None)
        else:
            sys.modules["docker.errors"] = original_docker_errors
        if original_rq is None:
            sys.modules.pop("rq", None)
        else:
            sys.modules["rq"] = original_rq
        if original_redis is None:
            sys.modules.pop("redis", None)
        else:
            sys.modules["redis"] = original_redis
