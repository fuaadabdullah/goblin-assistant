"""Standard-library helpers shared by the live dogfooding smoke scripts."""

from __future__ import annotations

import json
import secrets
import time
import urllib.error
import urllib.request
from typing import Any


class SmokeFailure(RuntimeError):
    """A failed smoke-test assertion with a user-actionable message."""


def request_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    access_token: str | None = None,
    timeout: float = 30,
) -> tuple[int, dict[str, Any]]:
    headers = {"Accept": "application/json", "User-Agent": "goblin-dogfood-smoke/1"}
    body = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode("utf-8")
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"

    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
            raw_body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as error:
        status = error.code
        raw_body = error.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as error:
        raise SmokeFailure(f"Unable to reach {url}: {error.reason}") from error

    if not raw_body.strip():
        return status, {}
    try:
        parsed = json.loads(raw_body)
    except json.JSONDecodeError as error:
        raise SmokeFailure(
            f"{url} returned non-JSON content (HTTP {status})"
        ) from error
    if not isinstance(parsed, dict):
        raise SmokeFailure(f"{url} returned an unexpected JSON shape (HTTP {status})")
    return status, parsed


def require_success(
    label: str,
    response: tuple[int, dict[str, Any]],
) -> dict[str, Any]:
    status, body = response
    if status < 200 or status >= 300:
        detail = body.get("detail") or body.get("error") or body
        raise SmokeFailure(f"{label} failed (HTTP {status}): {detail}")
    return body


def fetch_csrf(api_base_url: str) -> str:
    body = require_success(
        "CSRF token request",
        request_json(f"{api_base_url}/auth/csrf-token"),
    )
    token = body.get("csrf_token")
    if not isinstance(token, str) or not token:
        raise SmokeFailure("CSRF endpoint returned no csrf_token")
    return token


def unique_credentials() -> tuple[str, str]:
    unique = f"{int(time.time())}-{secrets.token_hex(4)}"
    return f"dogfood-smoke-{unique}@example.com", f"Dogfood!{secrets.token_urlsafe(18)}"


def register_user(api_base_url: str, email: str, password: str) -> dict[str, Any]:
    body = require_success(
        "Register",
        request_json(
            f"{api_base_url}/auth/register",
            method="POST",
            payload={
                "email": email,
                "password": password,
                "name": "Dogfood Smoke User",
                "csrf_token": fetch_csrf(api_base_url),
            },
        ),
    )
    data = body.get("data")
    if not isinstance(data, dict) or not isinstance(data.get("access_token"), str):
        raise SmokeFailure("Register response did not include data.access_token")
    return data


def login_user(api_base_url: str, email: str, password: str) -> dict[str, Any]:
    body = require_success(
        "Login",
        request_json(
            f"{api_base_url}/auth/login",
            method="POST",
            payload={
                "email": email,
                "password": password,
                "csrf_token": fetch_csrf(api_base_url),
            },
        ),
    )
    data = body.get("data")
    if not isinstance(data, dict) or not isinstance(data.get("access_token"), str):
        raise SmokeFailure("Login response did not include data.access_token")
    return data
