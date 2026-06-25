#!/usr/bin/env python3
"""Capability ownership and provider-leakage architecture guard."""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple


REPO_ROOT = Path(__file__).resolve().parents[2]
API_ROOT = REPO_ROOT / "apps" / "api" / "src" / "api"
MANIFEST_PATH = REPO_ROOT / "apps" / "api" / "architecture-capabilities.json"


@dataclass(frozen=True)
class Violation:
    file: str
    line: int
    rule: str
    detail: str


def _run_git(args: Sequence[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def changed_api_files(base_ref: str) -> Set[Path]:
    merge_base = _run_git(["merge-base", base_ref, "HEAD"])
    diff = _run_git(["diff", "--name-only", f"{merge_base}...HEAD"])
    changed: Set[Path] = set()
    for raw in diff.splitlines():
        if not raw.endswith(".py"):
            continue
        path = (REPO_ROOT / raw).resolve()
        if path.is_file() and API_ROOT in path.parents:
            changed.add(path)
    return changed


def iter_api_files(changed_only: Optional[Set[Path]] = None) -> Iterable[Path]:
    if changed_only is not None:
        for path in sorted(changed_only):
            if "/tests/" in path.as_posix() or path.name.startswith("test_"):
                continue
            yield path
        return

    for path in sorted(API_ROOT.rglob("*.py")):
        if "/tests/" in path.as_posix() or path.name.startswith("test_"):
            continue
        yield path


def module_name(path: Path) -> str:
    rel = path.relative_to(API_ROOT.parent)
    return ".".join(rel.with_suffix("").parts)


def resolve_import(module: str, node: ast.ImportFrom) -> Optional[str]:
    if node.level == 0:
        return node.module
    parts = module.split(".")
    if node.level > len(parts):
        return None
    base = parts[: -node.level]
    if node.module:
        base.extend(node.module.split("."))
    return ".".join(base) if base else None


def parse_imports(path: Path, module: str) -> List[Tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: List[Tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom):
            resolved = resolve_import(module, node)
            if resolved:
                imports.append((node.lineno, resolved))
    return imports


def starts_with_any(value: str, prefixes: Sequence[str]) -> bool:
    return any(value.startswith(prefix) for prefix in prefixes)


def load_manifest() -> Dict[str, object]:
    with open(MANIFEST_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def capability_for_module(
    module: str, manifest: Dict[str, object]
) -> Optional[Dict[str, object]]:
    for entry in manifest.get("capabilities", []):  # type: ignore[union-attr]
        owned = entry.get("owned_modules", [])
        if starts_with_any(module, owned):
            return entry
    return None


def check_capability_boundaries(
    files: Iterable[Path], manifest: Dict[str, object]
) -> List[Violation]:
    violations: List[Violation] = []
    rules = manifest.get("rules", {})  # type: ignore[assignment]
    global_forbidden_provider_prefixes = rules.get(  # type: ignore[union-attr]
        "global_forbidden_provider_module_prefixes",
        [],
    )
    provider_import_owner_prefixes = rules.get(  # type: ignore[union-attr]
        "global_provider_import_owner_prefixes",
        rules.get("global_provider_import_allowlist", []),  # type: ignore[union-attr]
    )
    orchestration_forbidden = rules.get("orchestration_forbidden_import_prefixes", [])  # type: ignore[union-attr]

    for file_path in files:
        module = module_name(file_path)
        capability = capability_for_module(module, manifest)
        imports = parse_imports(file_path, module)
        allowed_prefixes: List[str] = []
        capability_name = ""
        if capability is not None:
            allowed_prefixes = capability.get("allowed_dependency_prefixes", [])  # type: ignore[assignment]
            capability_name = str(capability.get("name", "unknown"))

        for lineno, imported in imports:
            if not imported.startswith("api."):
                continue

            if capability is not None and not starts_with_any(
                imported, allowed_prefixes
            ):
                violations.append(
                    Violation(
                        file=str(file_path.relative_to(REPO_ROOT)),
                        line=lineno,
                        rule="capability-allowed-deps",
                        detail=(
                            f"{module} ({capability_name}) imports {imported}, "
                            "which is outside allowed dependency prefixes"
                        ),
                    )
                )

            if not starts_with_any(
                module, provider_import_owner_prefixes
            ) and starts_with_any(imported, global_forbidden_provider_prefixes):
                violations.append(
                    Violation(
                        file=str(file_path.relative_to(REPO_ROOT)),
                        line=lineno,
                        rule="provider-leakage",
                        detail=f"{module} imports concrete provider module {imported}",
                    )
                )

            if capability_name == "orchestration" and starts_with_any(
                imported, orchestration_forbidden
            ):
                violations.append(
                    Violation(
                        file=str(file_path.relative_to(REPO_ROOT)),
                        line=lineno,
                        rule="orchestration-forbidden-import",
                        detail=f"{module} imports forbidden module {imported}",
                    )
                )

    return violations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-ref", help="Check changed API files against this Git ref"
    )
    args = parser.parse_args()

    manifest = load_manifest()

    changed_only: Optional[Set[Path]] = None
    if args.base_ref:
        try:
            changed_only = changed_api_files(args.base_ref)
        except subprocess.CalledProcessError as exc:
            print(f"Failed to compute changed files: {exc}", file=sys.stderr)
            return 2
        if not changed_only:
            print("No changed API files for capability boundary checks.")
            return 0

    violations = check_capability_boundaries(iter_api_files(changed_only), manifest)
    if violations:
        print("Capability boundary check failed:")
        for violation in violations:
            print(
                f"  - {violation.file}:{violation.line} "
                f"[{violation.rule}] {violation.detail}"
            )
        return 1

    print("Capability boundary check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
