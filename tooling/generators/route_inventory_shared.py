"""Shared helpers for the API route manifest and inventory generators."""

from __future__ import annotations

import sys
from pathlib import Path

METHOD_ORDER: dict[str, int] = {
    "DELETE": 0,
    "GET": 1,
    "HEAD": 2,
    "OPTIONS": 3,
    "PATCH": 4,
    "POST": 5,
    "PUT": 6,
}

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "shared" / "src"))

from api_routes import API_V1_PREFIX  # noqa: E402


def normalize_text(value: object, fallback: str = "-") -> str:
    if isinstance(value, str) and value.strip():
        return " ".join(value.split())
    return fallback


def normalize_tags(tags: object) -> tuple[str, ...]:
    if not isinstance(tags, list):
        return ()
    return tuple(str(tag) for tag in tags if str(tag).strip())


def strip_version_prefix(path: str) -> str:
    if path == API_V1_PREFIX:
        return "/"
    if path.startswith(f"{API_V1_PREFIX}/"):
        stripped = path[len(API_V1_PREFIX) :]
        return stripped if stripped else "/"
    return path


def group_for_path(path: str) -> str:
    parts = [segment for segment in path.split("/") if segment]
    if not parts:
        return "/"
    if parts[0] == "api" and len(parts) > 1:
        if parts[1] == "v1":
            return "/api/v1"
        return f"/api/{parts[1]}"
    return f"/{parts[0]}"


def method_sort_key(method: str) -> int:
    return METHOD_ORDER.get(method.upper(), len(METHOD_ORDER))
