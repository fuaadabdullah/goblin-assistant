"""JWT access/refresh token issuance and verification."""

import os
from datetime import datetime, timedelta
from typing import Dict, Optional

import jwt
from jwt import PyJWTError

from .config import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, REFRESH_TOKEN_EXPIRE_DAYS, SECRET_KEY

# Supabase configuration
SUPABASE_URL: Optional[str] = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY: Optional[str] = os.environ.get("SUPABASE_ANON_KEY")
SUPABASE_JWT_SECRET: Optional[str] = os.environ.get("SUPABASE_JWT_SECRET")

try:
    from jwt import PyJWKClient
except ImportError:
    PyJWKClient = None  # type: ignore

_jwks_client = None
_auth_api_cache: Dict[str, dict] = {}


def _get_jwks_client():
    global _jwks_client
    if _jwks_client is None:
        url = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
        _jwks_client = PyJWKClient(url, cache_keys=True, lifespan=300, timeout=10)
    return _jwks_client


def _verify_via_auth_api(token: str) -> Optional[dict]:
    if token in _auth_api_cache:
        return _auth_api_cache[token]
    try:
        import httpx
        resp = httpx.get(
            f"{SUPABASE_URL}/auth/v1/user",
            headers={
                "Authorization": f"Bearer {token}",
                "apikey": SUPABASE_ANON_KEY or "",
            },
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        payload: dict = {
            "sub": data.get("id", ""),
            "email": data.get("email", ""),
            "user_metadata": data.get("user_metadata", {}),
        }
        _auth_api_cache[token] = payload
        return payload
    except Exception:
        return None


def verify_supabase_token(token: str) -> Optional[dict]:
    try:
        if SUPABASE_JWT_SECRET:
            return jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
            )
        header = jwt.get_unverified_header(token)
        alg = header.get("alg", "")
        if alg == "HS256":
            return _verify_via_auth_api(token)
        if alg in ("RS256", "ES256"):
            client = _get_jwks_client()
            signing_key = client.get_signing_key_from_jwt(token)
            return jwt.decode(
                token,
                signing_key.key,
                algorithms=[alg],
                audience="authenticated",
            )
        return None
    except Exception:
        return None


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
