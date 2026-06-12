from __future__ import annotations

import json
from pathlib import Path


def test_provider_import_owner_prefixes_are_narrower_than_provider_package() -> None:
    manifest_path = Path(__file__).resolve().parents[3] / "architecture-capabilities.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rules = manifest["rules"]

    assert "global_provider_import_allowlist" not in rules
    owner_prefixes = rules["global_provider_import_owner_prefixes"]
    assert "api.providers" not in owner_prefixes
    assert "api.providers.dispatcher" in owner_prefixes
