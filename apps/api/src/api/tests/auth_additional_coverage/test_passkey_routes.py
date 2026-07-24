"""Passkey Routes auth coverage tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, Response

from api.auth.router import routes_passkey
from api.auth.router.schemas import PasskeyAuthRequest, PasskeyRegistrationRequest

from .conftest import _user_model


class TestPasskeyRoutes:
    @pytest.mark.asyncio
    async def test_passkey_register_and_auth_paths(self, monkeypatch):
        user = _user_model(
            passkey_credential_id="cred-1",
            passkey_public_key="pub-1",
        )
        user_service = MagicMock()
        user_service.get_user_by_email = AsyncMock(side_effect=[None, user, user, user, user])
        user_service.update_user = AsyncMock()
        user_service.update_user_last_login = AsyncMock()
        monkeypatch.setattr(routes_passkey._ar, "UserService", lambda _db: user_service)

        with pytest.raises(HTTPException, match="User not found"):
            await routes_passkey.register_passkey(
                PasskeyRegistrationRequest(
                    email="missing@example.com",
                    credential_id="cred",
                    public_key="pub",
                ),
                MagicMock(),
            )

        result = await routes_passkey.register_passkey(
            PasskeyRegistrationRequest(
                email="user@example.com",
                credential_id="cred-2",
                public_key="pub-2",
            ),
            MagicMock(),
        )
        assert result["message"] == "Passkey registered successfully"

        with pytest.raises(HTTPException, match="Invalid credential ID"):
            await routes_passkey.authenticate_passkey(
                PasskeyAuthRequest(
                    email="user@example.com",
                    credential_id="wrong",
                    authenticator_data="auth",
                    client_data_json="client",
                    signature="sig",
                ),
                Response(),
                MagicMock(),
            )

        inactive = _user_model(
            passkey_credential_id="cred-1",
            passkey_public_key="pub-1",
            is_active=False,
        )
        user_service.get_user_by_email = AsyncMock(side_effect=[inactive, user, user])
        with pytest.raises(HTTPException, match="inactive"):
            await routes_passkey.authenticate_passkey(
                PasskeyAuthRequest(
                    email="inactive@example.com",
                    credential_id="cred-1",
                    authenticator_data="auth",
                    client_data_json="client",
                    signature="sig",
                ),
                Response(),
                MagicMock(),
            )

        with pytest.raises(HTTPException, match="Invalid passkey authentication data"):
            await routes_passkey.authenticate_passkey(
                PasskeyAuthRequest(
                    email="user@example.com",
                    credential_id="cred-1",
                    authenticator_data="",
                    client_data_json="client",
                    signature="sig",
                ),
                Response(),
                MagicMock(),
            )

        monkeypatch.setattr(routes_passkey, "create_session_id", lambda _uid: "session-1")
        monkeypatch.setattr(routes_passkey, "_db_create_session", AsyncMock())
        monkeypatch.setattr(routes_passkey, "create_access_token", lambda **_kwargs: "access-token")
        monkeypatch.setattr(routes_passkey, "create_refresh_token", lambda *_args: "refresh-token")
        set_cookies = MagicMock()
        monkeypatch.setattr(routes_passkey, "_set_auth_cookies", set_cookies)

        success = await routes_passkey.authenticate_passkey(
            PasskeyAuthRequest(
                email="user@example.com",
                credential_id="cred-1",
                authenticator_data="auth",
                client_data_json="client",
                signature="sig",
            ),
            Response(),
            MagicMock(),
        )

        assert success.data.access_token == "access-token"
        assert set_cookies.called
        assert (await routes_passkey.get_passkey_challenge())["challenge"]
