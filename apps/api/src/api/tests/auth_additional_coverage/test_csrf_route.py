"""Csrf Route auth coverage tests."""

from unittest.mock import AsyncMock

import pytest

from api.auth.router import routes_csrf


class TestCsrfRoute:
    @pytest.mark.asyncio
    async def test_get_csrf_token_wraps_generated_value(self, monkeypatch):
        monkeypatch.setattr(routes_csrf, "generate_csrf_token", AsyncMock(return_value="csrf-123"))

        response = await routes_csrf.get_csrf_token()

        assert response.csrf_token == "csrf-123"
