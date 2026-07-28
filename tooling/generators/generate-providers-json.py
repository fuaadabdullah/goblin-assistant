#!/usr/bin/env python3
"""
Generate config/providers.json from the SINGLE source of truth config/providers.toml.

Usage:
    python tooling/generators/generate-providers-json.py        # writes to config/providers.json
    python tooling/generators/generate-providers-json.py --check # exit 1 if JSON is stale

Run this after editing config/providers.toml.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure we can import the shared schema
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "shared" / "src"))

from provider_config import load_provider_config  # noqa: E402


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate config/providers.json from providers.toml"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check that providers.json is up-to-date (exit 1 if not)",
    )
    parser.add_argument(
        "--toml-path",
        default=None,
        help="Path to providers.toml (default: config/providers.toml)",
    )
    parser.add_argument(
        "--json-path",
        default=None,
        help="Output path for providers.json (default: config/providers.json)",
    )
    args = parser.parse_args()

    toml_path = Path(args.toml_path) if args.toml_path else REPO_ROOT / "config" / "providers.toml"
    json_path = Path(args.json_path) if args.json_path else REPO_ROOT / "config" / "providers.json"

    # Validate & load via Pydantic schema
    cfg = load_provider_config(toml_path, use_cache=False)
    generated = cfg.as_json_serializable()

    if args.check:
        # Read existing providers.json and compare
        if not json_path.exists():
            print(f"ERROR: {json_path} does not exist. Run generate first.")
            return 1

        with open(json_path, "r") as f:
            existing = json.load(f)

        if existing != generated:
            print(f"ERROR: {json_path} is stale. Run generate-providers-json.py")
            return 1

        print(f"OK: {json_path} is up-to-date")
        return 0

    # Write
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w") as f:
        json.dump(generated, f, indent=2)
        f.write("\n")

    print(f"Generated {json_path} ({len(generated['providers'])} providers)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
