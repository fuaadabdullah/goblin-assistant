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
            timeout=10,  # the fetch is sync inside the auth path — never let it wedge requests
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


# Token-hash → (payload, token_exp) cache for the auth-API verification
# fallback, so we hit Supabase at most once per token instead of per request.
_auth_api_cache: dict = {}
_AUTH_API_CACHE_MAX = 1024

SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")


def _verify_via_auth_api(token: str) -> Optional[dict]:
    """Verify a Supabase token by asking Supabase itself (GET /auth/v1/user).

    Fallback for HS256 tokens when SUPABASE_JWT_SECRET isn't configured —
    Supabase is the source of truth regardless of signing algorithm. Results
    are cached until the token's own exp so each token costs one network call.
    """
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        return None

    import hashlib
    import time as _time

    key = hashlib.sha256(token.encode()).hexdigest()
    cached = _auth_api_cache.get(key)
    if cached and cached[1] > _time.time():
        return cached[0]

    try:
        import httpx

        resp = httpx.get(
            f"{SUPABASE_URL}/auth/v1/user",
            headers={"Authorization": f"Bearer {token}", "apikey": SUPABASE_ANON_KEY},
            timeout=5.0,
        )
        if resp.status_code != 200:
            return None
        user = resp.json()
        unverified = jwt.decode(token, options={"verify_signature": False})
        payload = {
            "sub": user.get("id") or unverified.get("sub"),
            "email": user.get("email") or unverified.get("email"),
            "user_metadata": user.get("user_metadata") or {},
            "aud": "authenticated",
            "exp": unverified.get("exp"),
        }
        if len(_auth_api_cache) >= _AUTH_API_CACHE_MAX:
            _auth_api_cache.clear()
        _auth_api_cache[key] = (payload, float(unverified.get("exp") or _time.time() + 300))
        return payload
    except Exception:  # network call — never raise into the auth path
        return None


def verify_supabase_token(token: str) -> Optional[dict]:
    """Verify a Supabase-issued JWT.

    Legacy projects sign with HS256 using the shared JWT secret; projects on
    Supabase's newer signing keys use ES256/RS256 published via JWKS. Branch
    on the token header so both verify. When no local verification material
    is available, fall back to validating against the Supabase auth API.
    """
    try:
        header = jwt.get_unverified_header(token)
    except PyJWTError:
        return None

    alg = header.get("alg", "")

    if alg == "HS256":
        if not SUPABASE_JWT_SECRET:
            return _verify_via_auth_api(token)
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
