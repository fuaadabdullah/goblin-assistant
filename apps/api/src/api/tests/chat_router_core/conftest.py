"""Shared fixtures for chat_router core tests."""

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.auth.router import get_current_user
from api.chat_router import router


def _payload(response):
    body = response.json()
    return body["data"] if isinstance(body, dict) and "data" in body else body


@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    return MagicMock(id="user_123", email="test@example.com")


@pytest.fixture
def app(mock_user):
    """FastAPI app wired with the chat router and an auth override.

    Uses `dependency_overrides` (the FastAPI-blessed pattern) rather than
    monkeypatching the module attribute — `Depends(get_current_user)`
    captures the function at registration, so attribute patches don't
    actually take effect.
    """
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: mock_user
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)
