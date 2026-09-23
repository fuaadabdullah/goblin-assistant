"""Passkey (WebAuthn) routes: /passkey/challenge, /passkey/register, /passkey/auth.

Backed by py_webauthn for spec-correct ceremony handling and verification.
Successful authentication mints a Supabase sign-in token hash (the session the
browser actually stores via @supabase/ssr) instead of a legacy JWT.
"""

from __future__ import annotations

import json
import secrets
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from ...core.contracts import SuccessEnvelope
from ...observability.telemetry import record_auth_event
from ...storage.cache import cache
from ...supabase_integration import SupabaseAuth
from . import _runtime as _ar
from .config import WEBAUTHN_ORIGINS, WEBAUTHN_RP_ID, WEBAUTHN_RP_NAME
from .dependencies import _is_user_active
from .schemas import (
    PasskeyAuthRequest,
    PasskeyAuthResponse,
    PasskeyChallengeRequest,
    PasskeyRegistrationRequest,
    User,
)
from .sessions import _db_create_session, create_session_id

router = APIRouter()

_CHALLENGE_CACHE_PREFIX = "auth:passkey:challenge"
_CHALLENGE_TTL_SECONDS = 300


def _challenge_cache_key(email: str) -> str:
    return f"{_CHALLENGE_CACHE_PREFIX}:{email.lower()}"


def _new_challenge() -> bytes:
    return secrets.token_bytes(32)


async def _store_challenge(email: str, challenge: bytes) -> None:
    await cache.set(
        _challenge_cache_key(email),
        {"challenge": bytes_to_base64url(challenge)},
        expire=_CHALLENGE_TTL_SECONDS,
    )


async def _consume_challenge(email: str) -> bytes | None:
    key = _challenge_cache_key(email)
    stored = await cache.get(key)
    if not isinstance(stored, dict) or not stored.get("challenge"):
        return None
    await cache.delete(key)
    return base64url_to_bytes(stored["challenge"])


def _registration_user_id(user_model: Any, email: str) -> bytes:
    user_id = getattr(user_model, "id", None)
    return (str(user_id) if user_id else email).encode("utf-8")[:64]


@router.post("/passkey/challenge")
async def get_passkey_challenge(
    request: PasskeyChallengeRequest,
    db: AsyncSession = Depends(_ar.get_db),
):
    """Return registration or authentication options for a user's email."""
    email = request.email.lower()
    user_service = _ar.UserService(db)
    user_model = await user_service.get_user_by_email(email)
    challenge = _new_challenge()
    await _store_challenge(email, challenge)

    if user_model and getattr(user_model, "passkey_credential_id", None):
        options = generate_authentication_options(
            rp_id=WEBAUTHN_RP_ID,
            challenge=challenge,
            allow_credentials=[
                PublicKeyCredentialDescriptor(
                    id=base64url_to_bytes(user_model.passkey_credential_id)
                )
            ],
            user_verification=UserVerificationRequirement.PREFERRED,
        )
    else:
        options = generate_registration_options(
            rp_id=WEBAUTHN_RP_ID,
            rp_name=WEBAUTHN_RP_NAME,
            user_name=email,
            user_id=_registration_user_id(user_model, email),
            challenge=challenge,
            authenticator_selection=AuthenticatorSelectionCriteria(
                resident_key=ResidentKeyRequirement.PREFERRED,
                user_verification=UserVerificationRequirement.PREFERRED,
            ),
        )

    return {"publicKey": json.loads(options_to_json(options))}


@router.post("/passkey/register")
async def register_passkey(
    request: PasskeyRegistrationRequest,
    db: AsyncSession = Depends(_ar.get_db),
):
    """Verify a registration response and store the credential."""
    user_service = _ar.UserService(db)
    user_model = await user_service.get_user_by_email(request.email)
    if not user_model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    expected_challenge = await _consume_challenge(request.email.lower())
    if expected_challenge is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passkey challenge expired. Please retry.",
        )

    try:
        verification = verify_registration_response(
            credential=request.credential,
            expected_challenge=expected_challenge,
            expected_rp_id=WEBAUTHN_RP_ID,
            expected_origin=WEBAUTHN_ORIGINS,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Passkey registration verification failed",
        ) from exc

    await user_service.update_user(
        user_model.id,
        passkey_credential_id=bytes_to_base64url(verification.credential_id),
        passkey_public_key=bytes_to_base64url(verification.credential_public_key),
    )

    return {"message": "Passkey registered successfully"}


@router.post("/passkey/auth", response_model=SuccessEnvelope[PasskeyAuthResponse])
async def authenticate_passkey(
    request: PasskeyAuthRequest,
    db: AsyncSession = Depends(_ar.get_db),
):
    """Verify an assertion and mint a Supabase session token hash."""
    user_service = _ar.UserService(db)
    user_model = await user_service.get_user_by_email(request.email)
    if not user_model or not user_model.passkey_credential_id or not user_model.passkey_public_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Passkey not registered for this user",
        )
    if not _is_user_active(user_model.is_active):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    expected_challenge = await _consume_challenge(request.email.lower())
    if expected_challenge is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passkey challenge expired. Please retry.",
        )

    try:
        verify_authentication_response(
            credential=request.assertion,
            expected_challenge=expected_challenge,
            expected_rp_id=WEBAUTHN_RP_ID,
            expected_origin=WEBAUTHN_ORIGINS,
            credential_public_key=base64url_to_bytes(user_model.passkey_public_key),
            credential_current_sign_count=0,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Passkey authentication failed",
        ) from exc

    await user_service.update_user_last_login(user_model.id)

    session_id = create_session_id(user_model.id)
    await _db_create_session(session_id, user_model.id, db)

    try:
        token_hash = await SupabaseAuth().generate_magic_link(user_model.email)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to establish a session. Please try again.",
        ) from exc

    user = User(
        id=user_model.id,
        email=user_model.email,
        name=user_model.name,
        google_id=user_model.google_id,
        passkey_credential_id=user_model.passkey_credential_id,
        passkey_public_key=user_model.passkey_public_key,
    )

    record_auth_event(event="login", method="passkey", success=True)

    return SuccessEnvelope(data=PasskeyAuthResponse(token_hash=token_hash, user=user))
