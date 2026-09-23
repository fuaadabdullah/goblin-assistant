"""Pydantic request/response models for the auth router."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, EmailStr


class User(BaseModel):
    id: str
    email: str
    name: Optional[str] = None
    google_id: Optional[str] = None
    passkey_credential_id: Optional[str] = None
    passkey_public_key: Optional[str] = None


class UserCreate(BaseModel):
    """User registration request model with required CSRF token."""

    email: EmailStr
    password: str
    name: Optional[str] = None
    csrf_token: Optional[str] = None  # Optional for compatibility; validated at runtime.


class UserLogin(BaseModel):
    """User login request model with required CSRF token."""

    email: EmailStr
    password: str
    csrf_token: Optional[str] = None  # Optional for compatibility; validated at runtime.


class Token(BaseModel):
    access_token: str
    token_type: str
    user: User


class TokenWithRefresh(BaseModel):
    """Token response that includes refresh token."""

    access_token: str
    refresh_token: str
    token_type: str
    user: User
    expires_in: int  # Access token expiration in seconds


class RefreshTokenRequest(BaseModel):
    """Request to refresh access token."""

    refresh_token: Optional[str] = None


class GoogleAuthRequest(BaseModel):
    token: str


class GoogleAuthCallback(BaseModel):
    code: str
    state: Optional[str] = None


class PasskeyChallengeRequest(BaseModel):
    email: EmailStr


class PasskeyRegistrationRequest(BaseModel):
    email: EmailStr
    credential: Dict[str, Any]


class PasskeyAuthRequest(BaseModel):
    email: EmailStr
    assertion: Dict[str, Any]


class PasskeyAuthResponse(BaseModel):
    token_hash: str
    user: User


class TokenValidationRequest(BaseModel):
    token: str


class LogoutResponse(BaseModel):
    """Response for logout endpoint."""

    message: str


class TokenValidationResponse(BaseModel):
    """Response for token validation endpoint."""

    valid: bool
    user: Optional[User] = None
    is_admin: bool = False


class CsrfTokenResponse(BaseModel):
    """Response for CSRF token endpoint."""

    csrf_token: str
