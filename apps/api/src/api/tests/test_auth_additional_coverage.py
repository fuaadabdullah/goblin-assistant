from __future__ import annotations

import json
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException, Response
from jwt import decode

from api.auth import oauth as oauth_module
from api.auth.oauth import GoogleOAuth
from api.auth.passkeys import WebAuthnPasskey
from api.auth.router import dependencies as deps
from api.auth.router import routes_csrf, routes_email, routes_google, routes_passkey
from api.auth.router import tokens as tokens_module
from api.auth.router.schemas import (
    GoogleAuthCallback,
    GoogleAuthRequest,
    PasskeyAuthRequest,
    PasskeyRegistrationRequest,
    RefreshTokenRequest,
    TokenValidationRequest,
    User,
)
from api.auth.router.tokens import (
    SECRET_KEY,
    create_refresh_token,
)
from api.auth.router.tokens import (
    create_access_token as create_real_access_token,
)
from api.auth.router.tokens import (
    verify_token as verify_auth_token,
)


def _auth_request(state: SimpleNamespace | None = None, cookies: dict | None = None):
    return SimpleNamespace(
        state=state or SimpleNamespace(),
        cookies=cookies or {},
    )


class _FakeExecuteResult:
    def __init__(self, *, first=None, scalar=None):
        self._first = first
        self._scalar = scalar

    def first(self):
        return self._first

    def scalar_one_or_none(self):
        return self._scalar


class _FakeDb:
    def __init__(self, results):
        self._results = list(results)
        self.execute = AsyncMock(side_effect=self._execute)

    async def _execute(self, *_args, **_kwargs):
        return self._results.pop(0)


def _user_model(**overrides):
    data = {
        "id": "user-1",
        "email": "user@example.com",
        "name": "Test User",
        "google_id": None,
        "passkey_credential_id": None,
        "passkey_public_key": None,
        "hashed_password": "hashed",
        "is_active": True,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _async_client_factory(*responses_or_exceptions):
    shared_items = list(responses_or_exceptions)

    class _Client:
        def __init__(self):
            self._items = shared_items

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *args, **kwargs):
            _ = args, kwargs
            item = self._items.pop(0)
            if isinstance(item, Exception):
                raise item
            return item

        async def get(self, *args, **kwargs):
            _ = args, kwargs
            item = self._items.pop(0)
            if isinstance(item, Exception):
                raise item
            return item

    return _Client


class TestGoogleOAuthHelpers:
    def test_get_authorization_url_uses_given_state(self, monkeypatch):
        monkeypatch.setattr(oauth_module, "GOOGLE_CLIENT_ID", "client-id")
        monkeypatch.setattr(oauth_module, "GOOGLE_REDIRECT_URI", "https://app/callback")

        url = GoogleOAuth.get_authorization_url(state="fixed-state")

        assert "client_id=client-id" in url
        assert "redirect_uri=https%3A%2F%2Fapp%2Fcallback" in url
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


