from __future__ import annotations

from pathlib import Path

import scripts.architecture.check_docs_links as docs_links


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_docs_link_check_passes_for_existing_targets(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    _write(root / "README.md", "# Root\nSee [Docs](/docs/README.md).\n")
    _write(root / "AGENTS.md", "# Agents\n")
    _write(root / "docs/README.md", "# Docs\nSee [Architecture](architecture/README.md).\n")
    _write(root / "docs/architecture/README.md", "# Architecture\n## Overview\n")
    _write(root / "docs/architecture/guide.md", f"# Guide\nSee [Root README]({root / 'README.md'}).\n")

    monkeypatch.setattr(docs_links, "REPO_ROOT", root)
    monkeypatch.setattr(docs_links, "DOCS_ROOT", root / "docs")
    monkeypatch.setattr(docs_links, "ROOT_DOCS", [root / "README.md", root / "AGENTS.md"])

    assert docs_links.main() == 0


def test_docs_link_check_flags_missing_target_and_anchor(tmp_path, monkeypatch, capsys):
    root = tmp_path / "repo"
    _write(root / "README.md", "# Root\nSee [Missing](docs/missing.md).\n")
    _write(root / "AGENTS.md", "# Agents\n")
    _write(root / "docs/README.md", "# Docs\nSee [Missing anchor](architecture/README.md#missing).\n")
    _write(root / "docs/architecture/README.md", "# Architecture\n## Overview\n")

    monkeypatch.setattr(docs_links, "REPO_ROOT", root)
    monkeypatch.setattr(docs_links, "DOCS_ROOT", root / "docs")
    monkeypatch.setattr(docs_links, "ROOT_DOCS", [root / "README.md", root / "AGENTS.md"])

    assert docs_links.main() == 1
    output = capsys.readouterr().out
    assert "missing link target" in output
    assert "missing anchor" in output
