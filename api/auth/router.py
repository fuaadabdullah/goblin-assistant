from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional
import jwt
from jwt import PyJWTError
import bcrypt
import secrets
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from .oauth import GoogleOAuth
from .passkeys import WebAuthnPasskey
from ..storage.database import get_db
from ..storage.user_service import UserService, UserCreateData
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.csrf_manager import generate_csrf_token, validate_csrf_token
from ..core.rate_limiter_auth import check_rate_limit

load_dotenv()

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer()


# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY environment variable is required")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Session tracking (in production, use DB or Redis)
# Format: {session_id: {"user_id": "...", "created_at": datetime, "revoked": bool}}
active_sessions = {}


def create_access_token(
    data: dict, 
    expires_delta: Optional[timedelta] = None,
    scopes: Optional[list] = None,
    session_id: Optional[str] = None,
):
    """Create JWT access token with optional scopes and session ID"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "type": "access",
    })
    
    # Add scopes if provided
    if scopes:
        to_encode["scopes"] = scopes
    
    # Add session ID if provided (for revocation support)
    if session_id:
        to_encode["session_id"] = session_id
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(user_id: str, session_id: str) -> str:
    """Create JWT refresh token with longer expiration"""
    to_encode = {
        "sub": user_id,
        "type": "refresh",
        "session_id": session_id,
    }
    
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_session_id(user_id: str) -> str:
    """Create unique session ID and track it"""
    session_id = secrets.token_urlsafe(32)
    active_sessions[session_id] = {
        "user_id": user_id,
        "created_at": datetime.utcnow(),
        "revoked": False,
    }
    return session_id


def revoke_session(session_id: str) -> bool:
    """Mark session as revoked"""
    if session_id in active_sessions:
        active_sessions[session_id]["revoked"] = True
        return True
    return False


def is_session_valid(session_id: str) -> bool:
    """Check if session is active and not revoked"""
    if session_id not in active_sessions:
        return False
    return not active_sessions[session_id]["revoked"]



class User(BaseModel):
    id: str
    email: str
    name: Optional[str] = None
    google_id: Optional[str] = None
    passkey_credential_id: Optional[str] = None
    passkey_public_key: Optional[str] = None


class UserCreate(BaseModel):
    """User registration request model with required CSRF token"""
    email: EmailStr
    password: str
    name: Optional[str] = None
    csrf_token: str  # Required: Must fetch from GET /auth/csrf-token first


class UserLogin(BaseModel):
    """User login request model with required CSRF token"""
    email: EmailStr
    password: str
    csrf_token: str  # Required: Must fetch from GET /auth/csrf-token first


class Token(BaseModel):
    access_token: str
    token_type: str
    user: User


class TokenWithRefresh(BaseModel):
    """Token response that includes refresh token"""
    access_token: str
    refresh_token: str
    token_type: str
    user: User
    expires_in: int  # Access token expiration in seconds


class RefreshTokenRequest(BaseModel):
    """Request to refresh access token"""
    refresh_token: str


class GoogleAuthRequest(BaseModel):
    token: str


class GoogleAuthCallback(BaseModel):
    code: str
    state: Optional[str] = None


class PasskeyRegistrationRequest(BaseModel):
    email: EmailStr
    credential_id: str
    public_key: str


class PasskeyAuthRequest(BaseModel):
    email: EmailStr
    credential_id: str
    authenticator_data: str
    client_data_json: str
    signature: str


def verify_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except PyJWTError:
        return None


def _is_user_active(value: object) -> bool:
    """Coerce legacy string/bool DB values into active flag semantics."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    if isinstance(value, (int, float)):
        return bool(value)
    return False


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify token type is 'access'
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

    # Validate session if present
    session_id = payload.get("session_id")
    if session_id and not is_session_valid(session_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired or been revoked",
        )

    user_service = UserService(db)
    user_model = await user_service.get_user_by_id(user_id)
    if not user_model:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    if not _is_user_active(user_model.is_active):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    # Convert database model to Pydantic model
    user = User(
        id=user_model.id,
        email=user_model.email,
        name=user_model.name,
        google_id=user_model.google_id,
        passkey_credential_id=user_model.passkey_credential_id,
        passkey_public_key=user_model.passkey_public_key,
    )

    return user


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


