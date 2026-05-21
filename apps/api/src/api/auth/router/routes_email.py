"""Email/password auth routes: /register, /login, /refresh, /logout, /me, /validate."""

from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from . import _runtime as _ar
from .config import ACCESS_TOKEN_EXPIRE_MINUTES
from .cookies import _clear_auth_cookies, _set_auth_cookies
from .dependencies import (
    _get_authenticated_user_model,
    _is_user_active,
    get_current_user,
    security,
)
from .passwords import hash_password, verify_password
from .schemas import (
    RefreshTokenRequest,
    Token,
    TokenValidationRequest,
    TokenWithRefresh,
    User,
    UserCreate,
    UserLogin,
)
from .sessions import _db_create_session, _db_revoke_session, create_session_id
from .tokens import create_access_token, create_refresh_token, verify_token

router = APIRouter()


@router.post("/register", response_model=Token)
async def register(
    user_data: UserCreate,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(_ar.get_db),
):
    client_ip = request.client.host if request.client else "unknown"

    if not await _ar.check_rate_limit(client_ip, endpoint="register"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
        )

    if not await _ar.validate_csrf_token(user_data.csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token"
        )

    user_service = _ar.UserService(db)

    existing_user = await user_service.get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    hashed_password = hash_password(user_data.password)

    user_create_data = _ar.UserCreateData(
        email=user_data.email,
        name=user_data.name,
        hashed_password=hashed_password,
    )

    user_model = await user_service.create_user(user_create_data, flush_only=True)
    if not user_model:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user",
        )

    user = User(
        id=user_model.id,
        email=user_model.email,
        name=user_model.name,
    )

    # Single atomic commit for user + session.
    session_id = create_session_id(user_model.id)
    await _db_create_session(session_id, user_model.id, db, skip_commit=True)
    await db.commit()
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_model.id},
        expires_delta=access_token_expires,
        scopes=["user"],
        session_id=session_id,
    )
    refresh_token = create_refresh_token(user_model.id, session_id)

    _set_auth_cookies(response, access_token, refresh_token)

    return TokenWithRefresh(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=user,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/login", response_model=TokenWithRefresh)
async def login(
    user_data: UserLogin,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(_ar.get_db),
):
    client_ip = request.client.host if request.client else "unknown"

    if not await _ar.check_rate_limit(client_ip, endpoint="login"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
        )

    if not await _ar.validate_csrf_token(user_data.csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token"
        )

    user_service = _ar.UserService(db)

    user_model = await user_service.get_user_by_email(user_data.email)
    if not user_model:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )

    if not user_model.hashed_password or not verify_password(
        user_data.password, user_model.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )
    if not _is_user_active(user_model.is_active):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    await user_service.update_user_last_login(user_model.id)

    user = User(
        id=user_model.id,
        email=user_model.email,
        name=user_model.name,
        google_id=user_model.google_id,
        passkey_credential_id=user_model.passkey_credential_id,
        passkey_public_key=user_model.passkey_public_key,
    )

    session_id = create_session_id(user_model.id)
    await _db_create_session(session_id, user_model.id, db)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_model.id},
        expires_delta=access_token_expires,
        scopes=["user"],
        session_id=session_id,
    )
    refresh_token = create_refresh_token(user_model.id, session_id)

    _set_auth_cookies(response, access_token, refresh_token)

    return TokenWithRefresh(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=user,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenWithRefresh)
async def refresh_token_endpoint(
    request: RefreshTokenRequest,
    http_request: Request,
    response: Response,
    db: AsyncSession = Depends(_ar.get_db),
):
    """Exchange refresh token for new access and refresh tokens."""
    raw_refresh = request.refresh_token or http_request.cookies.get("refresh_token")
    if not raw_refresh:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token provided",
        )
    payload = verify_token(raw_refresh)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user_id = payload.get("sub")
    session_id = payload.get("session_id")

    if not isinstance(user_id, str) or not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    if not isinstance(session_id, str) or not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired or been revoked",
        )

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

    user = User(
        id=user_model.id,
        email=user_model.email,
        name=user_model.name,
        google_id=user_model.google_id,
        passkey_credential_id=user_model.passkey_credential_id,
        passkey_public_key=user_model.passkey_public_key,
    )

    # New tokens, same session.
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_id},
        expires_delta=access_token_expires,
        scopes=["user"],
        session_id=session_id,
    )
    new_refresh_token = create_refresh_token(user_id, session_id)

    _set_auth_cookies(response, access_token, new_refresh_token)

    return TokenWithRefresh(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        user=user,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/logout")
async def logout(
    http_request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(_ar.get_db),
):
    """Logout user and revoke session."""
    token = None
    if credentials:
        token = credentials.credentials
    else:
        token = http_request.cookies.get("session_token")

    if token:
        payload = verify_token(token)
        if payload:
            session_id = payload.get("session_id")
            if session_id:
                await _db_revoke_session(session_id, db)

    _clear_auth_cookies(response)
    return {"message": "Logged out successfully"}


@router.post("/validate")
async def validate_token(
    request: TokenValidationRequest,
    db: AsyncSession = Depends(_ar.get_db),
):
    """Validate JWT token."""
    payload = verify_token(request.token)
    if not payload:
        return {"valid": False}

    user_id = payload.get("sub")
    if not user_id:
        return {"valid": False}

    user_service = _ar.UserService(db)
    user_model = await user_service.get_user_by_id(user_id)
    if not user_model:
        return {"valid": False}

    return {
        "valid": True,
        "user": {
            "id": user_model.id,
            "email": user_model.email,
            "name": user_model.name,
        },
    }
