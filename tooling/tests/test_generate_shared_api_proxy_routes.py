from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "tooling" / "generators" / "generate-shared-api-proxy-routes.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("generate_shared_api_proxy_routes", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load script module from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_load_available_paths_includes_manifest_alias_fields_and_openapi_paths(
    tmp_path: Path,
) -> None:
    module = _load_module()
    manifest_path = tmp_path / "routes.json"
    openapi_path = tmp_path / "openapi.json"

    manifest_path.write_text(
        json.dumps(
            {
                "routes": [
                    {
                        "path": "/api/v1/account/profile",
                        "canonical_path": "/api/v1/account/profile",
                        "replacement_path": "/api/v1/account/settings",
                        "compatibility_aliases": ["/account/profile"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    openapi_path.write_text(
        json.dumps({"paths": {"/api/v1/account/preferences": {}, "/api/v1/auth/login": {}}}),
        encoding="utf-8",
    )

    module.MANIFEST_PATH = manifest_path
    module.OPENAPI_PATH = openapi_path

    assert module._load_available_paths() == [
        "/api/v1/account/profile",
        "/api/v1/account/settings",
        "/account/profile",
        "/api/v1/account/preferences",
        "/api/v1/auth/login",
    ]


def test_validate_backend_targets_accepts_openapi_fallback(tmp_path: Path) -> None:
    module = _load_module()
    manifest_path = tmp_path / "routes.json"
    openapi_path = tmp_path / "openapi.json"

    manifest_path.write_text(json.dumps({"routes": [{"logical_path": "/account/profile"}]}), encoding="utf-8")
    openapi_path.write_text(
        json.dumps({"paths": {"/api/v1/account/profile": {"get": {}}}}),
        encoding="utf-8",
    )

    module.MANIFEST_PATH = manifest_path
    module.OPENAPI_PATH = openapi_path

    proxy_module = SimpleNamespace(
        PROXY_ROUTES=(SimpleNamespace(frontend_prefix="/api/account", backend_prefix="/api/v1/account"),),
        EXPLICIT_FRONTEND_PATHS=(),
    )

    module._validate_backend_targets(proxy_module, module._load_available_paths())
