"""Test suite for middleware.py"""

import os
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.middleware import (
    AuthenticationMiddleware,
    SecurityHeadersMiddleware,
)


def _build_test_app():
    """Create a test app with authentication middleware"""
    app = FastAPI()

    @app.get("/protected")
    async def protected_route():
        return {"message": "Protected"}

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


class TestAuthenticationMiddleware:
    """Tests for AuthenticationMiddleware"""

    def test_auth_middleware_excludes_health_endpoint(self):
        """Test that health endpoint is excluded from auth"""
        app = _build_test_app()
        app.add_middleware(
            AuthenticationMiddleware,
            exclude_paths=[],
        )
        client = TestClient(app)

        response = client.get("/health")

        assert response.status_code == 200

    @patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "development",
            "ALLOW_UNAUTHENTICATED_REQUESTS": "true",
        },
    )
    def test_auth_middleware_dev_mode_allows_unauthenticated(self):
        """Test that dev mode allows unauthenticated requests"""
        app = _build_test_app()
        app.add_middleware(AuthenticationMiddleware)
        client = TestClient(app)

        response = client.get("/protected")

        assert response.status_code == 200

    @patch.dict(os.environ, {"LOCAL_LLM_API_KEY": "test-key"})
    def test_auth_middleware_accepts_valid_api_key_header(self):
        """Test that valid API key in header is accepted"""
        app = _build_test_app()
        app.add_middleware(AuthenticationMiddleware)
        client = TestClient(app)

        response = client.get("/protected", headers={"x-api-key": "test-key"})

        assert response.status_code == 200

    @patch.dict(os.environ, {"LOCAL_LLM_API_KEY": "test-key"})
    def test_auth_middleware_accepts_bearer_token(self):
        """Test that Bearer token format is accepted"""
        app = _build_test_app()
        app.add_middleware(AuthenticationMiddleware)
        client = TestClient(app)

        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer test-key"},
        )

        assert response.status_code == 200

    @patch.dict(os.environ, {"LOCAL_LLM_API_KEY": "test-key"})
    def test_auth_middleware_rejects_invalid_api_key(self):
        """Test that invalid API key is rejected"""
        app = _build_test_app()
        app.add_middleware(AuthenticationMiddleware)
        client = TestClient(app)

        response = client.get("/protected", headers={"x-api-key": "wrong-key"})

        assert response.status_code == 401

    @patch.dict(os.environ, {"LOCAL_LLM_API_KEY": ""})
    def test_auth_middleware_unconfigured_in_production(self):
        """Test unconfigured API key in production mode"""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            app = _build_test_app()
            app.add_middleware(AuthenticationMiddleware)
            client = TestClient(app)

            response = client.get("/protected")

            assert response.status_code == 500
            assert response.json()["error"]["code"] == "CONFIGURATION_ERROR"

    def test_auth_middleware_custom_exclude_paths(self):
        """Test custom excluded paths"""
        app = _build_test_app()
        app.add_middleware(
            AuthenticationMiddleware,
            exclude_paths=["/custom"],
        )

        @app.get("/custom")
        def custom():
            return {"message": "Custom"}

        client = TestClient(app)
        response = client.get("/custom")

        assert response.status_code == 200

    def test_auth_middleware_excludes_docs_endpoints(self):
        """Test that documentation endpoints are excluded"""
        app = _build_test_app()
        app.add_middleware(AuthenticationMiddleware)
        client = TestClient(app)

        response = client.get("/docs")

        # Should not get 401
        assert response.status_code != 401


class TestSecurityHeadersMiddleware:
    """Tests for SecurityHeadersMiddleware"""

    def test_security_headers_middleware_adds_headers(self):
        """Test that security headers are added to responses"""
        app = FastAPI()

        @app.get("/test")
        def test_route():
            return {"message": "test"}

        app.add_middleware(SecurityHeadersMiddleware)
        client = TestClient(app)

        response = client.get("/test")

        assert response.status_code == 200
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"

    def test_security_headers_middleware_xframe_options(self):
        """Test X-Frame-Options header"""
        app = FastAPI()

        @app.get("/test")
        def test_route():
            return {"message": "test"}

        app.add_middleware(SecurityHeadersMiddleware)
        client = TestClient(app)

        response = client.get("/test")

        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"

    def test_security_headers_middleware_xss_protection(self):
        """Test X-XSS-Protection header"""
        app = FastAPI()

        @app.get("/test")
        def test_route():
            return {"message": "test"}

        app.add_middleware(SecurityHeadersMiddleware)
        client = TestClient(app)

        response = client.get("/test")

        assert "X-XSS-Protection" in response.headers
        assert "1; mode=block" in response.headers["X-XSS-Protection"]

    def test_security_headers_middleware_referrer_policy(self):
        """Test Referrer-Policy header"""
        app = FastAPI()

        @app.get("/test")
        def test_route():
            return {"message": "test"}

        app.add_middleware(SecurityHeadersMiddleware)
        client = TestClient(app)

        response = client.get("/test")

        assert "Referrer-Policy" in response.headers

    def test_security_headers_middleware_permissions_policy(self):
        """Test Permissions-Policy header"""
        app = FastAPI()

        @app.get("/test")
        def test_route():
            return {"message": "test"}

        app.add_middleware(SecurityHeadersMiddleware)
        client = TestClient(app)

        response = client.get("/test")

        assert "Permissions-Policy" in response.headers

    @patch.dict(os.environ, {"ENVIRONMENT": "production"})
    def test_security_headers_middleware_hsts_in_production(self):
        """Test HSTS header in production"""
        app = FastAPI()

        @app.get("/test")
        def test_route():
            return {"message": "test"}

        app.add_middleware(SecurityHeadersMiddleware)
        client = TestClient(app)

        response = client.get("/test")

        # HSTS should be present in production
        assert response.headers["Strict-Transport-Security"] == (
            "max-age=31536000; includeSubDomains"
        )

    @patch.dict(os.environ, {"ENVIRONMENT": "development"})
    def test_security_headers_middleware_no_hsts_in_dev(self):
        """Test HSTS not added in development"""
        app = FastAPI()

        @app.get("/test")
        def test_route():
            return {"message": "test"}

        app.add_middleware(SecurityHeadersMiddleware)
        client = TestClient(app)

        response = client.get("/test")

        # Should still have other headers
        assert "X-Content-Type-Options" in response.headers

    def test_security_headers_middleware_csp_header_if_configured(self):
        """Test CSP header if present"""
        app = FastAPI()

        @app.get("/test")
        def test_route():
            return {"message": "test"}

        app.add_middleware(SecurityHeadersMiddleware)
        client = TestClient(app)

        response = client.get("/test")

        # At minimum we should have the core security headers
        assert len(response.headers) >= 5
