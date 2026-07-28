from __future__ import annotations

import json
from pathlib import Path

import scripts.architecture.check_docs_inventory as docs_inventory


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _write_inventory(root: Path) -> Path:
    inventory = {
        "version": 1,
        "entries": [
            {
                "path": "docs/README.md",
                "classification": "canonical",
                "purpose": "Docs index",
                "owner": "Docs",
                "audience": ["All contributors"],
                "generation": "handwritten",
                "review_cadence": "On change",
            },
            {
                "path": "docs/architecture/DOCUMENTATION_COVERAGE.md",
                "classification": "generated",
                "purpose": "Coverage",
                "owner": "Docs",
                "audience": ["Engineers"],
                "generation": "generated",
                "review_cadence": "On change",
            },
            {
                "path_prefix": "docs/architecture/",
                "classification": "canonical",
                "purpose": "Architecture",
                "owner": "Docs",
                "audience": ["Engineers"],
                "generation": "handwritten",
                "review_cadence": "On change",
            },
            {
                "path_prefix": "docs/adr/",
                "classification": "compatibility-stub",
                "allow": ["README.md"],
                "purpose": "Legacy ADR entrypoint",
                "owner": "Docs",
                "audience": ["Legacy links only"],
                "generation": "stub",
                "review_cadence": "Never expand",
            },
        ],
    }
    path = root / "docs" / "architecture" / "documentation-map.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(inventory), encoding="utf-8")
    return path


def test_inventory_check_passes_for_covered_tree(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    _write(root / "docs/README.md", "# Docs\n")
    _write(root / "docs/architecture/guide.md", "# Guide\n")
    _write(root / "docs/architecture/nested/generated.generated.md", "# Generated\n")
    _write(root / "docs/architecture/DOCUMENTATION_COVERAGE.md", "# Coverage\n")
    _write(root / "docs/adr/README.md", "# Compatibility\n")
    inventory_path = _write_inventory(root)

    monkeypatch.setattr(docs_inventory, "REPO_ROOT", root)
    monkeypatch.setattr(docs_inventory, "DOCS_ROOT", root / "docs")
    monkeypatch.setattr(docs_inventory, "DOCUMENTATION_MAP", inventory_path)

    assert docs_inventory.main() == 0


def test_inventory_check_flags_orphans_and_stub_leaks(tmp_path, monkeypatch, capsys):
    root = tmp_path / "repo"
    _write(root / "docs/README.md", "# Docs\n")
    _write(root / "docs/architecture/guide.md", "# Guide\n")
    _write(root / "docs/adr/README.md", "# Compatibility\n")
    _write(root / "docs/adr/extra.md", "# Leak\n")
    _write(root / "docs/misc/notes.md", "# Orphan\n")
    inventory_path = _write_inventory(root)

    monkeypatch.setattr(docs_inventory, "REPO_ROOT", root)
    monkeypatch.setattr(docs_inventory, "DOCS_ROOT", root / "docs")
    monkeypatch.setattr(docs_inventory, "DOCUMENTATION_MAP", inventory_path)

    assert docs_inventory.main() == 1
    output = capsys.readouterr().out
    assert "docs/adr/extra.md" in output
    assert "docs/misc/notes.md" in output
