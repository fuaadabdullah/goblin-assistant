"""
Integration tests for secrets_router.

Mounts the real router on a test app with explicit dependency handling.
Tests exact status codes, response shapes, and failure paths.
"""

from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from api.integrations.secrets import (
    SecretBackendError,
    SecretNotFoundError,
    SecretUnauthorizedError,
    SecretValidationError,
)
from api.secrets_router import (
    SecretRequest,
    get_secrets_adapter,
    router,
)

# ── App Builders ────────────────────────────────────────────────────────────


def _build_app_with_working_adapter(
    secrets_data: dict[str, dict[str, str]] | None = None,
) -> FastAPI:
    """FastAPI app with a working mock secrets adapter."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    # Mock adapter that returns secrets
    mock_adapter = AsyncMock()
    secrets_data = secrets_data or {}

    async def mock_list_secrets(prefix: str = "", limit: int = 100):
        return list(secrets_data.keys())

    async def mock_get_secret(path: str, version: int | None = None):
        if path not in secrets_data:
            raise SecretNotFoundError(f"Secret not found: {path}")
        from api.integrations.secrets.models import Secret, SecretMetadata

        return Secret(
            path=path,
            data=secrets_data[path],
            metadata=SecretMetadata(version=1),
        )

    mock_adapter.list_secrets = mock_list_secrets
    mock_adapter.get_secret = mock_get_secret

    app.dependency_overrides[get_secrets_adapter] = lambda: mock_adapter
    return app


def _build_app_with_failed_adapter(error: Exception) -> FastAPI:
    """FastAPI app where get_secrets_adapter raises an exception."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    async def failing_get_adapter():
        raise error

    app.dependency_overrides[get_secrets_adapter] = failing_get_adapter
    return app


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def working_client() -> TestClient:
    """Client with working mock adapter."""
    return TestClient(_build_app_with_working_adapter(), raise_server_exceptions=False)


@pytest.fixture
def unauthorized_client() -> TestClient:
    """Client where adapter raises auth error."""
    return TestClient(
        _build_app_with_failed_adapter(SecretUnauthorizedError("Unauthorized")),
        raise_server_exceptions=False,
    )


@pytest.fixture
def unavailable_client() -> TestClient:
    """Client where adapter is unavailable (503)."""
    return TestClient(
        _build_app_with_failed_adapter(SecretBackendError("Backend unavailable")),
        raise_server_exceptions=False,
    )


# ── List Secrets Tests ──────────────────────────────────────────────────────


class TestListSecrets:
    """GET /api/v1/secrets/ — list all secrets"""

    def test_returns_200_with_secret_list(self, working_client: TestClient) -> None:
        """Authenticated list returns 200 with paths."""
        response = working_client.get("/api/v1/secrets/")
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert "paths" in body
        assert isinstance(body["paths"], list)

    def test_authorization_failure_returns_403(self, unauthorized_client: TestClient) -> None:
        """Unauthorized adapter raises 403 Forbidden."""
        response = unauthorized_client.get("/api/v1/secrets/")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        body = response.json()
        assert "detail" in body
        assert "Unauthorized" in body["detail"]

    def test_backend_unavailable_returns_503(self, unavailable_client: TestClient) -> None:
        """Unavailable backend raises 503 Service Unavailable."""
        response = unavailable_client.get("/api/v1/secrets/")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        body = response.json()
        assert "detail" in body

    def test_respects_prefix_parameter(self, working_client: TestClient) -> None:
        """List endpoint filters by prefix."""
        response = working_client.get("/api/v1/secrets/?prefix=APP_")
        assert response.status_code == status.HTTP_200_OK

    def test_respects_limit_parameter(self, working_client: TestClient) -> None:
        """List endpoint respects limit parameter."""
        response = working_client.get("/api/v1/secrets/?limit=10")
        assert response.status_code == status.HTTP_200_OK


# ── Get Secret Tests ────────────────────────────────────────────────────────


class TestGetSecret:
    """GET /api/v1/secrets/{path} — retrieve a single secret"""

    def test_returns_200_with_secret_data(self, working_client: TestClient) -> None:
        """Authenticated read returns 200 with secret response."""
        app = _build_app_with_working_adapter({"API_KEY": {"key": "my-secret"}})
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get("/api/v1/secrets/API_KEY")
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["path"] == "API_KEY"
        assert body["data"] == {"key": "my-secret"}
        assert "metadata" in body

    def test_nonexistent_secret_returns_404(self, working_client: TestClient) -> None:
        """Reading nonexistent secret returns 404."""
        response = working_client.get("/api/v1/secrets/DOES_NOT_EXIST")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        body = response.json()
        assert "detail" in body

    def test_authorization_failure_returns_403(self, unauthorized_client: TestClient) -> None:
        """Unauthorized adapter raises 403."""
        response = unauthorized_client.get("/api/v1/secrets/ANY_KEY")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_backend_unavailable_returns_503(self, unavailable_client: TestClient) -> None:
        """Unavailable backend raises 503."""
        response = unavailable_client.get("/api/v1/secrets/ANY_KEY")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