class TestPasskeyHelpers:
    def test_base64url_round_trip(self):
        raw = b"goblin-passkey"
        encoded = WebAuthnPasskey.encode_base64url(raw)

        assert WebAuthnPasskey.decode_base64url(encoded) == raw

    def test_parse_authenticator_data_variants(self):
        with pytest.raises(ValueError, match="too short"):
            WebAuthnPasskey.parse_authenticator_data(b"short")

        rp_id_hash = b"\x01" * 32
        flags = b"\x05"
        sign_count = (7).to_bytes(4, byteorder="big")
        aaguid = b"\x02" * 16
        credential_id = b"cred-123"
        cred_len = len(credential_id).to_bytes(2, byteorder="big")
        public_key = b"\x04" + b"\x03" * 64
        payload = rp_id_hash + flags + sign_count + aaguid + cred_len + credential_id + public_key

        parsed = WebAuthnPasskey.parse_authenticator_data(payload)

        assert parsed["flags"] == 5
        assert parsed["sign_count"] == 7
        assert parsed["attested_credential_data"]["aaguid"] == aaguid.hex()
        assert parsed["attested_credential_data"]["credential_id"] == credential_id

    def test_parse_authenticator_data_without_attested_data(self):
        payload = b"\x01" * 32 + b"\x05" + (7).to_bytes(4, byteorder="big")

        parsed = WebAuthnPasskey.parse_authenticator_data(payload)

        assert parsed["attested_credential_data"] is None

    def test_parse_cose_public_key_success(self):
        private_key = ec.generate_private_key(ec.SECP256R1())
        public_numbers = private_key.public_key().public_numbers()
        cose_key = (
            b"\x04" + public_numbers.x.to_bytes(32, "big") + public_numbers.y.to_bytes(32, "big")
        )

        parsed = WebAuthnPasskey.parse_cose_public_key(cose_key)

        assert parsed.public_numbers().x == public_numbers.x
        assert parsed.public_numbers().y == public_numbers.y

    def test_parse_cose_public_key_invalid(self):
        with pytest.raises(ValueError, match="Unsupported"):
            WebAuthnPasskey.parse_cose_public_key(b"invalid")

    def test_verify_signature_true_and_false(self):
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import ec

        private_key = ec.generate_private_key(ec.SECP256R1())
        public_key = private_key.public_key()
        authenticator_data = b"auth-data"
        client_data_json = b'{"type":"webauthn.get"}'
        signed_data = authenticator_data + __import__("hashlib").sha256(client_data_json).digest()
        signature = private_key.sign(signed_data, ec.ECDSA(hashes.SHA256()))

        assert (
            WebAuthnPasskey.verify_signature(
                public_key, signature, authenticator_data, client_data_json
            )
            is True
        )
        assert (
            WebAuthnPasskey.verify_signature(
                public_key, b"bad-signature", authenticator_data, client_data_json
            )
            is False
        )

    def test_verify_signature_generic_exception(self):
        class _BrokenPublicKey:
            def verify(self, *_args, **_kwargs):
                raise RuntimeError("boom")

        assert (
            WebAuthnPasskey.verify_signature(
                _BrokenPublicKey(),
                b"sig",
                b"auth",
                b'{"type":"webauthn.get"}',
            )
            is False
        )

    @pytest.mark.asyncio
    async def test_verify_passkey_authentication_paths(self, monkeypatch):
        challenge = "challenge-123"
        origin = "https://goblin.example"
        client_data = {
            "challenge": WebAuthnPasskey.encode_base64url(challenge.encode()),
            "origin": origin,
            "type": "webauthn.get",
        }
        client_data_json = json.dumps(client_data).encode()
        encoded_client_data = WebAuthnPasskey.encode_base64url(client_data_json)
        encoded_auth_data = WebAuthnPasskey.encode_base64url(b"a" * 37)
        encoded_signature = WebAuthnPasskey.encode_base64url(b"signature")
        encoded_public_key = WebAuthnPasskey.encode_base64url(b"\x04" + b"\x01" * 64)

        monkeypatch.setattr(
            WebAuthnPasskey,
            "parse_authenticator_data",
            staticmethod(lambda _data: {"flags": 1}),
        )
        monkeypatch.setattr(
            WebAuthnPasskey,
            "parse_cose_public_key",
            staticmethod(lambda _data: object()),
        )
        monkeypatch.setattr(
            WebAuthnPasskey,
            "verify_signature",
            staticmethod(lambda *_args: True),
        )

        assert (
            await WebAuthnPasskey.verify_passkey_authentication(
                _credential_id="cred",
                stored_public_key=encoded_public_key,
                authenticator_data_b64=encoded_auth_data,
                client_data_json_b64=encoded_client_data,
                signature_b64=encoded_signature,
                challenge=challenge,
                origin=origin,
            )
            is True
        )

        bad_origin = dict(client_data, origin="https://other.example")
        bad_origin_b64 = WebAuthnPasskey.encode_base64url(json.dumps(bad_origin).encode())
        assert (
            await WebAuthnPasskey.verify_passkey_authentication(
                _credential_id="cred",
                stored_public_key=encoded_public_key,
                authenticator_data_b64=encoded_auth_data,
                client_data_json_b64=bad_origin_b64,
                signature_b64=encoded_signature,
                challenge=challenge,
                origin=origin,
            )
            is False
        )

        assert WebAuthnPasskey.generate_challenge()

    @pytest.mark.asyncio
    async def test_verify_passkey_authentication_rejects_challenge_type_and_errors(
        self, monkeypatch
    ):
        challenge = "challenge-123"
        origin = "https://goblin.example"
        client_data = {
            "challenge": WebAuthnPasskey.encode_base64url(challenge.encode()),
            "origin": origin,
            "type": "webauthn.get",
        }

        monkeypatch.setattr(
            WebAuthnPasskey,
            "parse_authenticator_data",
            staticmethod(lambda _data: {"flags": 1}),
        )
        monkeypatch.setattr(
            WebAuthnPasskey,
            "parse_cose_public_key",
            staticmethod(lambda _data: object()),
        )
        monkeypatch.setattr(
            WebAuthnPasskey,
            "verify_signature",
            staticmethod(lambda *_args: True),
        )

        wrong_challenge = dict(client_data, challenge=WebAuthnPasskey.encode_base64url(b"other"))
        wrong_type = dict(client_data, type="webauthn.create")

        assert (
            await WebAuthnPasskey.verify_passkey_authentication(
                _credential_id="cred",
                stored_public_key=WebAuthnPasskey.encode_base64url(b"\x04" + b"\x01" * 64),
                authenticator_data_b64=WebAuthnPasskey.encode_base64url(b"a" * 37),
                client_data_json_b64=WebAuthnPasskey.encode_base64url(
                    json.dumps(wrong_challenge).encode()
                ),
                signature_b64=WebAuthnPasskey.encode_base64url(b"signature"),
                challenge=challenge,
                origin=origin,
            )
            is False
        )
        assert (
            await WebAuthnPasskey.verify_passkey_authentication(
                _credential_id="cred",
                stored_public_key=WebAuthnPasskey.encode_base64url(b"\x04" + b"\x01" * 64),
                authenticator_data_b64=WebAuthnPasskey.encode_base64url(b"a" * 37),
                client_data_json_b64=WebAuthnPasskey.encode_base64url(
                    json.dumps(wrong_type).encode()
                ),
                signature_b64=WebAuthnPasskey.encode_base64url(b"signature"),
                challenge=challenge,
                origin=origin,
            )
            is False
        )

        monkeypatch.setattr(
            WebAuthnPasskey,
            "parse_authenticator_data",
            staticmethod(lambda _data: (_ for _ in ()).throw(RuntimeError("bad auth data"))),
        )
        assert (
            await WebAuthnPasskey.verify_passkey_authentication(
                _credential_id="cred",
                stored_public_key=WebAuthnPasskey.encode_base64url(b"\x04" + b"\x01" * 64),
                authenticator_data_b64=WebAuthnPasskey.encode_base64url(b"a" * 37),
                client_data_json_b64=WebAuthnPasskey.encode_base64url(
                    json.dumps(client_data).encode()
                ),
                signature_b64=WebAuthnPasskey.encode_base64url(b"signature"),
                challenge=challenge,
                origin=origin,
            )
            is False
        )


