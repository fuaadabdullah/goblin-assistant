#!/usr/bin/env python3
"""Validate local markdown links inside the docs tree."""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote


REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_ROOT = REPO_ROOT / "docs"
ROOT_DOCS = [REPO_ROOT / "README.md", REPO_ROOT / "AGENTS.md"]

LINK_RE = re.compile(r"(?<!\!)\[[^\]]+\]\(([^)]+)\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)
ROOT_RELATIVE_PREFIXES = (
    "docs/",
    "apps/",
    "packages/",
    "scripts/",
    "tooling/",
    "README.md",
    "AGENTS.md",
    "Makefile",
    "render.yaml",
    "terraform/",
)
DOC_EXTENSIONS = {".md", ".markdown", ".mdx", ".rst", ".txt", ""}


def slugify_heading(text: str) -> str:
    slug = text.strip().lower()
    slug = re.sub(r"[^\w\- ]+", "", slug)
    slug = slug.replace(" ", "-")
    slug = re.sub(r"-+", "-", slug)
    return slug


def heading_slugs(markdown: str) -> set[str]:
    return {slugify_heading(match.group(2)) for match in HEADING_RE.finditer(markdown)}


def parse_target(raw: str) -> tuple[str, str]:
    target = raw.strip().strip('"').strip("'")
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    if "#" in target:
        path_part, anchor = target.split("#", 1)
    else:
        path_part, anchor = target, ""
    return path_part, anchor


def is_local_target(target: str) -> bool:
    return not (
        target.startswith("http://")
        or target.startswith("https://")
        or target.startswith("mailto:")
        or target.startswith("tel:")
        or target.startswith("ftp:")
        or target.startswith("data:")
        or target.startswith("//")
    )


def is_docs_target(path_part: str) -> bool:
    return Path(path_part).suffix.lower() in DOC_EXTENSIONS


def is_repo_root_docs_target(target: str) -> bool:
    return target.startswith(
        (
            "/docs/",
            "/apps/",
            "/packages/",
            "/scripts/",
            "/tooling/",
            "/README.md",
            "/AGENTS.md",
            "/Makefile",
            "/render.yaml",
            str(REPO_ROOT),
        )
    )


def resolve_target(source_dir: Path, path_part: str) -> Path:
    if path_part.startswith(str(REPO_ROOT)):
        return Path(path_part).resolve()
    if path_part.startswith("/"):
        return (REPO_ROOT / path_part.lstrip("/")).resolve()
    if path_part.startswith(ROOT_RELATIVE_PREFIXES):
        return (REPO_ROOT / path_part).resolve()
    return (source_dir / path_part).resolve()


def collect_docs_files() -> list[Path]:
    files = [path for path in DOCS_ROOT.rglob("*.md") if path.is_file()]
    files.extend(path for path in ROOT_DOCS if path.exists())
    return sorted(set(files))


def load_markdown(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def main() -> int:
    violations: list[str] = []
    headings_by_file: dict[Path, set[str]] = {}
    text_by_file: dict[Path, str] = {}

    for path in collect_docs_files():
        text = load_markdown(path)
        text_by_file[path] = text
        headings_by_file[path] = heading_slugs(text)

    for source, text in text_by_file.items():
        source_dir = source.parent
        for match in LINK_RE.finditer(text):
            raw_target = unquote(match.group(1)).strip()
            if not is_local_target(raw_target):
                if not (raw_target.startswith("/") and is_repo_root_docs_target(raw_target)):
                    continue
            path_part, anchor = parse_target(raw_target)
            if path_part and not is_docs_target(path_part):
                continue
            if not path_part and anchor:
                if anchor not in headings_by_file[source]:
                    violations.append(
                        f"{source.relative_to(REPO_ROOT)}: missing in-page anchor '#{anchor}'"
                    )
                continue

            resolved = resolve_target(source_dir, path_part) if path_part else source.resolve()
            if not resolved.exists():
                violations.append(
                    f"{source.relative_to(REPO_ROOT)}: missing link target '{raw_target}'"
                )
                continue

            if anchor:
                target_headings = headings_by_file.get(resolved)
                if target_headings is None and resolved.suffix.lower() == ".md":
                    target_headings = heading_slugs(load_markdown(resolved))
                    headings_by_file[resolved] = target_headings
                if target_headings is not None and anchor not in target_headings:
                    violations.append(
                        f"{source.relative_to(REPO_ROOT)}: missing anchor '#{anchor}' in '{raw_target}'"
                    )

    if violations:
        print("Documentation link check failed:")
        for violation in violations:
            print(f"  - {violation}")
        return 1

    print("Documentation link check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
