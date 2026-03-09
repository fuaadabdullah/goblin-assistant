"""
Security tests for authentication endpoints (CSRF, rate limiting)
and sandbox restrictions (bash removal).

This test suite validates:
1. CSRF tokens are required (not optional) on /register and /login
2. CSRF tokens are validated and one-time use
3. Rate limiting is enforced per IP
4. Bash language is removed from sandbox
"""


class TestCSRFProtection:
    """Test CSRF token enforcement on auth endpoints"""

    def test_csrf_token_endpoint_returns_valid_token(self, client):
        """GET /auth/csrf-token should return a valid CSRF token"""
        response = client.get("/auth/csrf-token")
        assert response.status_code == 200
        data = response.json()
        assert "csrf_token" in data
        assert isinstance(data["csrf_token"], str)
        assert len(data["csrf_token"]) > 20  # Should be a secure token

    def test_register_requires_csrf_token(self, client):
        """POST /auth/register without csrf_token should fail (field is required)"""
        response = client.post(
            "/auth/register",
            json={
                "email": "test@example.com",
                "password": "TestPassword123!",
                "name": "Test User",
                # Missing csrf_token field
            },
        )
        # Should fail validation because csrf_token is now required
        assert response.status_code == 422  # Unprocessable Entity (validation error)
        data = response.json()
        assert "detail" in data  # Validation error details

    def test_login_requires_csrf_token(self, client):
        """POST /auth/login without csrf_token should fail (field is required)"""
        response = client.post(
            "/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPassword123!",
                # Missing csrf_token field
            },
        )
        # Should fail validation because csrf_token is now required
        assert response.status_code == 422  # Unprocessable Entity (validation error)
        data = response.json()
        assert "detail" in data  # Validation error details

    def test_register_invalid_csrf_token_rejected(self, client):
        """POST /auth/register with invalid csrf_token should fail with 403"""
        response = client.post(
            "/auth/register",
            json={
                "email": "test@example.com",
                "password": "TestPassword123!",
                "name": "Test User",
                "csrf_token": "invalid_token_that_does_not_exist",
            },
        )
        assert response.status_code == 403
        data = response.json()
        assert "CSRF" in data["detail"]

    def test_login_invalid_csrf_token_rejected(self, client):
        """POST /auth/login with invalid csrf_token should fail with 403"""
        response = client.post(
            "/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPassword123!",
                "csrf_token": "invalid_token_that_does_not_exist",
            },
        )
        assert response.status_code == 403
        data = response.json()
        assert "CSRF" in data["detail"]

    def test_csrf_token_one_time_use(self, client):
        """
        CSRF token should be one-time use.
        After successful validation, reusing the same token should fail.
        """
        # Get a valid CSRF token
        csrf_response = client.get("/auth/csrf-token")
        csrf_token = csrf_response.json()["csrf_token"]

        # First use: should be rejected due to user not existing (but CSRF token should be consumed)
        response1 = client.post(
            "/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "WrongPassword123!",
                "csrf_token": csrf_token,
            },
        )
        # Should fail with 401 (unauthorized, user not found) or 403 (CSRF)
        assert response1.status_code in [401, 403]

        # Second use: Try to reuse the same token - should always fail with 403 CSRF
        response2 = client.post(
            "/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "WrongPassword123!",
                "csrf_token": csrf_token,  # Reusing the same token
            },
        )
        # Should definitely fail with 403 because token is already used
        assert response2.status_code == 403
        data = response2.json()
        assert "CSRF" in data["detail"]

    def test_csrf_token_expiration(self, client):
        """CSRF tokens should expire after 1 hour (this tests the TTL behavior)"""
        # Note: Full expiration test requires mocking time or waiting 1 hour
        # This is a placeholder for integration testing
        # In practice, this would be tested with clock mocking or in E2E tests
        pass


