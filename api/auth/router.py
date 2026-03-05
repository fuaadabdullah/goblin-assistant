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
from collections import defaultdict
from .oauth import GoogleOAuth
from .passkeys import WebAuthnPasskey
from ..storage.database import get_db
from ..storage.user_service import UserService, UserCreateData
from sqlalchemy.ext.asyncio import AsyncSession

load_dotenv()

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer()

# Rate limiting storage (in production, use Redis or similar)
rate_limit_store = defaultdict(list)

# Rate limiting configuration
MAX_LOGIN_ATTEMPTS = 5  # Max attempts per IP per hour
RATE_LIMIT_WINDOW = 3600  # 1 hour in seconds

# CSRF protection
csrf_tokens = set()


def generate_csrf_token() -> str:
    """Generate a new CSRF token"""
    token = secrets.token_urlsafe(32)
    csrf_tokens.add(token)
    return token


def validate_csrf_token(token: str) -> bool:
    """Validate CSRF token"""
    if token in csrf_tokens:
        csrf_tokens.discard(token)  # One-time use
        return True
    return False


def check_rate_limit(client_ip: str) -> bool:
    """Check if client IP is within rate limits"""
    now = datetime.utcnow()
    window_start = now - timedelta(seconds=RATE_LIMIT_WINDOW)

    # Clean old entries
    rate_limit_store[client_ip] = [
        timestamp
        for timestamp in rate_limit_store[client_ip]
        if timestamp > window_start
    ]

    # Check if under limit
    if len(rate_limit_store[client_ip]) >= MAX_LOGIN_ATTEMPTS:
        return False

    # Record this attempt
    rate_limit_store[client_ip].append(now)
    return True


# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY environment variable is required")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


class User(BaseModel):
    id: str
    email: str
    name: Optional[str] = None
    google_id: Optional[str] = None
    passkey_credential_id: Optional[str] = None
    passkey_public_key: Optional[str] = None


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None
    csrf_token: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    csrf_token: Optional[str] = None


class Token(BaseModel):
    access_token: str
    token_type: str
    user: User


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


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except PyJWTError:
        return None


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

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user_service = UserService(db)
    user_model = await user_service.get_user_by_id(user_id)
    if not user_model:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
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

    # Check rate limit (reuse login limit for registration)
    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
        )

    # Validate CSRF token if provided
    if user_data.csrf_token and not validate_csrf_token(user_data.csrf_token):
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

    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_model.id}, expires_delta=access_token_expires
    )

    return Token(access_token=access_token, token_type="bearer", user=user)


@router.post("/login", response_model=Token)
async def login(
    user_data: UserLogin, request: Request, db: AsyncSession = Depends(get_db)
):
    # Get client IP for rate limiting
    client_ip = request.client.host if request.client else "unknown"

    # Check rate limit
    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
        )

    # Validate CSRF token if provided
    if user_data.csrf_token and not validate_csrf_token(user_data.csrf_token):
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

    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_model.id}, expires_delta=access_token_expires
    )

    return Token(access_token=access_token, token_type="bearer", user=user)


@router.post("/google", response_model=Token)
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

    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_model.id}, expires_delta=access_token_expires
    )

    return Token(access_token=access_token, token_type="bearer", user=user)


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


@router.post("/refresh", response_model=Token)
async def refresh_token(current_user: User = Depends(get_current_user)):
    """Refresh access token for authenticated user"""
    # Create new access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": current_user.id}, expires_delta=access_token_expires
    )

    return Token(access_token=access_token, token_type="bearer", user=current_user)


@router.get("/csrf-token")
async def get_csrf_token():
    """Get a CSRF token for form submissions"""
    token = generate_csrf_token()
    return {"csrf_token": token}


@router.post("/google/callback", response_model=Token)
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

        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user_model.id}, expires_delta=access_token_expires
        )

        return Token(access_token=access_token, token_type="bearer", user=user)

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


@router.post("/passkey/auth", response_model=Token)
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

        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user_model.id}, expires_delta=access_token_expires
        )

        return Token(access_token=access_token, token_type="bearer", user=user)

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Passkey authentication failed",
        )


@router.get("/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/logout")
async def logout():
    """Logout user (client-side token removal)"""
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