class TestAuthDependencies:
    def test_is_user_active_variants(self):
        assert deps._is_user_active(True) is True
        assert deps._is_user_active("YES") is True
        assert deps._is_user_active(1) is True
        assert deps._is_user_active("off") is False
        assert deps._is_user_active(None) is False

    @pytest.mark.asyncio
    async def test_get_authenticated_user_model_paths(self):
        active_user = _user_model()
        active_session = SimpleNamespace(is_revoked=False)
        revoked_session = SimpleNamespace(is_revoked=True)

        db = _FakeDb(
            [
                _FakeExecuteResult(first=(active_user, active_session)),
                _FakeExecuteResult(first=(active_user, revoked_session)),
                _FakeExecuteResult(first=None),
                _FakeExecuteResult(scalar=active_user),
            ]
        )

        assert (
            await deps._get_authenticated_user_model(
                db, user_id=active_user.id, session_id="session-1"
            )
            is active_user
        )
        assert (
            await deps._get_authenticated_user_model(
                db, user_id=active_user.id, session_id="session-2"
            )
            is None
        )
        assert (
            await deps._get_authenticated_user_model(
                db, user_id=active_user.id, session_id="session-3"
            )
            is None
        )
        assert (
            await deps._get_authenticated_user_model(db, user_id=active_user.id, session_id=None)
            is active_user
        )

    @pytest.mark.asyncio
    async def test_get_current_user_error_and_cache_paths(self, monkeypatch):
        request = _auth_request()
        db = MagicMock()

        with pytest.raises(HTTPException, match="Not authenticated"):
            await deps.get_current_user(request, db, credentials=None)

        monkeypatch.setattr(deps, "verify_token", lambda _token: None)
        with pytest.raises(HTTPException, match="Invalid authentication credentials"):
            await deps.get_current_user(request, db, credentials=SimpleNamespace(credentials="bad"))

        monkeypatch.setattr(deps, "verify_token", lambda _token: {"type": "refresh"})
        with pytest.raises(HTTPException, match="Invalid token type"):
            await deps.get_current_user(
                request, db, credentials=SimpleNamespace(credentials="refresh")
            )

        monkeypatch.setattr(deps, "verify_token", lambda _token: {"type": "access"})
        with pytest.raises(HTTPException, match="Invalid token payload"):
            await deps.get_current_user(
                request, db, credentials=SimpleNamespace(credentials="missing-sub")
            )

        inactive_request = _auth_request()
        inactive_user = _user_model(is_active=False)
        monkeypatch.setattr(
            deps,
            "verify_token",
            lambda _token: {"type": "access", "sub": inactive_user.id, "session_id": "sid"},
        )
        monkeypatch.setattr(
            deps,
            "_get_authenticated_user_model",
            AsyncMock(return_value=inactive_user),
        )
        with pytest.raises(HTTPException, match="inactive"):
            await deps.get_current_user(
                inactive_request,
                db,
                credentials=SimpleNamespace(credentials="access"),
            )

        cached_model = _user_model(passkey_public_key="pk")
        cached_request = _auth_request(
            state=SimpleNamespace(
                auth_user=cached_model,
                auth_user_id=cached_model.id,
                auth_session_id="sid",
            )
        )
        fetcher = AsyncMock()
        monkeypatch.setattr(
            deps,
            "verify_token",
            lambda _token: {"type": "access", "sub": cached_model.id, "session_id": "sid"},
        )
        monkeypatch.setattr(deps, "_get_authenticated_user_model", fetcher)

        user = await deps.get_current_user(
            cached_request,
            db,
            credentials=SimpleNamespace(credentials="access"),
        )

        assert isinstance(user, User)
        assert user.id == cached_model.id
        fetcher.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_supabase_provision_and_get_current_user_paths(self, monkeypatch):
        db = SimpleNamespace(
            execute=AsyncMock(
                side_effect=[
                    _FakeExecuteResult(scalar=None),
                    _FakeExecuteResult(scalar=None),
                    _FakeExecuteResult(scalar=None),
                ]
            ),
            add=MagicMock(),
            commit=AsyncMock(),
            refresh=AsyncMock(),
        )

        provisioned_user = _user_model(id="supabase-user", email="supabase@example.com")
        db.execute = AsyncMock(
            side_effect=[
                _FakeExecuteResult(scalar=None),
                _FakeExecuteResult(scalar=None),
                _FakeExecuteResult(scalar=None),
            ]
        )

        async def fake_provision(_db, _payload):
            return provisioned_user

        monkeypatch.setattr(deps, "_provision_supabase_user", fake_provision)
        monkeypatch.setattr(deps, "verify_token", lambda _token: None)
        monkeypatch.setattr(
            deps,
            "verify_supabase_token",
            lambda _token: {"sub": "supabase-user", "email": "supabase@example.com"},
        )

        class _Ctx:
            async def __aenter__(self):
                return db

            async def __aexit__(self, exc_type, exc, tb):
                return False

        monkeypatch.setattr(deps, "get_db_context", _Ctx)

        request = _auth_request()
        user = await deps.get_current_user(
            request,
            db,
            credentials=SimpleNamespace(credentials="supabase-token"),
        )

        assert user.id == "supabase-user"
        assert request.state.auth_user_id == "supabase-user"

    @pytest.mark.asyncio
    async def test_get_authenticated_user_model_provision_and_revoke_paths(self, monkeypatch):
        write_db = SimpleNamespace(
            execute=AsyncMock(return_value=_FakeExecuteResult(scalar=None)),
            add=MagicMock(),
            commit=AsyncMock(),
            refresh=AsyncMock(),
        )

        monkeypatch.setattr(deps.uuid, "uuid4", lambda: "generated-user")

        result = await deps._provision_supabase_user(
            write_db,
            {"sub": "", "email": "new@example.com", "user_metadata": {"name": "New User"}},
        )

        assert result is not None
        assert result.email == "new@example.com"
        assert write_db.add.called
        write_db.commit.assert_awaited_once()
        write_db.refresh.assert_awaited_once()


