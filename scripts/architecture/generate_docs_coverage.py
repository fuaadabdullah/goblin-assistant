#!/usr/bin/env python3
"""Generate a short docs coverage report from the inventory map."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MAP_PATH = REPO_ROOT / "docs" / "architecture" / "documentation-map.json"
OUTPUT_PATH = REPO_ROOT / "docs" / "architecture" / "DOCUMENTATION_COVERAGE.md"


def main() -> int:
    data = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    counts = Counter()
    by_prefix: dict[str, int] = defaultdict(int)

    for entry in data["entries"]:
        classification = entry["classification"]
        counts[classification] += 1
        prefix = entry.get("path_prefix") or entry.get("path") or "<unknown>"
        by_prefix[prefix] += 1

    lines = [
        "# Documentation Coverage",
        "",
        "This report is generated from `docs/architecture/documentation-map.json`.",
        "",
        "## Summary",
        "",
        f"- Canonical areas: {counts['canonical']}",
        f"- Compatibility stubs: {counts['compatibility-stub']}",
        f"- Historical areas: {counts['historical']}",
        "",
        "## Coverage Map",
        "",
        "| Area | Entries |",
        "| --- | ---: |",
    ]

    for prefix, entry_count in sorted(by_prefix.items()):
        lines.append(f"| `{prefix}` | {entry_count} |")

    lines.extend(
        [
            "",
            "## Policy Notes",
            "",
            "- `docs/decisions/` remains the canonical ADR home.",
            "- `docs/adr/` and `docs/runbooks/` are compatibility-only entrypoints.",
            "- Use `make lint-policy` to validate canonical references, inventory coverage, and docs links.",
        ]
    )

    OUTPUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Generated {OUTPUT_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
