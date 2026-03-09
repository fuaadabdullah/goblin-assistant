"""
Sentry privacy hooks for Goblin Assistant.

These callbacks enforce payload minimization before data leaves the service.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional

from .sanitization import mask_sensitive

SENSITIVE_HEADERS = {
    "authorization",
    "proxy-authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "x-auth-token",
}


def _mask_headers(headers: Any) -> Any:
    if not isinstance(headers, dict):
        return headers

    masked = {}
    for key, value in headers.items():
        if str(key).lower() in SENSITIVE_HEADERS:
            masked[key] = "[REDACTED]"
        else:
            masked[key] = value
    return masked


def _sanitize_request(request: Dict[str, Any]) -> Dict[str, Any]:
    sanitized_request = deepcopy(request)

    # Remove or redact fields that can carry sensitive user data.
    if "data" in sanitized_request:
        sanitized_request["data"] = mask_sensitive(sanitized_request["data"])

    if "headers" in sanitized_request:
        sanitized_request["headers"] = _mask_headers(sanitized_request["headers"])

    if "cookies" in sanitized_request:
        sanitized_request["cookies"] = "[REDACTED]"

    return sanitized_request


def _sanitize_user(user: Dict[str, Any]) -> Dict[str, Any]:
    sanitized_user = dict(user)
    for field in ("email", "ip_address", "username", "name"):
        sanitized_user.pop(field, None)
    return mask_sensitive(sanitized_user)


def _sanitize_breadcrumb_values(values: Any) -> Any:
    if not isinstance(values, list):
        return values

    sanitized_values = []
    for crumb in values:
        if isinstance(crumb, dict):
            crumb_copy = dict(crumb)
            if "data" in crumb_copy:
                crumb_copy["data"] = mask_sensitive(crumb_copy["data"])
            sanitized_values.append(crumb_copy)
        else:
            sanitized_values.append(crumb)

    return sanitized_values


def sentry_before_send(
    event: Dict[str, Any], hint: Optional[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """Scrub Sentry events before they are transmitted."""
    _ = hint
    sanitized_event = deepcopy(event)

    if "request" in sanitized_event and isinstance(sanitized_event["request"], dict):
        sanitized_event["request"] = _sanitize_request(sanitized_event["request"])

    if "user" in sanitized_event and isinstance(sanitized_event["user"], dict):
        sanitized_event["user"] = _sanitize_user(sanitized_event["user"])

    for key in ("extra", "contexts", "tags"):
        if key in sanitized_event:
            sanitized_event[key] = mask_sensitive(sanitized_event[key])

    if "breadcrumbs" in sanitized_event and isinstance(
        sanitized_event["breadcrumbs"], dict
    ):
        values = sanitized_event["breadcrumbs"].get("values")
        sanitized_event["breadcrumbs"]["values"] = _sanitize_breadcrumb_values(values)

    return sanitized_event


def sentry_before_breadcrumb(
    breadcrumb: Dict[str, Any], hint: Optional[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """Scrub breadcrumb payloads before they are attached to events."""
    _ = hint
    sanitized = deepcopy(breadcrumb)

    if "data" in sanitized:
        sanitized["data"] = mask_sensitive(sanitized["data"])

    if "message" in sanitized and isinstance(sanitized["message"], str):
        sanitized["message"] = mask_sensitive(sanitized["message"])

    return sanitized
