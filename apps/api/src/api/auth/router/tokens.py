"""JWT access/refresh token issuance and verification."""

import os
from datetime import datetime, timedelta
from typing import Optional

import jwt
from jwt import PyJWKClient, PyJWTError

from .config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    REFRESH_TOKEN_EXPIRE_DAYS,
    SECRET_KEY,
)

SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
SUPABASE_URL = (os.getenv("SUPABASE_URL") or "").rstrip("/")

_jwks_client: Optional[PyJWKClient] = None


def _get_jwks_client() -> Optional[PyJWKClient]:
    global _jwks_client
    if _jwks_client is None and SUPABASE_URL:
        _jwks_client = PyJWKClient(
            f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json",
            cache_keys=True,
            lifespan=3600,
        )
    return _jwks_client


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

    to_encode.update(
        {
            "exp": expire,
            "type": "access",
        }
    )

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


def verify_supabase_token(token: str) -> Optional[dict]:
    """Verify a Supabase-issued JWT.

    Legacy projects sign with HS256 using the shared JWT secret; projects on
    Supabase's newer signing keys use ES256/RS256 published via JWKS. Branch
    on the token header so both verify.
    """
    try:
        header = jwt.get_unverified_header(token)
    except PyJWTError:
        return None

    alg = header.get("alg", "")

    if alg == "HS256":
        if not SUPABASE_JWT_SECRET:
            return None
        try:
            return jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
            )
        except PyJWTError:
            return None

    if alg in {"ES256", "RS256"}:
        jwks_client = _get_jwks_client()
        if jwks_client is None:
            return None
        try:
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            return jwt.decode(
                token,
                signing_key.key,
                algorithms=[alg],
                audience="authenticated",
            )
        except Exception:  # JWKS fetch is a network call; never raise into auth
            return None

    return None
