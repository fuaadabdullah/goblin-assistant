"""Passkey (WebAuthn) routes: /passkey/challenge, /passkey/register, /passkey/auth."""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.contracts import SuccessEnvelope
from ..passkeys import WebAuthnPasskey
from . import _runtime as _ar
from .config import ACCESS_TOKEN_EXPIRE_MINUTES
from .cookies import _set_auth_cookies
from .dependencies import _is_user_active
from .schemas import (
    PasskeyAuthRequest,
    PasskeyRegistrationRequest,
    TokenWithRefresh,
    User,
)
from .sessions import _db_create_session, create_session_id
from .tokens import create_access_token, create_refresh_token

router = APIRouter()


@router.post("/passkey/challenge")
async def get_passkey_challenge():
    """Get a challenge for passkey registration/authentication."""
    challenge = WebAuthnPasskey.generate_challenge()
    return {"challenge": challenge}


@router.post("/passkey/register")
async def register_passkey(
    request: PasskeyRegistrationRequest,
    db: AsyncSession = Depends(_ar.get_db),
):
    user_service = _ar.UserService(db)

    user_model = await user_service.get_user_by_email(request.email)
    if not user_model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await user_service.update_user(
        user_model.id,
        passkey_credential_id=request.credential_id,
        passkey_public_key=request.public_key,
    )

    return {"message": "Passkey registered successfully"}


@router.post("/passkey/auth", response_model=SuccessEnvelope[TokenWithRefresh])
async def authenticate_passkey(
    request: PasskeyAuthRequest,
    response: Response,
    db: AsyncSession = Depends(_ar.get_db),
):
    user_service = _ar.UserService(db)

    user_model = await user_service.get_user_by_email(request.email)
    if not user_model or not user_model.passkey_credential_id or not user_model.passkey_public_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Passkey not registered for this user",
        )

    if request.credential_id != user_model.passkey_credential_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credential ID"
        )

    # Simplified verification — production should run a full WebAuthn assertion check.
    try:
        if not _is_user_active(user_model.is_active):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
            )

        if not request.authenticator_data or not request.client_data_json or not request.signature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid passkey authentication data",
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

        return SuccessEnvelope(
            data=TokenWithRefresh(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                user=user,
                expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            )
        )

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Passkey authentication failed",
        )
