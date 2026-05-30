#!/usr/bin/env python3
"""Export FastAPI OpenAPI schema to packages/sdk/openapi/openapi.json."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
API_SRC = REPO_ROOT / "apps" / "api" / "src"
OUTPUT_PATH = REPO_ROOT / "packages" / "sdk" / "openapi" / "openapi.json"

os.environ.setdefault("JWT_SECRET_KEY", "dev-openapi-export-secret")
sys.path.insert(0, str(API_SRC))

# Import after PYTHONPATH setup.
from api.main import app  # noqa: E402


def main() -> int:
    schema = app.openapi()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Exported OpenAPI schema to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