@router.post("/register", response_model=Token)
async def register(
    user_data: UserCreate, request: Request, db: AsyncSession = Depends(get_db)
):
    # Get client IP for rate limiting
    client_ip = request.client.host if request.client else "unknown"

    # Check rate limit (reuse login limit for registration) - uses Redis
    if not await check_rate_limit(client_ip, endpoint="register"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
        )

    # Validate CSRF token (required, uses Redis)
    # Token must be provided and valid (one-time use)
    if not await validate_csrf_token(user_data.csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token"
        )

    user_service = UserService(db)

    # Check if user already exists
    existing_user = await user_service.get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create new user
    hashed_password = hash_password(user_data.password)

    user_create_data = UserCreateData(
        email=user_data.email,
        name=user_data.name,
        hashed_password=hashed_password,
    )

    user_model = await user_service.create_user(user_create_data)
    if not user_model:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user",
        )

    # Convert to Pydantic model for response
    user = User(
        id=user_model.id,
        email=user_model.email,
        name=user_model.name,
    )

    # Create session and tokens
    session_id = create_session_id(user_model.id)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_model.id}, 
        expires_delta=access_token_expires,
        scopes=["user"],
        session_id=session_id,
    )
    refresh_token = create_refresh_token(user_model.id, session_id)

    return TokenWithRefresh(
        access_token=access_token, 
        refresh_token=refresh_token,
        token_type="bearer", 
        user=user,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/login", response_model=TokenWithRefresh)
async def login(
    user_data: UserLogin, request: Request, db: AsyncSession = Depends(get_db)
):
    # Get client IP for rate limiting
    client_ip = request.client.host if request.client else "unknown"

    # Check rate limit - uses Redis
    if not await check_rate_limit(client_ip, endpoint="login"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
        )

    # Validate CSRF token (required, uses Redis)
    # Token must be provided and valid (one-time use)
    if not await validate_csrf_token(user_data.csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token"
        )

    user_service = UserService(db)

    # Find user by email
    user_model = await user_service.get_user_by_email(user_data.email)
    if not user_model:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )

    # Verify password
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

    # Update last login
    await user_service.update_user_last_login(user_model.id)

    # Convert to Pydantic model for response
    user = User(
        id=user_model.id,
        email=user_model.email,
        name=user_model.name,
        google_id=user_model.google_id,
        passkey_credential_id=user_model.passkey_credential_id,
        passkey_public_key=user_model.passkey_public_key,
    )

    # Create session and tokens
    session_id = create_session_id(user_model.id)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_model.id}, 
        expires_delta=access_token_expires,
        scopes=["user"],
        session_id=session_id,
    )
    refresh_token = create_refresh_token(user_model.id, session_id)

    return TokenWithRefresh(
        access_token=access_token, 
        refresh_token=refresh_token,
        token_type="bearer", 
        user=user,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/google", response_model=TokenWithRefresh)
async def google_auth(
    auth_request: GoogleAuthRequest, db: AsyncSession = Depends(get_db)
):
    # Verify Google OAuth token
    google_user = await GoogleOAuth.verify_token(auth_request.token)

    if not google_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google token"
        )

    email = google_user.get("email")
    google_id = google_user.get("sub")
    name = google_user.get("name")

    if not email or not google_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google user data"
        )

    user_service = UserService(db)

    # Check if user exists by Google ID
    user_model = await user_service.get_user_by_google_id(google_id)

    if not user_model:
        # Check if email already exists (might be registered with password)
        existing_user = await user_service.get_user_by_email(email)
        if existing_user:
            # Link Google account to existing user
            await user_service.update_user(existing_user.id, google_id=google_id)
            user_model = existing_user
        else:
            # Create new user
            user_create_data = UserCreateData(
                email=email,
                name=name,
                google_id=google_id,
            )
            user_model = await user_service.create_user(user_create_data)
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

    # Update last login
    await user_service.update_user_last_login(user_model.id)

    # Convert to Pydantic model for response
    user = User(
        id=user_model.id,
        email=user_model.email,
        name=user_model.name,
        google_id=user_model.google_id,
        passkey_credential_id=user_model.passkey_credential_id,
        passkey_public_key=user_model.passkey_public_key,
    )

    # Create session and tokens
    session_id = create_session_id(user_model.id)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_model.id},
        expires_delta=access_token_expires,
        scopes=["user"],
        session_id=session_id,
    )
    refresh_token = create_refresh_token(user_model.id, session_id)

    return TokenWithRefresh(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=user,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/google/url")
async def get_google_auth_url():
    """Get Google OAuth authorization URL"""
    try:
        auth_url = GoogleOAuth.get_authorization_url()
        return {"authorization_url": auth_url}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post("/refresh", response_model=TokenWithRefresh)
async def refresh_token_endpoint(
    request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)
):
    """Exchange refresh token for new access and refresh tokens"""
    # Verify refresh token
    payload = verify_token(request.refresh_token)
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
    
    # Verify session is still active
    if not is_session_valid(session_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired or been revoked",
        )
    
    # Verify user exists
    user_service = UserService(db)
    user_model = await user_service.get_user_by_id(user_id)
    if not user_model:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    # Convert to Pydantic model
    user = User(
        id=user_model.id,
        email=user_model.email,
        name=user_model.name,
        google_id=user_model.google_id,
        passkey_credential_id=user_model.passkey_credential_id,
        passkey_public_key=user_model.passkey_public_key,
    )
    
    # Create new access and refresh tokens using same session
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_id},
        expires_delta=access_token_expires,
        scopes=["user"],
        session_id=session_id,
    )
    new_refresh_token = create_refresh_token(user_id, session_id)
    
    return TokenWithRefresh(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        user=user,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/csrf-token")
async def get_csrf_token():
    """Get a CSRF token for form submissions. Required for /register and /login."""
    token = await generate_csrf_token()
    return {"csrf_token": token}


@router.post("/google/callback", response_model=TokenWithRefresh)
async def google_auth_callback(
    callback_data: GoogleAuthCallback, db: AsyncSession = Depends(get_db)
):
    """Handle Google OAuth callback"""
    try:
        # Exchange code for token
        token_data = await GoogleOAuth.exchange_code_for_token(callback_data.code)

        if not token_data or "access_token" not in token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to exchange code for token",
            )

        access_token = token_data["access_token"]

        # Get user info
        google_user = await GoogleOAuth.get_user_info(access_token)

        if not google_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to get user info from Google",
            )

        email = google_user.get("email")
        google_id = google_user.get("sub")
        name = google_user.get("name")

        if not email or not google_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google user data",
            )

        user_service = UserService(db)

        # Check if user exists by Google ID
        user_model = await user_service.get_user_by_google_id(google_id)

        if not user_model:
            # Check if email already exists (might be registered with password)
            existing_user = await user_service.get_user_by_email(email)
            if existing_user:
                # Link Google account to existing user
                await user_service.update_user(existing_user.id, google_id=google_id)
                user_model = existing_user
            else:
                # Create new user
                user_create_data = UserCreateData(
                    email=email,
                    name=name,
                    google_id=google_id,
                )
                user_model = await user_service.create_user(user_create_data)
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

        # Update last login
        await user_service.update_user_last_login(user_model.id)

        # Convert to Pydantic model for response
        user = User(
            id=user_model.id,
            email=user_model.email,
            name=user_model.name,
            google_id=user_model.google_id,
            passkey_credential_id=user_model.passkey_credential_id,
            passkey_public_key=user_model.passkey_public_key,
        )

        # Create session and tokens
        session_id = create_session_id(user_model.id)
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user_model.id},
            expires_delta=access_token_expires,
            scopes=["user"],
            session_id=session_id,
        )
        refresh_token = create_refresh_token(user_model.id, session_id)

        return TokenWithRefresh(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=user,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Google authentication failed: {str(e)}",
        )


