"""Focused tests for ErrorHandlingMiddleware."""

from __future__ import annotations

import os
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.middleware import ErrorHandlingMiddleware


def _client(app: FastAPI) -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def test_error_handling_middleware_adds_request_metadata_headers() -> None:
    app = FastAPI()

    @app.get("/ok")
    async def ok():
        return {"message": "ok"}

    app.add_middleware(ErrorHandlingMiddleware)
    client = _client(app)

    response = client.get("/ok")

    assert response.status_code == 200
    assert response.headers["X-Request-ID"]


@patch.dict(os.environ, {"DEBUG": "false"})
def test_error_handling_middleware_hides_error_details_by_default() -> None:
    app = FastAPI()

    @app.get("/boom")
    async def boom():
        raise RuntimeError("kaboom")

    app.add_middleware(ErrorHandlingMiddleware)
    client = _client(app)

    response = client.get("/boom")

    assert response.status_code == 500
    data = response.json()["error"]
    assert data["code"] == "internal_server_error"
    assert data["message"] == "An internal server error occurred"
    assert data["type"] == "RuntimeError"
    assert data["request_id"]


@patch.dict(os.environ, {"DEBUG": "true"})
def test_error_handling_middleware_exposes_debug_details() -> None:
    app = FastAPI()

    @app.get("/boom")
    async def boom():
        raise ValueError("debug boom")

    app.add_middleware(ErrorHandlingMiddleware)
    client = _client(app)

    response = client.get("/boom")

    assert response.status_code == 500
    assert response.json()["error"]["message"] == "debug boom"
