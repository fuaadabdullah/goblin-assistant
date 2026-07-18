"""Google Oauth Helpers auth coverage tests."""

from types import SimpleNamespace

import pytest

from api.auth import oauth as oauth_module
from api.auth.oauth import GoogleOAuth

from .conftest import _async_client_factory


class TestGoogleOAuthHelpers:
    def test_get_authorization_url_uses_given_state(self, monkeypatch):
        monkeypatch.setattr(oauth_module, "GOOGLE_CLIENT_ID", "client-id")
        monkeypatch.setattr(oauth_module, "GOOGLE_REDIRECT_URI", "https://app/callback")

        url = GoogleOAuth.get_authorization_url(state="fixed-state")

        assert "client_id=client-id" in url
        assert "redirect_uri=https%3A%2F%2Fapp%2Fcallback" in url
        assert "scope=openid+email" in url
        assert "state=fixed-state" in url

    def test_get_authorization_url_requires_client_id(self, monkeypatch):
        monkeypatch.setattr(oauth_module, "GOOGLE_CLIENT_ID", None)

        with pytest.raises(ValueError, match="GOOGLE_CLIENT_ID"):
            GoogleOAuth.get_authorization_url()

    @pytest.mark.asyncio
    async def test_exchange_code_for_token_success(self, monkeypatch):
        monkeypatch.setattr(oauth_module, "GOOGLE_CLIENT_ID", "client-id")
        monkeypatch.setattr(oauth_module, "GOOGLE_CLIENT_SECRET", "client-secret")
        response = SimpleNamespace(status_code=200, json=lambda: {"access_token": "token"})
        monkeypatch.setattr(
            oauth_module.httpx,
            "AsyncClient",
            _async_client_factory(response),
        )

        result = await GoogleOAuth.exchange_code_for_token("code-123")

        assert result == {"access_token": "token"}

    @pytest.mark.asyncio
    async def test_exchange_code_for_token_failure_and_exception(self, monkeypatch):
        monkeypatch.setattr(oauth_module, "GOOGLE_CLIENT_ID", "client-id")
        monkeypatch.setattr(oauth_module, "GOOGLE_CLIENT_SECRET", "client-secret")
        failure = SimpleNamespace(status_code=400, text="bad request")
        monkeypatch.setattr(
            oauth_module.httpx,
            "AsyncClient",
            _async_client_factory(failure, RuntimeError("boom")),
        )

        assert await GoogleOAuth.exchange_code_for_token("bad-code") is None
        assert await GoogleOAuth.exchange_code_for_token("bad-code") is None

    @pytest.mark.asyncio
    async def test_verify_token_and_get_user_info(self, monkeypatch):
        token_ok = SimpleNamespace(status_code=200, json=lambda: {"sub": "google-user"})
        token_bad = SimpleNamespace(status_code=401, json=lambda: {})
        user_ok = SimpleNamespace(status_code=200, json=lambda: {"email": "user@example.com"})
        user_bad = SimpleNamespace(status_code=403, json=lambda: {})
        monkeypatch.setattr(
            oauth_module.httpx,
            "AsyncClient",
            _async_client_factory(token_ok, token_bad, user_ok, user_bad),
        )

        assert await GoogleOAuth.verify_token("access-token") == {"sub": "google-user"}
        assert await GoogleOAuth.verify_token("bad-token") is None
        assert await GoogleOAuth.get_user_info("access-token") == {"email": "user@example.com"}
        assert await GoogleOAuth.get_user_info("bad-token") is None
