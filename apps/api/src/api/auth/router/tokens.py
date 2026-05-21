"""JWT access/refresh token issuance and verification."""

from datetime import datetime, timedelta
from typing import Optional

import jwt
from jwt import PyJWTError

from .config import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, REFRESH_TOKEN_EXPIRE_DAYS, SECRET_KEY


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
    scopes: Optional[list] = None,
    session_id: Optional[str] = None,
):
    """Create JWT access token with optional scopes and session ID."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "type": "access",
    })

    if scopes:
        to_encode["scopes"] = scopes

    if session_id:
        to_encode["session_id"] = session_id

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: str, session_id: str) -> str:
    """Create JWT refresh token with longer expiration."""
    to_encode = {
        "sub": user_id,
        "type": "refresh",
        "session_id": session_id,
    }
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except PyJWTError:
        return None
