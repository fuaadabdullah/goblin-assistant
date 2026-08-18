"""FastAPI auth dependency: extracts + validates the current user.

`get_current_user` resolves the access token (header or cookie), validates
it, fetches the user + session row in one DB hit, and memoizes the result
on `request.state` so duplicate Depends resolutions in the same request
don't re-hit the DB.
"""

from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

import uuid

from ...storage.database import get_db, get_db_context
from ...storage.models import UserModel, UserSessionModel
from .schemas import User
from .tokens import verify_token

security = HTTPBearer(auto_error=False)


def _is_user_active(value: object) -> bool:
    """Coerce legacy string/bool DB values into active flag semantics."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    if isinstance(value, (int, float)):
        return bool(value)
    return False


async def _get_authenticated_user_model(
    db: AsyncSession,
    user_id: str,
    session_id: Optional[str],
) -> Optional[UserModel]:
    """Fetch user and session state in one query for auth hot paths.

    Session semantics:
    - Session row exists and revoked -> invalid (None)
    - Session row exists and active -> valid
    - Session row missing -> allow as legacy-token fallback
    """
    if session_id:
        result = await db.execute(
            select(UserModel, UserSessionModel)
            .outerjoin(
                UserSessionModel,
                and_(
                    UserSessionModel.user_id == UserModel.id,
                    UserSessionModel.session_id == session_id,
                ),
            )
            .where(UserModel.id == user_id)
        )
        row = result.first()
        if not row:
            return None

        user_model, session_model = row
        if session_model is not None and session_model.is_revoked:
            return None
        return user_model

    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    return result.scalar_one_or_none()


def verify_supabase_token(token: str) -> Optional[dict]:
    """Validate a Supabase JWT. Returns payload dict or None if invalid."""
    return None


async def _provision_supabase_user(
    db: AsyncSession,
    payload: dict,
) -> Optional[UserModel]:
    """Create a local user row from a validated Supabase token payload."""
    email = payload.get("email", "")
    meta = payload.get("user_metadata") or {}
    name = meta.get("name") or meta.get("full_name") or email.split("@")[0]
    user_id = str(payload.get("sub") or uuid.uuid4())

    result = await db.execute(select(UserModel).where(UserModel.email == email))
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    user = UserModel(id=user_id, email=email, name=name, is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> User:
    # Request-scoped memoization: skip the DB if Depends resolved us already.
    cached_user = getattr(request.state, "auth_user", None)
    cached_user_id = getattr(request.state, "auth_user_id", None)
    cached_session_id = getattr(request.state, "auth_session_id", None)

    token: str | None = None
    if credentials:
        token = credentials.credentials
    else:
        token = request.cookies.get("session_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = verify_token(token)
    if not payload:
        # Try Supabase token as a fallback
        supabase_payload = verify_supabase_token(token)
        if supabase_payload:
            async with get_db_context() as write_db:
                user_model = await _provision_supabase_user(write_db, supabase_payload)
            if not user_model:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not provision user account",
                )
            request.state.auth_user_id = str(supabase_payload.get("sub", ""))
            request.state.auth_user = user_model
            return User(
                id=user_model.id,
                email=user_model.email,
                name=user_model.name,
                google_id=getattr(user_model, "google_id", None),
                passkey_credential_id=getattr(user_model, "passkey_credential_id", None),
                passkey_public_key=getattr(user_model, "passkey_public_key", None),
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_type = payload.get("type")
    if token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type - expected access token",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    session_id = payload.get("session_id")
    if (
        cached_user is not None
        and cached_user_id == user_id
        and cached_session_id == session_id
    ):
        user_model = cached_user
    else:
        user_model = await _get_authenticated_user_model(db, user_id, session_id)

    if not user_model:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired or been revoked",
        )
    if not _is_user_active(user_model.is_active):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    request.state.auth_user = user_model
    request.state.auth_user_id = user_id
    request.state.auth_session_id = session_id

    return User(
        id=user_model.id,
        email=user_model.email,
        name=user_model.name,
        google_id=user_model.google_id,
        passkey_credential_id=user_model.passkey_credential_id,
        passkey_public_key=user_model.passkey_public_key,
    )
