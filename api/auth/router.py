from fastapi import APIRouter, HTTPException, Depends, status
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

load_dotenv()

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer()

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Mock user database (replace with real database in production)
users_db = {}


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


class UserLogin(BaseModel):
    email: EmailStr
    password: str


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


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
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
    if user_id not in users_db:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    user = users_db[user_id]
    if not isinstance(user, User):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user data",
        )

    return user


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


@router.post("/register", response_model=Token)
async def register(user_data: UserCreate):
    # Check if user already exists
    for user in users_db.values():
        if isinstance(user, User) and user.email == user_data.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

    # Create new user
    user_id = secrets.token_urlsafe(16)
    hashed_password = hash_password(user_data.password)

    user = User(id=user_id, email=user_data.email, name=user_data.name)

    # Store user with password (in production, use proper database)
    users_db[user_id] = user
    # In production, store hashed password separately
    users_db[f"{user_id}_password"] = hashed_password

    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_id}, expires_delta=access_token_expires
    )

    return Token(access_token=access_token, token_type="bearer", user=user)


@router.post("/login", response_model=Token)
async def login(user_data: UserLogin):
    # Find user by email
    user = None
    user_id = None
    for uid, u in users_db.items():
        if isinstance(u, User) and u.email == user_data.email:
            user = u
            user_id = uid
            break

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )

    # Verify password
    stored_password = users_db.get(f"{user_id}_password")
    if not stored_password or not verify_password(user_data.password, stored_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )

    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_id}, expires_delta=access_token_expires
    )

    return Token(access_token=access_token, token_type="bearer", user=user)


@router.post("/google", response_model=Token)
async def google_auth(auth_request: GoogleAuthRequest):
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

    # Check if user exists
    user = None
    user_id = None
    for uid, u in users_db.items():
        if isinstance(u, User) and u.google_id == google_id:
            user = u
            user_id = uid
            break

    if not user:
        # Create new user
        user_id = secrets.token_urlsafe(16)
        user = User(id=user_id, email=email, name=name, google_id=google_id)
        users_db[user_id] = user

    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_id}, expires_delta=access_token_expires
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


@router.post("/google/callback", response_model=Token)
async def google_auth_callback(callback_data: GoogleAuthCallback):
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

        # Check if user exists
        user = None
        user_id = None
        for uid, u in users_db.items():
            if isinstance(u, User) and u.google_id == google_id:
                user = u
                user_id = uid
                break

        if not user:
            # Create new user
            user_id = secrets.token_urlsafe(16)
            user = User(id=user_id, email=email, name=name, google_id=google_id)
            users_db[user_id] = user

        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user_id}, expires_delta=access_token_expires
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
async def register_passkey(request: PasskeyRegistrationRequest):
    # Find user by email
    user = None
    user_id = None
    for uid, u in users_db.items():
        if isinstance(u, User) and u.email == request.email:
            user = u
            user_id = uid
            break

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Update user with passkey info
    user.passkey_credential_id = request.credential_id
    user.passkey_public_key = request.public_key
    users_db[user_id] = user

    return {"message": "Passkey registered successfully"}


@router.post("/passkey/auth", response_model=Token)
async def authenticate_passkey(request: PasskeyAuthRequest):
    # Find user by email
    user = None
    user_id = None
    for uid, u in users_db.items():
        if isinstance(u, User) and u.email == request.email:
            user = u
            user_id = uid
            break

    if not user or not user.passkey_credential_id or not user.passkey_public_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Passkey not registered for this user",
        )

    # Verify credential ID matches
    if request.credential_id != user.passkey_credential_id:
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

        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user_id}, expires_delta=access_token_expires
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
async def validate_token(request: TokenValidationRequest):
    """Validate JWT token"""
    payload = verify_token(request.token)
    if not payload:
        return {"valid": False}

    user_id = payload.get("sub")
    if user_id not in users_db:
        return {"valid": False}

    user = users_db[user_id]
    return {
        "valid": True,
        "user": {"id": user.id, "email": user.email, "name": user.name},
    }
