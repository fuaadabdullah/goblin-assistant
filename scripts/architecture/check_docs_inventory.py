#!/usr/bin/env python3
"""Validate the machine-readable docs inventory against the docs tree."""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_ROOT = REPO_ROOT / "docs"
DOCUMENTATION_MAP = DOCS_ROOT / "architecture" / "documentation-map.json"


@dataclass(frozen=True)
class InventoryEntry:
    path: str | None
    path_prefix: str | None
    classification: str
    allow: tuple[str, ...]
    purpose: str
    owner: str
    audience: tuple[str, ...]
    generation: str
    review_cadence: str

    @property
    def label(self) -> str:
        return self.path or self.path_prefix or "<unknown>"


def load_inventory() -> list[InventoryEntry]:
    data = json.loads(DOCUMENTATION_MAP.read_text(encoding="utf-8"))
    entries = []
    for raw in data["entries"]:
        entries.append(
            InventoryEntry(
                path=raw.get("path"),
                path_prefix=raw.get("path_prefix"),
                classification=raw["classification"],
                allow=tuple(raw.get("allow", ())),
                purpose=raw["purpose"],
                owner=raw["owner"],
                audience=tuple(raw.get("audience", ())),
                generation=raw["generation"],
                review_cadence=raw["review_cadence"],
            )
        )
    return entries


def classify_path(entries: Iterable[InventoryEntry], path: str) -> list[InventoryEntry]:
    exact_matches: list[InventoryEntry] = []
    prefix_matches: list[InventoryEntry] = []
    for entry in entries:
        if entry.path and path == entry.path:
            exact_matches.append(entry)
        elif entry.path_prefix and path.startswith(entry.path_prefix):
            prefix_matches.append(entry)
    return exact_matches or prefix_matches


def main() -> int:
    if not DOCUMENTATION_MAP.exists():
        print(f"Missing inventory map: {DOCUMENTATION_MAP.relative_to(REPO_ROOT)}", file=sys.stderr)
        return 2

    entries = load_inventory()
    violations: list[str] = []
    counts = Counter()
    seen = defaultdict(list)

    for path in sorted(DOCS_ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(REPO_ROOT).as_posix()
        matches = classify_path(entries, rel)

        if not matches:
            violations.append(f"{rel}: orphaned doc not covered by documentation-map.json")
            continue

        if len(matches) > 1:
            labels = ", ".join(entry.label for entry in matches)
            violations.append(f"{rel}: matched multiple inventory entries ({labels})")
            continue

        entry = matches[0]
        file_classification = "generated" if rel.endswith(".generated.md") else entry.classification
        counts[file_classification] += 1
        seen[entry.label].append(rel)

        if entry.classification == "compatibility-stub":
            allowed = set(entry.allow)
            if path.name not in allowed:
                violations.append(
                    f"{rel}: compatibility stub may only contain {', '.join(sorted(allowed))}"
                )

    if violations:
        print("Documentation inventory check failed:")
        for violation in violations:
            print(f"  - {violation}")
        return 1

    print(
        "Documentation inventory check passed "
        f"(canonical={counts['canonical']}, historical={counts['historical']}, "
        f"compatibility-stub={counts['compatibility-stub']}, generated={counts['generated']})."
    )
    for label, paths in sorted(seen.items()):
        print(f"  - {label}: {len(paths)} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
