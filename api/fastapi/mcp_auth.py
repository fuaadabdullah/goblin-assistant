"""
MCP Authentication and Authorization

JWT-based authentication with role-based access control (RBAC) for the MCP service.
"""

import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass

import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Password hashing - using pbkdf2_sha256 for better compatibility
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# JWT settings
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "30"))


class UserRole(Enum):
    ADMIN = "admin"
    USER = "user"
    SERVICE = "service"  # For internal services


@dataclass
class User:
    """User model for authentication."""

    id: str
    username: str
    role: UserRole
    hashed_password: str
    is_active: bool = True
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class AuthService:
    """Authentication service for JWT tokens and user management."""

    def __init__(self):
        # In production, use a proper database
        self.users: Dict[str, User] = {}
        try:
            self._create_default_users()  # Enable default users for testing
        except Exception as e:
            print(f"Warning: Could not create default users: {e}")
            # Create a simple test user without bcrypt
            from passlib.hash import pbkdf2_sha256

            test_password = pbkdf2_sha256.hash("admin123")
            self.users["admin"] = User(
                id="admin-001",
                username="admin",
                role=UserRole.ADMIN,
                hashed_password=test_password,
                is_active=True,
            )

    def _create_default_users(self):
        """Create default users for development."""
        # Admin user
        admin_password = self.hash_password("admin123")
        self.users["admin"] = User(
            id="admin-001",
            username="admin",
            role=UserRole.ADMIN,
            hashed_password=admin_password,
        )

        # Regular user
        user_password = self.hash_password("user123")
        self.users["user"] = User(
            id="user-001",
            username="user",
            role=UserRole.USER,
            hashed_password=user_password,
        )

        # Service account
        service_password = self.hash_password("service123")
        self.users["service"] = User(
            id="service-001",
            username="service",
            role=UserRole.SERVICE,
            hashed_password=service_password,
        )

    def hash_password(self, password: str) -> str:
        """Hash a password."""
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate a user."""
        user = self.users.get(username)
        if not user or not self.verify_password(password, user.hashed_password):
            return None
        return user

    def create_access_token(
        self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode and validate a JWT token."""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.JWTError:
            return None

    def get_current_user(self, token: str) -> Optional[User]:
        """Get current user from JWT token."""
        payload = self.decode_token(token)
        if not payload:
            return None

        username = payload.get("sub")
        if not username:
            return None

        return self.users.get(username)


# Global auth service instance
auth_service = AuthService()

# FastAPI security scheme
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """Dependency to get current authenticated user."""
    token = credentials.credentials
    user = auth_service.get_current_user(token)

    if not user:
        raise HTTPException(
            status_code=401, detail="Invalid authentication credentials"
        )

    if not user.is_active:
        raise HTTPException(status_code=401, detail="User account is disabled")

    return user


def require_role(required_role: UserRole):
    """Dependency factory for role-based access control."""

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role != required_role and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required role: {required_role.value}",
            )
        return current_user

    return role_checker


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency for admin-only endpoints."""
    return require_role(UserRole.ADMIN)(current_user)


def require_user_or_service(current_user: User = Depends(get_current_user)) -> User:
    """Dependency for user or service access."""
    if current_user.role not in [UserRole.USER, UserRole.SERVICE, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Access denied")
    return current_user


# Utility functions for MCP request hashing
def hash_user_id(user_id: str) -> str:
    """Hash user ID for privacy."""
    import hashlib

    return hashlib.sha256(user_id.encode()).hexdigest()[:16]


def hash_request_data(data: str) -> str:
    """Hash request data for logging."""
    import hashlib

    return hashlib.sha256(data.encode()).hexdigest()[:16]