class TestTokenHelpers:
    def test_get_jwks_client_is_created_and_cached(self, monkeypatch):
        created = {}

        class FakeJwksClient:
            def __init__(self, url, cache_keys, lifespan, timeout):
                created["url"] = url
                created["cache_keys"] = cache_keys
                created["lifespan"] = lifespan
                created["timeout"] = timeout

        monkeypatch.setattr(tokens_module, "SUPABASE_URL", "https://supabase.example")
        monkeypatch.setattr(tokens_module, "_jwks_client", None)
        monkeypatch.setattr(tokens_module, "PyJWKClient", FakeJwksClient)

        first = tokens_module._get_jwks_client()
        second = tokens_module._get_jwks_client()

        assert first is second
        assert created["url"].endswith("/auth/v1/.well-known/jwks.json")
        assert created["cache_keys"] is True

    @pytest.mark.asyncio
    async def test_verify_via_auth_api_caches_success(self, monkeypatch):
        tokens_module._auth_api_cache.clear()
        monkeypatch.setattr(tokens_module, "SUPABASE_URL", "https://supabase.example")
        monkeypatch.setattr(tokens_module, "SUPABASE_ANON_KEY", "anon-key")

        token = jwt.encode(
            {"sub": "supabase-user", "email": "supabase@example.com", "exp": 2000000000},
            "secret",
            algorithm="HS256",
        )
        calls = {"count": 0}

        class FakeResponse:
            status_code = 200

            def json(self):
                return {
                    "id": "supabase-user",
                    "email": "supabase@example.com",
                    "user_metadata": {"name": "Supabase User"},
                }

        def fake_get(*args, **kwargs):
            calls["count"] += 1
            return FakeResponse()

        monkeypatch.setitem(sys.modules, "httpx", SimpleNamespace(get=fake_get))

        first = tokens_module._verify_via_auth_api(token)
        second = tokens_module._verify_via_auth_api(token)

        assert first == second
        assert first["sub"] == "supabase-user"
        assert calls["count"] == 1

    def test_verify_supabase_token_hs256_es256_and_invalid_paths(self, monkeypatch):
        monkeypatch.setattr(tokens_module, "SUPABASE_JWT_SECRET", "supabase-secret")
        hs_token = jwt.encode(
            {"sub": "user-1", "aud": "authenticated"},
            "supabase-secret",
            algorithm="HS256",
        )
        assert tokens_module.verify_supabase_token(hs_token)["sub"] == "user-1"

        monkeypatch.setattr(tokens_module, "SUPABASE_JWT_SECRET", None)
        monkeypatch.setattr(
            tokens_module, "_verify_via_auth_api", lambda _token: {"sub": "api-user"}
        )
        monkeypatch.setattr(
            tokens_module.jwt, "get_unverified_header", lambda _token: {"alg": "HS256"}
        )
        assert tokens_module.verify_supabase_token("hs-token") == {"sub": "api-user"}

        fake_jwks = SimpleNamespace(
            get_signing_key_from_jwt=lambda _token: SimpleNamespace(key="public-key")
        )
        seen = {}

        def fake_decode(token, key, algorithms, audience):
            seen["args"] = (token, key, algorithms, audience)
            return {"sub": "es-user"}

        monkeypatch.setattr(tokens_module, "_get_jwks_client", lambda: fake_jwks)
        monkeypatch.setattr(
            tokens_module.jwt, "get_unverified_header", lambda _token: {"alg": "ES256"}
        )
        monkeypatch.setattr(tokens_module.jwt, "decode", fake_decode)
        assert tokens_module.verify_supabase_token("es-token") == {"sub": "es-user"}
        assert seen["args"][1] == "public-key"

        monkeypatch.setattr(
            tokens_module.jwt, "get_unverified_header", lambda _token: {"alg": "none"}
        )
        assert tokens_module.verify_supabase_token("bad-token") is None


