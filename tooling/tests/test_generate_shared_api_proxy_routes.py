from __future__ import annotations

import importlib.util
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GENERATOR_PATH = REPO_ROOT / "tooling" / "generators" / "generate-shared-api-proxy-routes.py"


def _load_generator():
    spec = importlib.util.spec_from_file_location("shared_api_proxy_generator", GENERATOR_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load generator: {GENERATOR_PATH}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_load_openapi_paths_returns_empty_when_snapshot_is_missing(tmp_path: Path) -> None:
    generator = _load_generator()

    assert generator._load_openapi_paths(tmp_path / "openapi.json") == []


def test_load_openapi_paths_normalizes_snapshot_paths(tmp_path: Path) -> None:
    openapi_path = tmp_path / "openapi.json"
    openapi_path.write_text(
        json.dumps({"paths": {"/": {}, "/api/v1/chat/": {}, "/api/v1/models": {}}}),
        encoding="utf-8",
    )

    generator = _load_generator()

    assert generator._load_openapi_paths(openapi_path) == [
        "/",
        "/api/v1/chat",
        "/api/v1/models",
    ]
