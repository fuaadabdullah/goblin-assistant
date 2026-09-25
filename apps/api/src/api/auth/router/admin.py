"""Admin authorization dependencies for sensitive platform routes."""

import os
from typing import Annotated

from fastapi import Depends, HTTPException, status

from .dependencies import get_current_user
from .schemas import User

ADMIN_EMAIL_ENV = "ADMIN_EMAILS"
ADMIN_DOMAIN_ENV = "ADMIN_DOMAINS"
PUBLIC_ADMIN_EMAIL_ENV = "NEXT_PUBLIC_ADMIN_EMAILS"
PUBLIC_ADMIN_DOMAIN_ENV = "NEXT_PUBLIC_ADMIN_DOMAINS"


def _parse_list(value: str | None) -> set[str]:
    if not value:
        return set()
    return {item.strip().lower() for item in value.split(",") if item.strip()}


def _admin_emails() -> set[str]:
    return _parse_list(os.getenv(ADMIN_EMAIL_ENV)) | _parse_list(os.getenv(PUBLIC_ADMIN_EMAIL_ENV))


def _admin_domains() -> set[str]:
    return _parse_list(os.getenv(ADMIN_DOMAIN_ENV)) | _parse_list(
        os.getenv(PUBLIC_ADMIN_DOMAIN_ENV)
    )


def is_admin_email(email: str | None) -> bool:
    """Return True when an email matches the configured admin allowlist.

    Kept public so the token-validation response can surface the same
    server-derived admin claim to the browser instead of re-deriving it from
    the server-only ADMIN_EMAILS/ADMIN_DOMAINS env vars in the client bundle.
    """
    normalized = (email or "").strip().lower()
    if not normalized:
        return False
    if normalized in _admin_emails():
        return True
    _, _, domain = normalized.partition("@")
    return bool(domain and domain in _admin_domains())


async def require_admin_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Require an authenticated user from the configured admin allowlist."""
    if is_admin_email(current_user.email):
        return current_user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin access required",
    )
