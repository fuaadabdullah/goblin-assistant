"""HttpOnly auth cookies — set and clear."""

from fastapi import Response

from .config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    COOKIE_SAMESITE,
    COOKIE_SECURE,
    REFRESH_MAX_AGE,
)


def _set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
    access_max_age: int | None = None,
) -> None:
    """Set HttpOnly auth cookies on the response."""
    response.set_cookie(
        key="session_token",
        value=access_token,
        httponly=True,
        samesite=COOKIE_SAMESITE,
        secure=COOKIE_SECURE,
        max_age=access_max_age or ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite=COOKIE_SAMESITE,
        secure=COOKIE_SECURE,
        max_age=REFRESH_MAX_AGE,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    """Clear HttpOnly auth cookies."""
    for name in ("session_token", "refresh_token"):
        response.delete_cookie(
            key=name,
            httponly=True,
            samesite=COOKIE_SAMESITE,
            secure=COOKIE_SECURE,
            path="/",
        )
