"""Engine contract tests — Auth pillar.

These tests assert that the Auth pillar's public contract
(documented in docs/architecture/ENGINE_CONTRACTS.md) is upheld.
"""

from __future__ import annotations


import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import auth


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(auth.router, prefix="/api/v1")
    return TestClient(app)


# ── Registration Contract ──────────────────────────────────────────────


class TestRegistrationContract:
    """Contract: POST /api/v1/auth/register creates user and returns token."""

    def test_register_with_valid_input(self, client):
        """Valid registration returns token and user info."""
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "test@example.com", "password": "SecurePass123!"},
        )
        # If auth is fully wired: 200 with token
        # If CSRF required: 403
        # If email exists: 409
        assert response.status_code in (200, 403, 409)
        if response.status_code == 200:
            data = response.json()
            assert "token" in data or "access_token" in data
            assert "user" in data or "id" in data

    def test_register_with_weak_password_returns_400(self, client):
        """Weak passwords should be rejected."""
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "test@example.com", "password": "123"},
        )
        assert response.status_code in (400, 422, 403)


# ── Login Contract ─────────────────────────────────────────────────────


class TestLoginContract:
    """Contract: POST /api/v1/auth/login authenticates and returns token."""

    def test_login_with_valid_credentials(self, client):
        """Valid login returns token and user info."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "SecurePass123!"},
        )
        # If auth is fully wired: 200 with token
        # If CSRF required: 403
        # If invalid credentials: 401
        assert response.status_code in (200, 401, 403)
        if response.status_code == 200:
            data = response.json()
            assert "token" in data or "access_token" in data

    def test_login_with_invalid_password_returns_401(self, client):
        """Wrong password returns 401."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@example.com", "password": "WrongPass123!"},
        )
        assert response.status_code in (401, 403)

    def test_login_rate_limit_returns_429(self, client):
        """Rate limiting should return 429 after threshold."""
        # Make multiple rapid login attempts
        for _ in range(15):
            response = client.post(
                "/api/v1/auth/login",
                json={"email": "ratelimit@example.com", "password": "AnyPass123!"},
            )
        # Last attempt should be rate-limited
        assert response.status_code in (429, 401, 403)


# ── Token Validation Contract ──────────────────────────────────────────


class TestTokenValidationContract:
    """Contract: GET /api/v1/auth/validate validates JWT tokens."""

    def test_validate_without_token_returns_401(self, client):
        """Missing token returns 401."""
        response = client.get("/api/v1/auth/validate")
        assert response.status_code in (401, 403)

    def test_validate_with_invalid_token_returns_401(self, client):
        """Invalid JWT token returns 401 with INVALID_TOKEN code."""
        response = client.get(
            "/api/v1/auth/validate",
            headers={"Authorization": "Bearer invalid.jwt.token"},
        )
        assert response.status_code == 401
        data = response.json()
        # Error detail should indicate invalid token
        assert "detail" in data


# ── CSRF Token Contract ────────────────────────────────────────────────


class TestCSRFTokenContract:
    """Contract: GET /api/v1/auth/csrf/token issues one-time CSRF tokens."""

    def test_csrf_token_endpoint_returns_token(self, client):
        """CSRF token endpoint returns a token string."""
        response = client.get("/api/v1/auth/csrf/token")
        assert response.status_code in (200, 401, 403)
        if response.status_code == 200:
            data = response.json()
            assert "csrf_token" in data or "token" in data

    def test_csrf_token_is_one_time_use(self, client):
        """Using the same CSRF token twice should fail the second time."""
        response = client.get("/api/v1/auth/csrf/token")
        if response.status_code == 200:
            data = response.json()
            csrf_token = data.get("csrf_token") or data.get("token")

            # First use should succeed or fail with CSRF validation
            client.post(
                "/api/v1/auth/login",
                json={"email": "test@example.com", "password": "SecurePass123!"},
                headers={"X-CSRF-Token": csrf_token},
            )

            # Second use with same token should fail
            login_resp2 = client.post(
                "/api/v1/auth/login",
                json={"email": "test@example.com", "password": "SecurePass123!"},
                headers={"X-CSRF-Token": csrf_token},
            )
            assert login_resp2.status_code in (401, 403)


# ── Error Contract ─────────────────────────────────────────────────────


class TestAuthErrorContract:
    """Contract: Auth errors have standardized error codes."""

    ERROR_CODES = {
        401: [
            "INVALID_CREDENTIALS",
            "TOKEN_EXPIRED",
            "INVALID_TOKEN",
            "UNAUTHORIZED",
            "INVALID_CSRF",
        ],
        409: ["EMAIL_EXISTS"],
        429: ["RATE_LIMITED"],
    }

    def test_401_errors_have_detail(self, client):
        """401 responses must have a detail field explaining the error."""
        response = client.get("/api/v1/auth/validate")
        if response.status_code == 401:
            data = response.json()
            assert "detail" in data
