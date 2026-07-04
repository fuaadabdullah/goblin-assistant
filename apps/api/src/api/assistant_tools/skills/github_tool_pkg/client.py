from __future__ import annotations

import os
import re
from typing import Any, Dict, Optional

import httpx

_BASE = "https://api.github.com"
_TIMEOUT = 15.0
_REPO_SCOPE_ENV_VARS = ("AGENT_GITHUB_ALLOWED_REPOSITORY", "GITHUB_REPOSITORY")
_TOKEN_ENV_VARS = ("GH_TOKEN", "GITHUB_TOKEN")


def _normalize_repo(value: str) -> str:
    return (
        value.strip()
        .removeprefix("https://github.com/")
        .removeprefix("http://github.com/")
        .strip("/")
        .lower()
    )


def get_allowed_repository() -> Optional[str]:
    for env_name in _REPO_SCOPE_ENV_VARS:
        raw = os.environ.get(env_name, "").strip()
        if raw:
            return _normalize_repo(raw)
    return None


def require_repo_scope(owner: str, repo: str) -> None:
    allowed = get_allowed_repository()
    if not allowed:
        return
    requested = f"{owner}/{repo}".strip("/").lower()
    if requested != allowed:
        raise ValueError(
            f"GitHub access is scoped to {allowed}; refusing repository access for {requested}"
        )


def _validate_repo_path(path: str) -> None:
    match = re.match(r"^/repos/([^/]+)/([^/]+)(/|$)", path)
    if not match:
        return
    require_repo_scope(match.group(1), match.group(2))


def headers() -> Dict[str, str]:
    token = ""
    for env_name in _TOKEN_ENV_VARS:
        token = os.environ.get(env_name, "").strip()
        if token:
            break
    req_headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        req_headers["Authorization"] = f"Bearer {token}"
    return req_headers


async def get(path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    _validate_repo_path(path)
    async with httpx.AsyncClient(
        base_url=_BASE,
        headers=headers(),
        timeout=_TIMEOUT,
    ) as client:
        resp = await client.get(path, params=params or {})
        if not resp.is_success:
            return {
                "error": resp.json().get("message", resp.text),
                "status": resp.status_code,
            }
        return resp.json()


async def post(path: str, body: Dict[str, Any]) -> Dict[str, Any]:
    _validate_repo_path(path)
    async with httpx.AsyncClient(
        base_url=_BASE,
        headers=headers(),
        timeout=_TIMEOUT,
    ) as client:
        resp = await client.post(path, json=body)
        if not resp.is_success:
            return {
                "error": resp.json().get("message", resp.text),
                "status": resp.status_code,
            }
        return resp.json()
