"""
Comprehensive auth router tests

Tests cover:
- User registration with validation
- User login with password verification
- Rate limiting enforcement
- CSRF token validation
- Error cases (duplicate email, invalid password, rate limit exceeded)
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, Mock
import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.router import (
    router,
    create_access_token,
    verify_token,
    hash_password,
    verify_password,
    check_rate_limit,
    generate_csrf_token,
    validate_csrf_token,
    SECRET_KEY,
    ALGORITHM,
)
from api.storage.user_service import UserService, UserCreateData
from fastapi import FastAPI

# Create a test app
test_app = FastAPI()
test_app.include_router(router)


@pytest.fixture
def client():
    """FastAPI TestClient for auth endpoints"""
    return TestClient(test_app)


@pytest.fixture
def mock_db():
    """Mock AsyncSession database"""
    return AsyncMock(spec=AsyncSession)


class TestPasswordHashing:
    """Test password hashing and verification"""

    def test_hash_password_returns_string(self):
        """Test that hash_password returns a string"""
        password = "test_password_123"
        hashed = hash_password(password)
        assert isinstance(hashed, str)
        assert hashed != password

    def test_hash_password_different_each_time(self):
        """Test that same password produces different hashes"""
        password = "test_password_123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2

    def test_verify_password_valid(self):
        """Test that verify_password returns True for correct password"""
        password = "test_password_123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_invalid(self):
        """Test that verify_password returns False for incorrect password"""
        password = "test_password_123"
        hashed = hash_password(password)
        assert verify_password("wrong_password", hashed) is False


class TestJWTTokens:
    """Test JWT token creation and verification"""

    def test_create_access_token(self):
        """Test that create_access_token generates valid JWT"""
        data = {"sub": "user_123"}
        token = create_access_token(data)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_token_valid(self):
        """Test that verify_token correctly decodes valid token"""
        data = {"sub": "user_123"}
        token = create_access_token(data)
        payload = verify_token(token)
        assert payload is not None
        assert payload["sub"] == "user_123"

    def test_verify_token_invalid(self):
        """Test that verify_token returns None for invalid token"""
        invalid_token = "invalid.token.here"
        payload = verify_token(invalid_token)
        assert payload is None

    def test_verify_token_expired(self):
        """Test that verify_token returns None for expired token"""
        data = {"sub": "user_123"}
        # Create a token that expires immediately
        to_encode = data.copy()
        expire = datetime.utcnow() - timedelta(minutes=1)
        to_encode.update({"exp": expire})
        expired_token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        payload = verify_token(expired_token)
        assert payload is None

    def test_token_contains_correct_user_id(self):
        """Test that token payload contains correct user_id"""
        user_id = "user_abc_123"
        data = {"sub": user_id}
        token = create_access_token(data)
        payload = verify_token(token)
        assert payload["sub"] == user_id


class TestCSRFProtection:
    """Test CSRF token generation and validation"""

    def test_generate_csrf_token_returns_string(self):
        """Test that CSRF token is generated"""
        token = generate_csrf_token()
        assert isinstance(token, str)
        assert len(token) > 0

    def test_csrf_tokens_are_unique(self):
        """Test that CSRF tokens are unique"""
        token1 = generate_csrf_token()
        token2 = generate_csrf_token()
        assert token1 != token2

    def test_validate_csrf_token_valid(self):
        """Test that valid CSRF token passes validation"""
        token = generate_csrf_token()
        assert validate_csrf_token(token) is True

    def test_validate_csrf_token_invalid(self):
        """Test that invalid CSRF token fails validation"""
        assert validate_csrf_token("invalid_token") is False

    def test_csrf_token_one_time_use(self):
        """Test that CSRF token is consumed after validation"""
        token = generate_csrf_token()
        # First use should succeed
        assert validate_csrf_token(token) is True
        # Second use should fail
        assert validate_csrf_token(token) is False


class TestRateLimiting:
    """Test rate limiting functionality"""

    def test_rate_limit_allows_under_limit(self):
        """Test that requests under limit are allowed"""
        client_ip = "192.168.1.1"
        # First 5 requests should succeed
        for _ in range(5):
            assert check_rate_limit(client_ip) is True

    def test_rate_limit_blocks_over_limit(self):
        """Test that requests over limit are blocked"""
        client_ip = "192.168.1.2"
        # Fill up the limit
        for _ in range(5):
            check_rate_limit(client_ip)
        # Next request should fail
        assert check_rate_limit(client_ip) is False

    def test_rate_limit_per_ip(self):
        """Test that rate limiting is per IP"""
        ip1 = "192.168.1.3"
        ip2 = "192.168.1.4"
        
        # Max out ip1
        for _ in range(5):
            check_rate_limit(ip1)
        
        # ip2 should still have requests available
        assert check_rate_limit(ip2) is True


class TestRegisterEndpoint:
    """Test user registration endpoint"""

    @pytest.mark.asyncio
    async def test_register_success(self, client, mock_db):
        """Test successful user registration"""
        with patch('api.auth.router.get_db', return_value=mock_db):
            mock_user_service = AsyncMock(spec=UserService)
            
            # Mock user doesn't exist yet
            mock_user_service.get_user_by_email.return_value = None
            
            # Mock user creation
            mock_user_model = MagicMock()
            mock_user_model.id = "user_123"
            mock_user_model.email = "test@example.com"
            mock_user_model.name = "Test User"
            mock_user_model.hashed_password = hash_password("password123")
            mock_user_service.create_user.return_value = mock_user_model
            
            with patch('api.auth.router.UserService', return_value=mock_user_service):
                response = client.post(
                    "/auth/register",
                    json={
                        "email": "test@example.com",
                        "password": "password123",
                        "name": "Test User",
                    },
                )
            
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"
            assert data["user"]["email"] == "test@example.com"

    def test_register_duplicate_email(self, client):
        """Test registration with existing email"""
        with patch('api.auth.router.UserService') as MockUserService:
            mock_service = AsyncMock()
            # Email already exists
            mock_service.get_user_by_email.return_value = MagicMock()
            MockUserService.return_value = mock_service
            
            with patch('api.auth.router.get_db'):
                response = client.post(
                    "/auth/register",
                    json={
                        "email": "existing@example.com",
                        "password": "password123",
                        "name": "Test User",
                    },
                )
            
            assert response.status_code == 400
            assert "already registered" in response.json()["detail"]

    def test_register_rate_limited(self, client):
        """Test registration rate limiting"""
        # Reset rate limit
        from api.auth.router import rate_limit_store
        rate_limit_store.clear()
        
        with patch('api.auth.router.UserService') as MockUserService:
            mock_service = AsyncMock()
            mock_service.get_user_by_email.return_value = None
            MockUserService.return_value = mock_service
            
            with patch('api.auth.router.get_db'):
                # Make 5 requests (at limit)
                for i in range(5):
                    response = client.post(
                        "/auth/register",
                        json={
                            "email": f"user{i}@example.com",
                            "password": "password123",
                        },
                    )
                    assert response.status_code == 200
                
                # 6th request should fail
                response = client.post(
                    "/auth/register",
                    json={
                        "email": "user6@example.com",
                        "password": "password123",
                    },
                )
                assert response.status_code == 429


class TestLoginEndpoint:
    """Test user login endpoint"""

    def test_login_success(self, client):
        """Test successful login"""
        password = "password123"
        with patch('api.auth.router.UserService') as MockUserService:
            mock_service = AsyncMock()
            
            # Mock user exists
            mock_user_model = MagicMock()
            mock_user_model.id = "user_123"
            mock_user_model.email = "user@example.com"
            mock_user_model.hashed_password = hash_password(password)
            mock_service.get_user_by_email.return_value = mock_user_model
            mock_service.update_user_last_login = AsyncMock()
            
            MockUserService.return_value = mock_service
            
            with patch('api.auth.router.get_db'):
                response = client.post(
                    "/auth/login",
                    json={
                        "email": "user@example.com",
                        "password": password,
                    },
                )
            
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["user"]["email"] == "user@example.com"

    def test_login_invalid_email(self, client):
        """Test login with non-existent email"""
        with patch('api.auth.router.UserService') as MockUserService:
            mock_service = AsyncMock()
            mock_service.get_user_by_email.return_value = None
            MockUserService.return_value = mock_service
            
            with patch('api.auth.router.get_db'):
                response = client.post(
                    "/auth/login",
                    json={
                        "email": "nonexistent@example.com",
                        "password": "password123",
                    },
                )
            
            assert response.status_code == 401
            assert "Invalid email or password" in response.json()["detail"]

    def test_login_invalid_password(self, client):
        """Test login with incorrect password"""
        password = "correct_password"
        with patch('api.auth.router.UserService') as MockUserService:
            mock_service = AsyncMock()
            
            # Mock user exists
            mock_user_model = MagicMock()
            mock_user_model.id = "user_123"
            mock_user_model.email = "user@example.com"
            mock_user_model.hashed_password = hash_password(password)
            mock_service.get_user_by_email.return_value = mock_user_model
            
            MockUserService.return_value = mock_service
            
            with patch('api.auth.router.get_db'):
                response = client.post(
                    "/auth/login",
                    json={
                        "email": "user@example.com",
                        "password": "wrong_password",
                    },
                )
            
            assert response.status_code == 401
            assert "Invalid email or password" in response.json()["detail"]

    def test_login_rate_limited(self, client):
        """Test login rate limiting"""
        from api.auth.router import rate_limit_store
        rate_limit_store.clear()
        
        with patch('api.auth.router.UserService') as MockUserService:
            mock_service = AsyncMock()
            mock_service.get_user_by_email.return_value = None
            MockUserService.return_value = mock_service
            
            with patch('api.auth.router.get_db'):
                # Make 5 login attempts (at limit)
                for i in range(5):
                    response = client.post(
                        "/auth/login",
                        json={
                            "email": "user@example.com",
                            "password": "password123",
                        },
                    )
                
                # 6th attempt should be rate limited
                response = client.post(
                    "/auth/login",
                    json={
                        "email": "user@example.com",
                        "password": "password123",
                    },
                )
                assert response.status_code == 429