class TestCsrfRoute:
    @pytest.mark.asyncio
    async def test_get_csrf_token_wraps_generated_value(self, monkeypatch):
        monkeypatch.setattr(routes_csrf, "generate_csrf_token", AsyncMock(return_value="csrf-123"))

        response = await routes_csrf.get_csrf_token()

        assert response.csrf_token == "csrf-123"


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


class TestGoogleRoutes:
    @pytest.mark.asyncio
    async def test_issue_google_session_tokens_existing_and_linked_user(self, monkeypatch):
        committed = {"count": 0}

        async def commit():
            committed["count"] += 1

        db = SimpleNamespace(commit=AsyncMock(side_effect=commit))
        response = Response()

        linked_user = _user_model(email="user@example.com", google_id=None)
        existing_google_user = _user_model(email="google@example.com", google_id="gid")

        user_service = MagicMock()
        user_service.get_user_by_google_id = AsyncMock(side_effect=[existing_google_user, None])
        user_service.get_user_by_email = AsyncMock(return_value=linked_user)
        user_service.update_user = AsyncMock()
        user_service.create_user = AsyncMock()
        user_service.update_user_last_login = AsyncMock()

        monkeypatch.setattr(routes_google._ar, "UserService", lambda _db: user_service)
        monkeypatch.setattr(routes_google, "create_session_id", lambda _uid: "session-1")
        monkeypatch.setattr(routes_google, "_db_create_session", AsyncMock())
        monkeypatch.setattr(routes_google, "create_access_token", lambda **_kwargs: "access-token")
        monkeypatch.setattr(routes_google, "create_refresh_token", lambda *_args: "refresh-token")
        set_cookies = MagicMock()
        monkeypatch.setattr(routes_google, "_set_auth_cookies", set_cookies)

        direct = await routes_google._issue_google_session_tokens(
            {"email": "google@example.com", "sub": "gid", "name": "Google User"},
            db,
            response,
        )
        linked = await routes_google._issue_google_session_tokens(
            {"email": "user@example.com", "sub": "new-google-id", "name": "Linked User"},
            db,
            response,
        )

        assert direct.data.user.email == "google@example.com"
        assert linked.data.user.email == "user@example.com"
        assert committed["count"] == 2
        assert user_service.update_user.await_count == 1
        assert set_cookies.call_count == 2

    @pytest.mark.asyncio
    async def test_issue_google_session_tokens_error_paths(self, monkeypatch):
        db = SimpleNamespace(commit=AsyncMock())
        response = Response()

        with pytest.raises(HTTPException, match="Invalid Google user data"):
            await routes_google._issue_google_session_tokens({"email": "missing-sub"}, db, response)

        inactive_user = _user_model(google_id="gid", is_active=False)
        failing_service = MagicMock()
        failing_service.get_user_by_google_id = AsyncMock(return_value=inactive_user)
        failing_service.get_user_by_email = AsyncMock(return_value=None)
        failing_service.create_user = AsyncMock(return_value=None)
        failing_service.update_user_last_login = AsyncMock()
        monkeypatch.setattr(routes_google._ar, "UserService", lambda _db: failing_service)

        with pytest.raises(HTTPException, match="inactive"):
            await routes_google._issue_google_session_tokens(
                {"email": "inactive@example.com", "sub": "gid", "name": "Inactive"},
                db,
                response,
            )

    @pytest.mark.asyncio
    async def test_google_route_wrappers(self, monkeypatch):
        db = MagicMock()
        response = Response()

        monkeypatch.setattr(
            routes_google.GoogleOAuth,
            "verify_token",
            AsyncMock(return_value={"email": "user@example.com", "sub": "gid", "name": "User"}),
        )
        monkeypatch.setattr(
            routes_google,
            "_issue_google_session_tokens",
            AsyncMock(return_value=SimpleNamespace(ok=True)),
        )
        result = await routes_google.google_auth(GoogleAuthRequest(token="token"), response, db)
        assert result.ok is True

        monkeypatch.setattr(
            routes_google.GoogleOAuth, "get_authorization_url", lambda: "https://google"
        )
        assert (await routes_google.get_google_auth_url())["authorization_url"] == "https://google"

        monkeypatch.setattr(
            routes_google.GoogleOAuth,
            "get_authorization_url",
            lambda: (_ for _ in ()).throw(ValueError("missing config")),
        )
        with pytest.raises(HTTPException, match="missing config"):
            await routes_google.get_google_auth_url()

        monkeypatch.setattr(
            routes_google.GoogleOAuth,
            "exchange_code_for_token",
            AsyncMock(return_value={"access_token": "token"}),
        )
        monkeypatch.setattr(
            routes_google.GoogleOAuth,
            "get_user_info",
            AsyncMock(return_value={"email": "user@example.com", "sub": "gid", "name": "User"}),
        )
        monkeypatch.setattr(
            routes_google,
            "_issue_google_session_tokens",
            AsyncMock(return_value=SimpleNamespace(done=True)),
        )
        callback_result = await routes_google.google_auth_callback(
            GoogleAuthCallback(code="code"),
            response,
            db,
        )
        assert callback_result.done is True

        monkeypatch.setattr(
            routes_google.GoogleOAuth,
            "exchange_code_for_token",
            AsyncMock(return_value=None),
        )
        with pytest.raises(HTTPException, match="Failed to exchange code"):
            await routes_google.google_auth_callback(GoogleAuthCallback(code="bad"), response, db)


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


