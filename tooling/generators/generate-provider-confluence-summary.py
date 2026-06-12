#!/usr/bin/env python3
"""
Generate a Confluence-friendly provider summary from config/providers.toml.

The output is a read-only view layer for Confluence pages. It must not become
the source of truth for provider config, pricing, or limits.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "shared" / "src"))

from provider_config import ProviderToml  # noqa: E402


def _provider_summary(provider_id: str, provider, visible_providers: list[str]) -> dict:
    return {
        "provider_id": provider_id,
        "display_name": provider.resolved_display_name,
        "default_model": provider.default_model,
        "tier": provider.tier,
        "capabilities": provider.capabilities,
        "active": provider.is_active,
        "visible": provider_id in visible_providers and not provider.hidden,
        "hidden": provider.hidden,
        "local_routing": provider.local_routing,
        "api_key_env": provider.api_key_env,
        "endpoint_env": provider.endpoint_env,
        "requires_env": provider.requires_env or [],
        "models": provider.models,
        "costs": {
            model_name: {
                "input_per1k": cost.input_per1k,
                "output_per1k": cost.output_per1k,
            }
            for model_name, cost in provider.costs.items()
        },
        "rate_limits": {
            model_name: {
                "requests_per_minute": rate_limit.requests_per_minute,
                "tokens_per_minute": rate_limit.tokens_per_minute,
                "concurrency": rate_limit.concurrency,
            }
            for model_name, rate_limit in provider.rate_limits.items()
        },
    }


def build_summary(config_path: Path) -> dict:
    config = ProviderToml.load(config_path)
    providers = [
        _provider_summary(provider_id, provider, config.visible_providers)
        for provider_id, provider in sorted(config.providers.items())
    ]
    return {
        "source_of_truth": "config/providers.toml",
        "generated_from": str(config_path.relative_to(REPO_ROOT)),
        "visible_providers": config.visible_providers,
        "providers": providers,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a Confluence-friendly provider summary JSON artifact."
    )
    parser.add_argument(
        "--toml-path",
        default=None,
        help="Path to providers.toml (default: config/providers.toml)",
    )
    parser.add_argument(
        "--json-path",
        default=None,
        help="Optional output file path. Default is stdout.",
    )
    args = parser.parse_args()

    config_path = (
        Path(args.toml_path)
        if args.toml_path
        else REPO_ROOT / "config" / "providers.toml"
    )
    summary = build_summary(config_path)
    rendered = json.dumps(summary, indent=2)

    if args.json_path:
        output_path = Path(args.json_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
        print(f"Wrote {output_path}")
        return 0

    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
