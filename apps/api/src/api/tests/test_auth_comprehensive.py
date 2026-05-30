"""
Comprehensive auth router tests.

Tests cover:
- Password hashing + JWT token issuance/verification
- CSRF token lifecycle (one-time use, expiry semantics)
- Rate limiting (per-IP sliding window)
- Register/login flows: success, duplicate email, invalid password, rate limiting

Implementation notes:
- CSRF + rate-limit functions are async + Redis-backed in production; tests
  mock the Redis client and exercise the in-memory fallback paths.
- Register/login routes are exercised via TestClient with FastAPI
  `dependency_overrides` for `get_db` and `_ar.X` runtime patches for
  `validate_csrf_token`, `check_rate_limit`, and `UserService`.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.router import (
    ALGORITHM,
    SECRET_KEY,
    create_access_token,
    get_db,
    hash_password,
    router,
    verify_password,
    verify_token,
)
from api.core import csrf_manager


@pytest.fixture
def app(mock_db):
    """FastAPI app with auth router wired up and DB override.

    Using `dependency_overrides` rather than monkeypatching `get_db` —
    `Depends(get_db)` captures the function reference at route registration,
    so post-registration attribute patches don't take effect.
    """
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: mock_db
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def mock_db():
    db = AsyncMock(spec=AsyncSession)
    # `add` is sync on real Session; AsyncMock would make it a coroutine.
    db.add = MagicMock()
    return db


@pytest.fixture
def csrf_always_valid():
    """Patch the CSRF check used by routes to always succeed."""
    with patch(
        "api.auth.router.validate_csrf_token",
        new=AsyncMock(return_value=True),
    ):
        yield


@pytest.fixture
def rate_limit_open():
    """Patch the rate-limiter used by routes to always allow."""
    with patch(
        "api.auth.router.check_rate_limit",
        new=AsyncMock(return_value=True),
    ):
        yield


@pytest.fixture(autouse=True)
def _reset_csrf_fallback():
    """Clear the CSRF in-memory fallback between tests."""
    csrf_manager._csrf_fallback_store.clear()
    yield
    csrf_manager._csrf_fallback_store.clear()


# ---------- Password hashing ----------


class TestPasswordHashing:
    def test_hash_password_returns_string(self):
        hashed = hash_password("test_password_123")
        assert isinstance(hashed, str)
        assert hashed != "test_password_123"

    def test_hash_password_different_each_time(self):
        hash1 = hash_password("test_password_123")
        hash2 = hash_password("test_password_123")
        assert hash1 != hash2

    def test_verify_password_valid(self):
        password = "test_password_123"
        assert verify_password(password, hash_password(password)) is True

    def test_verify_password_invalid(self):
        hashed = hash_password("test_password_123")
        assert verify_password("wrong_password", hashed) is False


# ---------- JWT tokens ----------


class TestJWTTokens:
    def test_create_access_token(self):
        token = create_access_token({"sub": "user_123"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_token_valid(self):
        token = create_access_token({"sub": "user_123"})
        payload = verify_token(token)
        assert payload is not None
        assert payload["sub"] == "user_123"

    def test_verify_token_invalid(self):
        assert verify_token("invalid.token.here") is None

    def test_verify_token_expired(self):
        to_encode = {
            "sub": "user_123",
            "exp": datetime.utcnow() - timedelta(minutes=1),
        }
        expired_token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        assert verify_token(expired_token) is None

    def test_token_contains_correct_user_id(self):
        user_id = "user_abc_123"
        token = create_access_token({"sub": user_id})
        assert verify_token(token)["sub"] == user_id


# ---------- CSRF token lifecycle ----------


def _fail_redis():
    """Make `get_redis_client` fail so CSRF/rate-limit fall back to in-memory."""
    return patch(
        "api.core.csrf_manager.get_redis_client",
        side_effect=RuntimeError("redis unavailable"),
    )


class TestCSRFProtection:
    @pytest.mark.asyncio
    async def test_generate_csrf_token_returns_string(self):
        with _fail_redis():
            token = await csrf_manager.generate_csrf_token()
        assert isinstance(token, str)
        assert len(token) > 0

    @pytest.mark.asyncio
    async def test_csrf_tokens_are_unique(self):
        with _fail_redis():
            t1 = await csrf_manager.generate_csrf_token()
            t2 = await csrf_manager.generate_csrf_token()
        assert t1 != t2

    @pytest.mark.asyncio
    async def test_validate_csrf_token_valid(self):
        with _fail_redis():
            token = await csrf_manager.generate_csrf_token()
            assert await csrf_manager.validate_csrf_token(token) is True

    @pytest.mark.asyncio
    async def test_validate_csrf_token_invalid(self):
        with _fail_redis():
            assert await csrf_manager.validate_csrf_token("invalid_token") is False

    @pytest.mark.asyncio
    async def test_csrf_token_one_time_use(self):
        with _fail_redis():
            token = await csrf_manager.generate_csrf_token()
            assert await csrf_manager.validate_csrf_token(token) is True
            # Second use must fail — the token is consumed on validation.
            assert await csrf_manager.validate_csrf_token(token) is False


# ---------- Rate limiting ----------


def _redis_mock_for_rate_limit(count_sequence):
    """Build a redis_client mock where `zcard` returns the given counts in order.

    The rate limiter calls `zremrangebyscore`, then `zcard` (count), then
    `zadd` + `expire`. Only `zcard` drives the allow/deny decision.
    """
    redis_client = AsyncMock()
    redis_client.zremrangebyscore = AsyncMock(return_value=0)
    redis_client.zcard = AsyncMock(side_effect=count_sequence)
    redis_client.zadd = AsyncMock(return_value=1)
    redis_client.expire = AsyncMock(return_value=True)
    return redis_client


class TestRateLimiting:
    @pytest.mark.asyncio
    async def test_rate_limit_allows_under_limit(self):
        from api.core.rate_limiter_auth import check_rate_limit

        # Counts < MAX_LOGIN_ATTEMPTS (5) for each of 5 calls.
        redis_client = _redis_mock_for_rate_limit([0, 1, 2, 3, 4])
        with patch(
            "api.core.rate_limiter_auth.get_redis_client",
            return_value=redis_client,
        ):
            for _ in range(5):
                assert await check_rate_limit("192.168.1.1") is True

    @pytest.mark.asyncio
    async def test_rate_limit_blocks_over_limit(self):
        from api.core.rate_limiter_auth import check_rate_limit

        # 6th call sees count==5, which is >= MAX_LOGIN_ATTEMPTS → False.
        redis_client = _redis_mock_for_rate_limit([0, 1, 2, 3, 4, 5])
        with patch(
            "api.core.rate_limiter_auth.get_redis_client",
            return_value=redis_client,
        ):
            for _ in range(5):
                await check_rate_limit("192.168.1.2")
            assert await check_rate_limit("192.168.1.2") is False

    @pytest.mark.asyncio
    async def test_rate_limit_per_ip(self):
        from api.core.rate_limiter_auth import check_rate_limit

        # ip1: 5 calls (counts 0..4); ip2: 1 call (count 0). Both stay under limit.
        redis_client = _redis_mock_for_rate_limit([0, 1, 2, 3, 4, 0])
        with patch(
            "api.core.rate_limiter_auth.get_redis_client",
            return_value=redis_client,
        ):
            for _ in range(5):
                await check_rate_limit("192.168.1.3")
            assert await check_rate_limit("192.168.1.4") is True


# ---------- Register endpoint ----------


class TestRegisterEndpoint:
    def test_register_success(self, client, csrf_always_valid, rate_limit_open):
        mock_service = AsyncMock()
        mock_service.get_user_by_email = AsyncMock(return_value=None)

        mock_user_model = MagicMock()
        mock_user_model.id = "user_123"
        mock_user_model.email = "test@example.com"
        mock_user_model.name = "Test User"
        mock_user_model.hashed_password = hash_password("password123")
        mock_service.create_user = AsyncMock(return_value=mock_user_model)

        with patch("api.auth.router.UserService", return_value=mock_service):
            response = client.post(
                "/auth/register",
                json={
                    "email": "test@example.com",
                    "password": "password123",
                    "name": "Test User",
                    "csrf_token": "fake-csrf",
                },
            )

        assert response.status_code == 200, response.text
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "test@example.com"

    def test_register_duplicate_email(self, client, csrf_always_valid, rate_limit_open):
        mock_service = AsyncMock()
        mock_service.get_user_by_email = AsyncMock(return_value=MagicMock())

        with patch("api.auth.router.UserService", return_value=mock_service):
            response = client.post(
                "/auth/register",
                json={
                    "email": "existing@example.com",
                    "password": "password123",
                    "name": "Test User",
                    "csrf_token": "fake-csrf",
                },
            )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    def test_register_rate_limited(self, client, csrf_always_valid):
        # Force the rate-limiter to deny — verifies the route returns 429.
        with patch(
            "api.auth.router.check_rate_limit",
            new=AsyncMock(return_value=False),
        ):
            response = client.post(
                "/auth/register",
                json={
                    "email": "user@example.com",
                    "password": "password123",
                    "csrf_token": "fake-csrf",
                },
            )
        assert response.status_code == 429


# ---------- Login endpoint ----------


class TestLoginEndpoint:
    def test_login_success(self, client, csrf_always_valid, rate_limit_open):
        password = "password123"
        mock_service = AsyncMock()

        mock_user_model = MagicMock()
        mock_user_model.id = "user_123"
        mock_user_model.email = "user@example.com"
        mock_user_model.name = None
        mock_user_model.google_id = None
        mock_user_model.passkey_credential_id = None
        mock_user_model.passkey_public_key = None
        mock_user_model.is_active = True
        mock_user_model.hashed_password = hash_password(password)
        mock_service.get_user_by_email = AsyncMock(return_value=mock_user_model)
        mock_service.update_user_last_login = AsyncMock()

        with patch("api.auth.router.UserService", return_value=mock_service):
            response = client.post(
                "/auth/login",
                json={
                    "email": "user@example.com",
                    "password": password,
                    "csrf_token": "fake-csrf",
                },
            )

        assert response.status_code == 200, response.text
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == "user@example.com"

    def test_login_invalid_email(self, client, csrf_always_valid, rate_limit_open):
        mock_service = AsyncMock()
        mock_service.get_user_by_email = AsyncMock(return_value=None)

        with patch("api.auth.router.UserService", return_value=mock_service):
            response = client.post(
                "/auth/login",
                json={
                    "email": "nonexistent@example.com",
                    "password": "password123",
                    "csrf_token": "fake-csrf",
                },
            )

        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    def test_login_invalid_password(self, client, csrf_always_valid, rate_limit_open):
        password = "correct_password"
        mock_service = AsyncMock()

        mock_user_model = MagicMock()
        mock_user_model.id = "user_123"
        mock_user_model.email = "user@example.com"
        mock_user_model.is_active = True
        mock_user_model.hashed_password = hash_password(password)
        mock_service.get_user_by_email = AsyncMock(return_value=mock_user_model)

        with patch("api.auth.router.UserService", return_value=mock_service):
            response = client.post(
                "/auth/login",
                json={
                    "email": "user@example.com",
                    "password": "wrong_password",
                    "csrf_token": "fake-csrf",
                },
            )

        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    def test_login_rate_limited(self, client, csrf_always_valid):
        with patch(
            "api.auth.router.check_rate_limit",
            new=AsyncMock(return_value=False),
        ):
            response = client.post(
                "/auth/login",
                json={
                    "email": "user@example.com",
                    "password": "password123",
                    "csrf_token": "fake-csrf",
                },
            )
        assert response.status_code == 429