@router.post("/passkey/challenge")
async def get_passkey_challenge():
    """Get a challenge for passkey registration/authentication"""
    challenge = WebAuthnPasskey.generate_challenge()
    return {"challenge": challenge}


@router.post("/passkey/register")
async def register_passkey(
    request: PasskeyRegistrationRequest, db: AsyncSession = Depends(get_db)
):
    user_service = UserService(db)

    # Find user by email
    user_model = await user_service.get_user_by_email(request.email)
    if not user_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Update user with passkey info
    await user_service.update_user(
        user_model.id,
        passkey_credential_id=request.credential_id,
        passkey_public_key=request.public_key,
    )

    return {"message": "Passkey registered successfully"}


@router.post("/passkey/auth", response_model=TokenWithRefresh)
async def authenticate_passkey(
    request: PasskeyAuthRequest, db: AsyncSession = Depends(get_db)
):
    user_service = UserService(db)

    # Find user by email
    user_model = await user_service.get_user_by_email(request.email)
    if (
        not user_model
        or not user_model.passkey_credential_id
        or not user_model.passkey_public_key
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Passkey not registered for this user",
        )

    # Verify credential ID matches
    if request.credential_id != user_model.passkey_credential_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credential ID"
        )

    # Verify passkey signature (simplified for demo - in production use full WebAuthn verification)
    # For now, we'll do basic validation
    try:
        if not _is_user_active(user_model.is_active):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
            )

        # In production, you would verify the full WebAuthn assertion here
        # For demo purposes, we'll accept any valid-looking passkey data
        if (
            not request.authenticator_data
            or not request.client_data_json
            or not request.signature
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid passkey authentication data",
            )

        # Update last login
        await user_service.update_user_last_login(user_model.id)

        # Convert to Pydantic model for response
        user = User(
            id=user_model.id,
            email=user_model.email,
            name=user_model.name,
            google_id=user_model.google_id,
            passkey_credential_id=user_model.passkey_credential_id,
            passkey_public_key=user_model.passkey_public_key,
        )

        # Create session and tokens
        session_id = create_session_id(user_model.id)
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user_model.id},
            expires_delta=access_token_expires,
            scopes=["user"],
            session_id=session_id,
        )
        refresh_token = create_refresh_token(user_model.id, session_id)

        return TokenWithRefresh(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=user,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Passkey authentication failed",
        )


@router.get("/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user), credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Logout user and revoke session"""
    # Extract session ID from token
    token = credentials.credentials
    payload = verify_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    
    session_id = payload.get("session_id")
    if session_id:
        revoke_session(session_id)
    
    return {"message": "Logged out successfully"}


class TokenValidationRequest(BaseModel):
    token: str


@router.post("/validate")
async def validate_token(
    request: TokenValidationRequest, db: AsyncSession = Depends(get_db)
):
    """Validate JWT token"""
    payload = verify_token(request.token)
    if not payload:
        return {"valid": False}

    user_id = payload.get("sub")
    if not user_id:
        return {"valid": False}

    user_service = UserService(db)
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