class TestRateLimiting:
    """Test rate limiting on auth endpoints"""

    def test_rate_limit_on_login_attempts(self, client):
        """
        After 5 failed login attempts from same IP, subsequent attempts
        should return 429 (Too Many Requests)
        """
        # Get 5 CSRF tokens for 5 attempts
        tokens = []
        for _ in range(5):
            csrf_response = client.get("/auth/csrf-token")
            tokens.append(csrf_response.json()["csrf_token"])

        # Make 5 failed login attempts
        for token in tokens:
            response = client.post(
                "/auth/login",
                json={
                    "email": "nonexistent@example.com",
                    "password": "WrongPassword123!",
                    "csrf_token": token,
                },
            )
            # Should fail with 401 (user not found) for first 5 attempts
            assert response.status_code == 401

        # 6th attempt should be rate limited (429)
        csrf_response = client.get("/auth/csrf-token")
        sixth_token = csrf_response.json()["csrf_token"]

        response = client.post(
            "/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "WrongPassword123!",
                "csrf_token": sixth_token,
            },
        )
        assert response.status_code == 429
        data = response.json()
        assert "rate" in data["detail"].lower() or "too many" in data["detail"].lower()

    def test_rate_limit_on_registration_attempts(self, client):
        """
        After 5 failed registration attempts from same IP, subsequent attempts
        should return 429 (Too Many Requests)
        """
        # Get 5 CSRF tokens for 5 attempts
        tokens = []
        for _ in range(5):
            csrf_response = client.get("/auth/csrf-token")
            tokens.append(csrf_response.json()["csrf_token"])

        # Make 5 failed registration attempts with invalid data
        for i, token in enumerate(tokens):
            response = client.post(
                "/auth/register",
                json={
                    "email": f"test{i}@example.com",
                    "password": "TestPassword123!",
                    "name": "Test User",
                    "csrf_token": token,
                },
            )
            # First 5 should fail with various errors but NOT 429
            assert response.status_code != 429

        # 6th attempt should be rate limited (429)
        csrf_response = client.get("/auth/csrf-token")
        sixth_token = csrf_response.json()["csrf_token"]

        response = client.post(
            "/auth/register",
            json={
                "email": "test6@example.com",
                "password": "TestPassword123!",
                "name": "Test User",
                "csrf_token": sixth_token,
            },
        )
        assert response.status_code == 429
        data = response.json()
        assert "rate" in data["detail"].lower() or "too many" in data["detail"].lower()


class TestSandboxSecurity:
    """Test sandbox endpoint restrictions and security"""

    def test_sandbox_bash_not_supported(self, client):
        """POST /sandbox/submit with language='bash' should return 400"""
        response = client.post(
            "/sandbox/submit",
            json={
                "language": "bash",
                "source": "echo 'hello'",
                "timeout": 10,
            },
            headers={"X-API-Key": "devkey"},
        )
        # Should fail because bash is not in supported languages
        assert response.status_code == 400
        data = response.json()
        assert "unsupported" in data["detail"].lower() or "bash" in data["detail"].lower()
        assert "python" in data["detail"].lower() or "javascript" in data["detail"].lower()

    def test_sandbox_python_still_supported(self, client):
        """POST /sandbox/submit with language='python' should not reject based on language"""
        # Note: Might fail for other reasons (sandbox disabled, auth, etc.)
        # But should NOT fail with "unsupported language"
        response = client.post(
            "/sandbox/submit",
            json={
                "language": "python",
                "source": "print('hello')",
                "timeout": 10,
            },
            headers={"X-API-Key": "devkey"},
        )
        # Should not fail because of unsupported language
        data = response.json()
        if response.status_code == 400:
            detail = data.get("detail", "").lower()
            assert "unsupported language" not in detail, "Python should still be supported"

    def test_sandbox_javascript_still_supported(self, client):
        """POST /sandbox/submit with language='javascript' should not reject based on language"""
        response = client.post(
            "/sandbox/submit",
            json={
                "language": "javascript",
                "source": "console.log('hello')",
                "timeout": 10,
            },
            headers={"X-API-Key": "devkey"},
        )
        # Should not fail because of unsupported language
        data = response.json()
        if response.status_code == 400:
            detail = data.get("detail", "").lower()
            assert "unsupported language" not in detail, "JavaScript should still be supported"

    def test_sandbox_invalid_language_rejected(self, client):
        """POST /sandbox/submit with invalid language should return 400"""
        response = client.post(
            "/sandbox/submit",
            json={
                "language": "ruby",
                "source": "puts 'hello'",
                "timeout": 10,
            },
            headers={"X-API-Key": "devkey"},
        )
        assert response.status_code == 400
        data = response.json()
        assert "unsupported" in data["detail"].lower()
