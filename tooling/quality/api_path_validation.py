"""Validate frontend API path literals against the checked-in contract manifest."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_ROOTS = (REPO_ROOT / "apps" / "web" / "app", REPO_ROOT / "apps" / "web" / "src")
MANIFEST_PATH = REPO_ROOT / "packages" / "sdk" / "openapi" / "routes.json"
PROXY_CONTRACT_PATH = REPO_ROOT / "packages" / "shared" / "src" / "api_proxy_routes.py"
VALID_EXTENSIONS = {".ts", ".tsx", ".js", ".jsx"}
IGNORED_DIRS = {".git", ".next", "coverage", "dist", "node_modules"}
IGNORED_PATH_PARTS = {"__tests__", "__mocks__", "test", "tests"}

STRING_LITERAL_RE = re.compile(r"""(?P<quote>['"`])(?P<value>[^'"`]*?/api/[^'"`]*)\1""")
TEMPLATE_EXPR_RE = re.compile(r"\$\{[^}]+\}")


@dataclass(frozen=True)
class PathFinding:
    file: Path
    line: int
    literal: str
    normalized: str


def _load_manifest_paths(manifest_path: Path = MANIFEST_PATH) -> list[str]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    routes = manifest.get("routes", [])
    if not isinstance(routes, list):
        return []

    paths: list[str] = []
    for route in routes:
        if not isinstance(route, dict):
            continue
        path = route.get("path")
        if isinstance(path, str) and path:
            paths.append(path)
    return paths


def _compile_route_pattern(route_path: str) -> re.Pattern[str]:
    normalized = route_path.rstrip("/") if route_path != "/" else "/"
    parts = []
    for segment in normalized.split("/"):
        if not segment:
            continue
        if segment == "*":
            parts.append(r"[^/]+")
            continue
        if segment.startswith("{") and segment.endswith("}"):
            token = segment[1:-1]
            if token.endswith(":path"):
                parts.append(r".+")
            else:
                parts.append(r"[^/]+")
            continue
        parts.append(re.escape(segment))

    if not parts:
        return re.compile(r"^/$")
    return re.compile(r"^/" + "/".join(parts) + r"/?$")


def _compile_proxy_prefix_pattern(frontend_prefix: str) -> re.Pattern[str]:
    normalized = frontend_prefix.rstrip("/") if frontend_prefix != "/" else "/"
    return re.compile(rf"^{re.escape(normalized)}(?:/.*)?/?$")


def _load_proxy_contract(contract_path: Path = PROXY_CONTRACT_PATH) -> tuple[list[re.Pattern[str]], list[re.Pattern[str]]]:
    spec = importlib.util.spec_from_file_location("api_proxy_routes_contract", contract_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load API proxy route contract: {contract_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    proxy_patterns = []
    for route in getattr(module, "PROXY_ROUTES", ()):
        frontend_prefix = getattr(route, "frontend_prefix", None)
        if isinstance(frontend_prefix, str) and frontend_prefix:
            proxy_patterns.append(_compile_proxy_prefix_pattern(frontend_prefix))

    explicit_patterns = []
    for path in getattr(module, "EXPLICIT_FRONTEND_PATHS", ()):
        if isinstance(path, str) and path:
            explicit_patterns.append(_compile_route_pattern(path))

    # ProxyEndpointSpec routes are allowed as exact frontend paths (no sub-paths).
    for route in getattr(module, "PROXY_ENDPOINT_ROUTES", ()):
        frontend_path = getattr(route, "frontend_path", None)
        if isinstance(frontend_path, str) and frontend_path:
            explicit_patterns.append(_compile_route_pattern(frontend_path))

    return proxy_patterns, explicit_patterns


def _normalize_literal(value: str) -> str:
    literal = value.strip()
    if "http://" in literal or "https://" in literal:
        parsed = urlparse(literal)
        literal = parsed.path or "/"
        if parsed.query:
            literal = f"{literal}?{parsed.query}"

    literal = TEMPLATE_EXPR_RE.sub("*", literal)
    api_index = literal.find("/api")
    if api_index >= 0:
        literal = literal[api_index:]
    if "?" in literal:
        literal = literal.split("?", 1)[0]
    if "#" in literal:
        literal = literal.split("#", 1)[0]
    if literal != "/" and literal.endswith("/"):
        literal = literal.rstrip("/")
    return literal


def _looks_like_api_reference(literal: str) -> bool:
    stripped = literal.strip()
    if "V1_API_PREFIX" in stripped or "V1_CHAT_PREFIX" in stripped:
        return False
    if stripped.startswith("/api/"):
        return True
    if stripped.startswith("http://") or stripped.startswith("https://"):
        parsed = urlparse(stripped)
        return parsed.path.startswith("/api/")
    if stripped.startswith("${") and "/api/" in stripped:
        return True
    return False


def _scan_frontend_paths(root: Path) -> list[PathFinding]:
    findings: list[PathFinding] = []
    if not root.exists():
        return findings

    for path in root.rglob("*"):
        if path.is_dir() or path.suffix not in VALID_EXTENSIONS:
            continue
        if any(part in IGNORED_DIRS for part in path.parts):
            continue
        if path.parts[-3:-1] == ("app", "api") or "app/api" in path.as_posix():
            continue
        if any(part in IGNORED_PATH_PARTS for part in path.parts):
            continue

        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if "/api" not in line:
                continue
            for match in STRING_LITERAL_RE.finditer(line):
                literal = match.group("value")
                if not _looks_like_api_reference(literal):
                    continue
                normalized = _normalize_literal(literal)
                if normalized in {"/api/v1", "/api/v1/"}:
                    continue
                if normalized.startswith("/api"):
                    findings.append(
                        PathFinding(
                            file=path,
                            line=line_no,
                            literal=literal,
                            normalized=normalized,
                        )
                    )
    return findings


def validate_frontend_api_paths(
    frontend_roots: tuple[Path, ...] = FRONTEND_ROOTS,
    manifest_path: Path = MANIFEST_PATH,
    proxy_contract_path: Path = PROXY_CONTRACT_PATH,
) -> list[PathFinding]:
    route_patterns = [_compile_route_pattern(path) for path in _load_manifest_paths(manifest_path)]
    proxy_patterns, explicit_patterns = _load_proxy_contract(proxy_contract_path)
    allowed_patterns = [*route_patterns, *proxy_patterns, *explicit_patterns]

    findings: list[PathFinding] = []
    for root in frontend_roots:
        findings.extend(_scan_frontend_paths(root))

    violations: list[PathFinding] = []
    for finding in findings:
        if any(pattern.match(finding.normalized) for pattern in allowed_patterns):
            continue
        violations.append(finding)
    return violations


def main() -> int:
    violations = validate_frontend_api_paths()
    if violations:
        print(
            "❌ Frontend API path validation failed. These literals do not match the checked-in contract manifest:"
        )
        for finding in violations:
            print(f"  - {finding.file.relative_to(REPO_ROOT)}:{finding.line} -> {finding.literal}")
        print(
            "Use packages/sdk/openapi/routes.json and packages/shared/src/api_proxy_routes.py as the source of truth."
        )
        return 1

    print("✅ Frontend API path validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
