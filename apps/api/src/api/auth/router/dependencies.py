"""FastAPI auth dependency: extracts + validates the current user.

`get_current_user` resolves the access token (header or cookie), validates
it, fetches the user + session row in one DB hit, and memoizes the result
on `request.state` so duplicate Depends resolutions in the same request
don't re-hit the DB.

Supabase tokens are accepted as a fallback: if the token fails local JWT
verification, it is re-verified against SUPABASE_JWT_SECRET. On success,
the user is looked up by email and auto-provisioned if they don't exist yet.
"""

import uuid
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...storage.database import get_db, get_readonly_db
from ...storage.models import UserModel, UserSessionModel
from .schemas import User
from .tokens import verify_supabase_token, verify_token

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
    """Fetch user and session state in one query for auth hot paths."""
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


async def _provision_supabase_user(
    db: AsyncSession,
    supabase_payload: dict,
) -> Optional[UserModel]:
    """Look up a user by Supabase sub/email, creating one if needed."""
    email = supabase_payload.get("email") or ""
    supabase_id = supabase_payload.get("sub") or ""

    if not email and not supabase_id:
        return None

    # Try by Supabase UUID first (most precise), then fall back to email.
    user_model: Optional[UserModel] = None
    if supabase_id:
        result = await db.execute(select(UserModel).where(UserModel.id == supabase_id))
        user_model = result.scalar_one_or_none()

    if user_model is None and email:
        result = await db.execute(select(UserModel).where(UserModel.email == email))
        user_model = result.scalar_one_or_none()

    if user_model is not None:
        return user_model

    # Auto-provision: create a local user record for this Supabase identity.
    new_id = supabase_id if supabase_id else str(uuid.uuid4())
    new_user = UserModel(
        id=new_id,
        email=email,
        name=supabase_payload.get("user_metadata", {}).get("name"),
        is_active=True,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


async def get_current_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_readonly_db)],
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> User:
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

    # --- Path 1: local JWT (legacy / existing Render-issued tokens) ---
    payload = verify_token(token)
    if payload:
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

    # --- Path 2: Supabase JWT ---
    supabase_payload = verify_supabase_token(token)
    if not supabase_payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Auto-provision: needs a writable session (get_readonly_db won't work here).
    user_model = None
    async for write_db in get_db():
        user_model = await _provision_supabase_user(write_db, supabase_payload)
        break

    if not user_model:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not resolve user identity",
        )

    if not _is_user_active(getattr(user_model, "is_active", True)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    request.state.auth_user = user_model
    request.state.auth_user_id = user_model.id
    request.state.auth_session_id = None

    return User(
        id=user_model.id,
        email=user_model.email,
        name=user_model.name,
        google_id=getattr(user_model, "google_id", None),
        passkey_credential_id=getattr(user_model, "passkey_credential_id", None),
        passkey_public_key=getattr(user_model, "passkey_public_key", None),
    )
