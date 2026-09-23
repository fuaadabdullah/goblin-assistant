"""Passkey Routes auth coverage tests (py_webauthn-backed flow)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from webauthn.helpers import bytes_to_base64url

from api.auth.router import routes_passkey
from api.auth.router.schemas import (
    PasskeyAuthRequest,
    PasskeyChallengeRequest,
    PasskeyRegistrationRequest,
)

from .conftest import _user_model

CRED_B64 = bytes_to_base64url(b"cred-1")
PUB_B64 = bytes_to_base64url(b"pub-1")


class TestPasskeyRoutes:
    def _patch(self, monkeypatch, *, has_passkey: bool):
        user = _user_model(
            passkey_credential_id=CRED_B64 if has_passkey else None,
            passkey_public_key=PUB_B64 if has_passkey else None,
        )
        user_service = MagicMock()
        user_service.get_user_by_email = AsyncMock(return_value=user)
        user_service.update_user = AsyncMock()
        user_service.update_user_last_login = AsyncMock()
        monkeypatch.setattr(routes_passkey._ar, "UserService", lambda _db: user_service)

        monkeypatch.setattr(routes_passkey, "_new_challenge", lambda: b"challenge-bytes")
        monkeypatch.setattr(routes_passkey, "_store_challenge", AsyncMock())
        monkeypatch.setattr(
            routes_passkey, "_consume_challenge", AsyncMock(return_value=b"challenge-bytes")
        )
        monkeypatch.setattr(routes_passkey, "create_session_id", lambda _uid: "session-1")
        monkeypatch.setattr(routes_passkey, "_db_create_session", AsyncMock())
        return user, user_service

    @pytest.mark.asyncio
    async def test_challenge_returns_registration_options(self, monkeypatch):
        self._patch(monkeypatch, has_passkey=False)
        result = await routes_passkey.get_passkey_challenge(
            PasskeyChallengeRequest(email="user@example.com"),
            MagicMock(),
        )
        assert "publicKey" in result
        assert "challenge" in result["publicKey"]

    @pytest.mark.asyncio
    async def test_challenge_returns_authentication_options_when_registered(self, monkeypatch):
        self._patch(monkeypatch, has_passkey=True)
        result = await routes_passkey.get_passkey_challenge(
            PasskeyChallengeRequest(email="user@example.com"),
            MagicMock(),
        )
        assert "allowCredentials" in result["publicKey"]

    @pytest.mark.asyncio
    async def test_register_user_not_found(self, monkeypatch):
        _, user_service = self._patch(monkeypatch, has_passkey=False)
        user_service.get_user_by_email = AsyncMock(return_value=None)
        with pytest.raises(HTTPException, match="User not found"):
            await routes_passkey.register_passkey(
                PasskeyRegistrationRequest(email="user@example.com", credential={}),
                MagicMock(),
            )

    @pytest.mark.asyncio
    async def test_register_challenge_expired(self, monkeypatch):
        self._patch(monkeypatch, has_passkey=False)
        monkeypatch.setattr(routes_passkey, "_consume_challenge", AsyncMock(return_value=None))
        with pytest.raises(HTTPException, match="challenge expired"):
            await routes_passkey.register_passkey(
                PasskeyRegistrationRequest(email="user@example.com", credential={}),
                MagicMock(),
            )

    @pytest.mark.asyncio
    async def test_register_stores_credential(self, monkeypatch):
        user, user_service = self._patch(monkeypatch, has_passkey=False)
        verified = MagicMock(credential_id=b"cred-raw", credential_public_key=b"pub-raw")
        monkeypatch.setattr(routes_passkey, "verify_registration_response", lambda **_: verified)

        result = await routes_passkey.register_passkey(
            PasskeyRegistrationRequest(email="user@example.com", credential={}),
            MagicMock(),
        )

        assert result["message"] == "Passkey registered successfully"
        user_service.update_user.assert_awaited_once_with(
            user.id,
            passkey_credential_id=bytes_to_base64url(b"cred-raw"),
            passkey_public_key=bytes_to_base64url(b"pub-raw"),
        )

    @pytest.mark.asyncio
    async def test_auth_not_registered(self, monkeypatch):
        self._patch(monkeypatch, has_passkey=False)
        with pytest.raises(HTTPException, match="not registered"):
            await routes_passkey.authenticate_passkey(
                PasskeyAuthRequest(email="user@example.com", assertion={}),
                MagicMock(),
            )

    @pytest.mark.asyncio
    async def test_auth_verification_failure(self, monkeypatch):
        self._patch(monkeypatch, has_passkey=True)
        monkeypatch.setattr(
            routes_passkey,
            "verify_authentication_response",
            MagicMock(side_effect=Exception("bad signature")),
        )
        with pytest.raises(HTTPException, match="authentication failed"):
            await routes_passkey.authenticate_passkey(
                PasskeyAuthRequest(email="user@example.com", assertion={}),
                MagicMock(),
            )

    @pytest.mark.asyncio
    async def test_auth_success_mints_supabase_token_hash(self, monkeypatch):
        self._patch(monkeypatch, has_passkey=True)
        monkeypatch.setattr(
            routes_passkey, "verify_authentication_response", lambda **_: MagicMock()
        )
        supabase = MagicMock()
        supabase.generate_magic_link = AsyncMock(return_value="hashed-token")
        monkeypatch.setattr(routes_passkey, "SupabaseAuth", lambda: supabase)

        success = await routes_passkey.authenticate_passkey(
            PasskeyAuthRequest(email="user@example.com", assertion={}),
            MagicMock(),
        )

        assert success.data.token_hash == "hashed-token"
        routes_passkey._db_create_session.assert_awaited_once()