class TestEmailRoutes:
    @pytest.mark.asyncio
    async def test_refresh_logout_and_validate_paths(self, monkeypatch):
        active_user = _user_model(passkey_public_key="pk")
        db = MagicMock()
        response = Response()

        with pytest.raises(HTTPException, match="No refresh token provided"):
            await routes_email.refresh_token_endpoint(
                RefreshTokenRequest(refresh_token=None),
                SimpleNamespace(cookies={}),
                response,
                db,
            )

        monkeypatch.setattr(routes_email, "verify_token", lambda _token: {"type": "access"})
        with pytest.raises(HTTPException, match="Invalid refresh token"):
            await routes_email.refresh_token_endpoint(
                RefreshTokenRequest(refresh_token="wrong-type"),
                SimpleNamespace(cookies={}),
                response,
                db,
            )

        valid_refresh = create_refresh_token(active_user.id, "session-1")
        monkeypatch.setattr(routes_email, "verify_token", verify_auth_token)
        monkeypatch.setattr(
            routes_email, "_get_authenticated_user_model", AsyncMock(return_value=active_user)
        )
        monkeypatch.setattr(routes_email, "create_access_token", lambda **_kwargs: "new-access")
        monkeypatch.setattr(routes_email, "create_refresh_token", lambda *_args: "new-refresh")
        set_cookies = MagicMock()
        monkeypatch.setattr(routes_email, "_set_auth_cookies", set_cookies)

        refreshed = await routes_email.refresh_token_endpoint(
            RefreshTokenRequest(refresh_token=valid_refresh),
            SimpleNamespace(cookies={}),
            response,
            db,
        )
        assert refreshed.data.access_token == "new-access"
        assert set_cookies.called

        revoke = AsyncMock()
        clear_cookies = MagicMock()
        monkeypatch.setattr(routes_email, "_db_revoke_session", revoke)
        monkeypatch.setattr(routes_email, "_clear_auth_cookies", clear_cookies)
        access_token = create_real_access_token(
            data={"sub": active_user.id}, session_id="session-1"
        )

        logged_out = await routes_email.logout(
            SimpleNamespace(cookies={"session_token": access_token}),
            response,
            User(id=active_user.id, email=active_user.email),
            None,
            db,
        )
        assert logged_out.data.message == "Logged out successfully"
        revoke.assert_awaited_once()
        assert clear_cookies.called

        monkeypatch.setattr(routes_email, "verify_token", lambda _token: None)
        invalid = await routes_email.validate_token(TokenValidationRequest(token="bad"), db)
        assert invalid.data.valid is False

        payload = decode(valid_refresh, SECRET_KEY, algorithms=["HS256"])
        access_like = create_real_access_token(data={"sub": payload["sub"]}, session_id="session-1")
        monkeypatch.setattr(
            routes_email,
            "verify_token",
            lambda _token: decode(access_like, SECRET_KEY, algorithms=["HS256"]),
        )
        user_service = MagicMock()
        user_service.get_user_by_id = AsyncMock(return_value=active_user)
        monkeypatch.setattr(routes_email._ar, "UserService", lambda _db: user_service)

        valid = await routes_email.validate_token(TokenValidationRequest(token=access_like), db)
        assert valid.data.valid is True
        assert valid.data.user.email == active_user.email
