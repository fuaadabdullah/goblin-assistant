"""Tokens auth coverage tests."""

import sys
from types import SimpleNamespace

import jwt
import pytest

from api.auth.router import tokens as tokens_module


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
