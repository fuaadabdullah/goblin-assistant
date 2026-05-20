"""Tests for the GDPR/CCPA privacy router endpoints.

Strategy
--------
The api/tests/conftest.py pre-stubs ``api.routes.privacy`` with an empty router
to prevent the main-app import from loading heavy dependencies at session startup.
We remove that stub here, load the **real** privacy module, and mount it on an
isolated FastAPI app so we can exercise every endpoint without touching the full
application stack.

Env-var note: ``JWT_SECRET_KEY`` must exist before ``api.auth.router`` is
imported (it raises ValueError otherwise).  We set a test-only value via
os.environ.setdefault so that production secrets are never overwritten.
"""

import importlib
import os
import sys
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Bootstrap: ensure auth router can be imported without raising.
# ---------------------------------------------------------------------------
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-privacy-router-tests-only")

# ---------------------------------------------------------------------------
# Remove the conftest stub and load the REAL privacy module.
# The stub is set in api/tests/conftest.py at import time; without this pop
# importlib would just return the stub again.
# ---------------------------------------------------------------------------
sys.modules.pop("api.routes.privacy", None)

_privacy_mod = importlib.import_module("api.routes.privacy")
_real_router = _privacy_mod.router

# These imports happen AFTER the env-var is set.
from api.auth.router import get_current_user  # noqa: F401 — used as dependency_overrides key
from api.storage.database import get_db  # noqa: F401 — used as dependency_overrides key


# ---------------------------------------------------------------------------
# Shared DB stub — prevents SQLite file creation during tests.
# ---------------------------------------------------------------------------
async def _stub_db() -> AsyncGenerator[Any, None]:
    yield MagicMock()


# ---------------------------------------------------------------------------
# App factories
# ---------------------------------------------------------------------------

def _build_auth_app(user_id: str = "u-privacy-test") -> FastAPI:
    """FastAPI app with the privacy router and auth bypassed."""
    app = FastAPI()
    app.include_router(_real_router)

    # Return a plain string — the privacy router declares `user_id: str = Depends(...)`.
    async def _auth_override() -> str:
        return user_id

    app.dependency_overrides[get_current_user] = _auth_override
    # get_db is not needed for authenticated requests (auth override skips it),
    # but we stub it so any handler that instantiates its own stores still works.
    app.dependency_overrides[get_db] = _stub_db
    return app


def _build_anon_app() -> FastAPI:
    """FastAPI app with privacy router but NO auth override — triggers 401."""
    app = FastAPI()
    app.include_router(_real_router)
    # Still stub get_db so the real get_current_user can resolve its dependency
    # without touching the filesystem.
    app.dependency_overrides[get_db] = _stub_db
    return app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def auth_client() -> TestClient:
    return TestClient(_build_auth_app(), raise_server_exceptions=False)


@pytest.fixture(scope="module")
def anon_client() -> TestClient:
    return TestClient(_build_anon_app(), raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Export endpoint (POST /api/privacy/export)
# ---------------------------------------------------------------------------

def test_data_export_returns_200(auth_client: TestClient) -> None:
    """Authenticated POST /api/privacy/export must return 200."""
    response = auth_client.post("/api/privacy/export")
    assert response.status_code == 200
    body = response.json()
    assert "user_id" in body
    assert "exported_at" in body
    assert "data" in body


def test_data_export_contains_correct_user(auth_client: TestClient) -> None:
    """The export payload must reflect the authenticated user's ID."""
    response = auth_client.post("/api/privacy/export")
    assert response.status_code == 200
    assert response.json()["user_id"] == "u-privacy-test"


def test_data_export_without_vectors_or_conversations(auth_client: TestClient) -> None:
    """Optional sections can be disabled via query params."""
    response = auth_client.post(
        "/api/privacy/export",
        params={
            "include_vectors": "false",
            "include_conversations": "false",
            "include_preferences": "false",
        },
    )
    assert response.status_code == 200
    assert response.json()["data"] == {}


def test_data_export_requires_auth(anon_client: TestClient) -> None:
    """POST /api/privacy/export must reject unauthenticated requests."""
    response = anon_client.post("/api/privacy/export")
    assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Delete endpoint (DELETE /api/privacy/delete)
# ---------------------------------------------------------------------------

def test_data_delete_requires_auth(anon_client: TestClient) -> None:
    """DELETE /api/privacy/delete must reject unauthenticated requests."""
    response = anon_client.delete("/api/privacy/delete")
    assert response.status_code in (401, 403)


def test_data_delete_requires_confirm_flag(auth_client: TestClient) -> None:
    """DELETE without confirm=true must return 400, not silently erase data."""
    response = auth_client.delete("/api/privacy/delete")
    assert response.status_code == 400


def test_data_delete_confirm_false_returns_400(auth_client: TestClient) -> None:
    """Explicit confirm=false must also return 400."""
    response = auth_client.delete("/api/privacy/delete", params={"confirm": "false"})
    assert response.status_code == 400


def test_data_delete_with_confirm_returns_200(auth_client: TestClient) -> None:
    """DELETE with confirm=true must return 200 with a success payload."""
    response = auth_client.delete("/api/privacy/delete", params={"confirm": "true"})
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "deleted_items" in body
    assert "deleted_at" in body


# ---------------------------------------------------------------------------
# Data-summary endpoint (GET /api/privacy/data-summary)
# ---------------------------------------------------------------------------

def test_data_summary_returns_200(auth_client: TestClient) -> None:
    """GET /api/privacy/data-summary must return 200 with the expected shape."""
    response = auth_client.get("/api/privacy/data-summary")
    assert response.status_code == 200
    body = response.json()
    assert "user_id" in body
    assert "data_summary" in body


def test_data_summary_requires_auth(anon_client: TestClient) -> None:
    """GET /api/privacy/data-summary must reject unauthenticated requests."""
    response = anon_client.get("/api/privacy/data-summary")
    assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# RAG consent endpoint (POST /api/privacy/consent/rag)
# ---------------------------------------------------------------------------

def test_rag_consent_grant_returns_200(auth_client: TestClient) -> None:
    """POST /api/privacy/consent/rag?consent_given=true must return 200."""
    with patch("api.storage.preferences_service.preferences_service") as mock_prefs:
        mock_prefs.update_rag_consent = AsyncMock()
        response = auth_client.post(
            "/api/privacy/consent/rag",
            params={"consent_given": "true"},
        )
    assert response.status_code == 200
    body = response.json()
    assert "consent_given" in body


def test_rag_consent_revoke_returns_200(auth_client: TestClient) -> None:
    """POST /api/privacy/consent/rag?consent_given=false must return 200."""
    with patch("api.storage.preferences_service.preferences_service") as mock_prefs:
        mock_prefs.update_rag_consent = AsyncMock()
        response = auth_client.post(
            "/api/privacy/consent/rag",
            params={"consent_given": "false"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body.get("consent_given") is False


def test_rag_consent_requires_auth(anon_client: TestClient) -> None:
    """POST /api/privacy/consent/rag must reject unauthenticated requests."""
    response = anon_client.post(
        "/api/privacy/consent/rag",
        params={"consent_given": "true"},
    )
    assert response.status_code in (401, 403)
