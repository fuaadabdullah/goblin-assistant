"""Google OAuth routes: /google, /google/url, /google/callback."""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..oauth import GoogleOAuth
from . import _runtime as _ar
from .config import ACCESS_TOKEN_EXPIRE_MINUTES
from .cookies import _set_auth_cookies
from .dependencies import _is_user_active
from .schemas import GoogleAuthCallback, GoogleAuthRequest, TokenWithRefresh, User
from .sessions import _db_create_session, create_session_id
from .tokens import create_access_token, create_refresh_token
from ...core.contracts import SuccessEnvelope

router = APIRouter()


async def _issue_google_session_tokens(
    google_user: dict,
    db: AsyncSession,
    response: Response,
) -> TokenWithRefresh:
    """Shared body for /google and /google/callback once we have the Google user.

    Looks up by google_id, falls back to email-link, otherwise creates a new
    user. Then mints a session + JWT pair and sets cookies.
    """
    email = google_user.get("email")
    google_id = google_user.get("sub")
    name = google_user.get("name")

    if not email or not google_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google user data"
        )

    user_service = _ar.UserService(db)

    user_model = await user_service.get_user_by_google_id(google_id)

    if not user_model:
        existing_user = await user_service.get_user_by_email(email)
        if existing_user:
            await user_service.update_user(existing_user.id, google_id=google_id, flush_only=True)
            user_model = existing_user
        else:
            user_create_data = _ar.UserCreateData(
                email=email,
                name=name,
                google_id=google_id,
            )
            user_model = await user_service.create_user(user_create_data, flush_only=True)
            if not user_model:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create user",
                )

    if not _is_user_active(user_model.is_active):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    await user_service.update_user_last_login(user_model.id, flush_only=True)

    user = User(
        id=user_model.id,
        email=user_model.email,
        name=user_model.name,
        google_id=user_model.google_id,
        passkey_credential_id=user_model.passkey_credential_id,
        passkey_public_key=user_model.passkey_public_key,
    )

    # Single atomic commit for user updates + session.
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

    return SuccessEnvelope(
        data=TokenWithRefresh(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=user,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
    )


@router.post("/google", response_model=SuccessEnvelope[TokenWithRefresh])
async def google_auth(
    auth_request: GoogleAuthRequest,
    response: Response,
    db: AsyncSession = Depends(_ar.get_db),
):
    google_user = await GoogleOAuth.verify_token(auth_request.token)
    if not google_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google token")
    return await _issue_google_session_tokens(google_user, db, response)


@router.get("/google/url")
async def get_google_auth_url():
    """Get Google OAuth authorization URL."""
    try:
        auth_url = GoogleOAuth.get_authorization_url()
        return {"authorization_url": auth_url}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/google/callback", response_model=SuccessEnvelope[TokenWithRefresh])
async def google_auth_callback(
    callback_data: GoogleAuthCallback,
    response: Response,
    db: AsyncSession = Depends(_ar.get_db),
):
    """Handle Google OAuth callback."""
    try:
        token_data = await GoogleOAuth.exchange_code_for_token(callback_data.code)

        if not token_data or "access_token" not in token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to exchange code for token",
            )

        access_token = token_data["access_token"]
        google_user = await GoogleOAuth.get_user_info(access_token)

        if not google_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to get user info from Google",
            )

        return await _issue_google_session_tokens(google_user, db, response)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Google authentication failed: {str(e)}",
        )