# ── Put Secret Tests ────────────────────────────────────────────────────────


class TestPutSecret:
    """PUT /api/v1/secrets/{path} — create or update a secret"""

    def test_creates_secret_returns_200(self, working_client: TestClient) -> None:
        """Creating a new secret returns 200."""
        response = working_client.put(
            "/api/v1/secrets/NEW_SECRET",
            json=SecretRequest(
                path="NEW_SECRET",
                data={"password": "secret123"},
            ).model_dump(),
        )
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["path"] == "NEW_SECRET"

    def test_path_mismatch_returns_400(self, working_client: TestClient) -> None:
        """Path in URL must match path in body."""
        response = working_client.put(
            "/api/v1/secrets/URL_PATH",
            json=SecretRequest(
                path="BODY_PATH",  # Mismatch!
                data={"password": "secret123"},
            ).model_dump(),
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        body = response.json()
        assert "Path in request body must match URL path" in body["detail"]

    def test_validation_error_returns_422(self) -> None:
        """Invalid request body returns 422 Unprocessable Entity."""
        app = _build_app_with_working_adapter()
        # Mock adapter to raise validation error
        mock_adapter = AsyncMock()
        mock_adapter.put_secret = AsyncMock(
            side_effect=SecretValidationError("Invalid secret format")
        )
        app.dependency_overrides[get_secrets_adapter] = lambda: mock_adapter
        client = TestClient(app, raise_server_exceptions=False)

        response = client.put(
            "/api/v1/secrets/TEST",
            json=SecretRequest(
                path="TEST",
                data={"key": ""},  # Empty value
            ).model_dump(),
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_authorization_failure_returns_403(self, unauthorized_client: TestClient) -> None:
        """Unauthorized adapter raises 403."""
        response = unauthorized_client.put(
            "/api/v1/secrets/TEST",
            json=SecretRequest(
                path="TEST",
                data={"key": "value"},
            ).model_dump(),
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_backend_unavailable_returns_503(self, unavailable_client: TestClient) -> None:
        """Unavailable backend raises 503."""
        response = unavailable_client.put(
            "/api/v1/secrets/TEST",
            json=SecretRequest(
                path="TEST",
                data={"key": "value"},
            ).model_dump(),
        )
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


# ── Delete Secret Tests ─────────────────────────────────────────────────────


class TestDeleteSecret:
    """DELETE /api/v1/secrets/{path} — delete a secret"""

    def test_deletes_secret_returns_200(self, working_client: TestClient) -> None:
        """Deleting a secret returns 200 with confirmation."""
        mock_adapter = AsyncMock()
        mock_adapter.delete_secret = AsyncMock()
        app = _build_app_with_working_adapter()
        app.dependency_overrides[get_secrets_adapter] = lambda: mock_adapter
        client = TestClient(app, raise_server_exceptions=False)

        response = client.delete("/api/v1/secrets/API_KEY")
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert "message" in body
        assert "deleted" in body["message"].lower()

    def test_nonexistent_secret_returns_404(self) -> None:
        """Deleting nonexistent secret returns 404."""
        mock_adapter = AsyncMock()
        mock_adapter.delete_secret = AsyncMock(side_effect=SecretNotFoundError("Secret not found"))
        app = _build_app_with_working_adapter()
        app.dependency_overrides[get_secrets_adapter] = lambda: mock_adapter
        client = TestClient(app, raise_server_exceptions=False)

        response = client.delete("/api/v1/secrets/DOES_NOT_EXIST")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_authorization_failure_returns_403(self, unauthorized_client: TestClient) -> None:
        """Unauthorized adapter raises 403."""
        response = unauthorized_client.delete("/api/v1/secrets/API_KEY")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_backend_unavailable_returns_503(self, unavailable_client: TestClient) -> None:
        """Unavailable backend raises 503."""
        response = unavailable_client.delete("/api/v1/secrets/API_KEY")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


# ── Router Registration Tests ───────────────────────────────────────────────


def test_router_registered_endpoints() -> None:
    """Verify the router registers all expected endpoints."""
    routes = {(r.path, frozenset(r.methods or [])) for r in router.routes}

    # Check list endpoint (GET /, PUT /)
    assert any(r[0] == "/" and "GET" in r[1] for r in routes), "Missing GET /"
    assert any(r[0] == "/" and "PUT" in r[1] for r in routes), "Missing PUT /"

    # Check detail endpoint (GET /{path}, DELETE /{path})
    assert any(r[0] == "/{path:path}" and "GET" in r[1] for r in routes), "Missing GET /{path}"
    assert any(r[0] == "/{path:path}" and "DELETE" in r[1] for r in routes), (
        "Missing DELETE /{path}"
    )

    # Check rotate endpoint
    assert any("rotate" in r[0] and "POST" in r[1] for r in routes), "Missing POST /rotate"
