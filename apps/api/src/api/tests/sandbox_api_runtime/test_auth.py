"""Auth sandbox API runtime tests."""

import os
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from .conftest import sandbox_api


def test_require_api_key_fails_closed_when_key_missing() -> None:
    with (
        patch.object(sandbox_api, "SANDBOX_ENABLED", False),
        patch.object(sandbox_api, "API_KEY", None),
        pytest.raises(HTTPException) as exc,
    ):
        sandbox_api.require_api_key("any-key")

    assert exc.value.status_code == 500
    assert "API_AUTH_KEY" in str(exc.value.detail)


def test_require_api_key_validates_when_key_configured() -> None:
    with (
        patch.object(sandbox_api, "SANDBOX_ENABLED", False),
        patch.object(sandbox_api, "API_KEY", "secret"),
    ):
        with pytest.raises(HTTPException) as exc:
            sandbox_api.require_api_key("wrong")
        sandbox_api.require_api_key("secret")

    assert exc.value.status_code in (401, 403)


def test_require_api_key_skips_auth_in_development_when_enabled() -> None:
    with (
        patch.object(sandbox_api, "SANDBOX_ENABLED", True),
        patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=False),
    ):
        sandbox_api.require_api_key("anything")
