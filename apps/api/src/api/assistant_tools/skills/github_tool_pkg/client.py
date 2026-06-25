from __future__ import annotations

import os
from typing import Any, Dict, Optional

import httpx

_BASE = "https://api.github.com"
_TIMEOUT = 15.0


def headers() -> Dict[str, str]:
    token = os.environ.get("GITHUB_TOKEN", "")
    req_headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        req_headers["Authorization"] = f"Bearer {token}"
    return req_headers


async def get(path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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
