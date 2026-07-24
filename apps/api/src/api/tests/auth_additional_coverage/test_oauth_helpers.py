"""Oauth Helpers auth coverage tests."""

import pytest

from api.auth import oauth as oauth_module


class TestOAuthHelpers:
    def test_get_authorization_url_generates_default_state(self, monkeypatch):
        monkeypatch.setattr(oauth_module, "GOOGLE_CLIENT_ID", "client-id")
        monkeypatch.setattr(oauth_module, "GOOGLE_REDIRECT_URI", "https://app/callback")
        monkeypatch.setattr(oauth_module.secrets, "token_urlsafe", lambda _n: "generated-state")

        url = oauth_module.GoogleOAuth.get_authorization_url()

        assert "state=generated-state" in url

    @pytest.mark.asyncio
    async def test_exchange_code_for_token_without_credentials_returns_none(self, monkeypatch):
        monkeypatch.setattr(oauth_module, "GOOGLE_CLIENT_ID", None)
        monkeypatch.setattr(oauth_module, "GOOGLE_CLIENT_SECRET", None)

        assert await oauth_module.GoogleOAuth.exchange_code_for_token("code") is None
