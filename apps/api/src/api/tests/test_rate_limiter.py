"""Unit tests for api.middleware.rate_limiter's client-identification helpers.

_bucket_user_id() replaced a dead request.state.user_id check (never set by
anything, and unreachable before this middleware runs even if it were) with a
read of the bearer token's `sub` claim, used only to choose a rate-limit
bucket, not for authorization.

The subject is only honoured when the token's signature verifies against a
secret we hold locally. The bucket key selects which counter a request is
charged to, so accepting an unverified `sub` would let any caller forge a
token without a signing key and rotate the claim to mint unlimited empty
buckets — disabling rate limiting on every route this global middleware
guards. Anything not locally verifiable falls back to the IP bucket.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import jwt
import pytest

from api.middleware.rate_limiter import RateLimiter, _bucket_user_id

SIGNING_SECRET = "test-signing-secret-at-least-32-bytes-long"


@pytest.fixture(autouse=True)
def _signing_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    """Give the limiter a known local HMAC secret to verify against."""
    monkeypatch.setenv("JWT_SECRET_KEY", SIGNING_SECRET)
    monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)


def _request_with_headers(headers: dict[str, str], client_host: str = "203.0.113.5") -> MagicMock:
    request = MagicMock()
    request.headers = headers
    request.client = MagicMock(host=client_host)
    return request


def _bearer_token(payload: dict, secret: str = SIGNING_SECRET) -> str:
    return jwt.encode(payload, secret, algorithm="HS256")


class TestBucketUserId:
    def test_extracts_subject_from_verified_bearer_token(self):
        token = _bearer_token({"sub": "user-42"})
        request = _request_with_headers({"Authorization": f"Bearer {token}"})

        assert _bucket_user_id(request) == "user-42"

    def test_accepts_token_signed_with_the_supabase_secret(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SUPABASE_JWT_SECRET", "supabase-secret-at-least-32-bytes-long")
        token = _bearer_token(
            {"sub": "user-5", "aud": "authenticated"},
            secret="supabase-secret-at-least-32-bytes-long",
        )
        request = _request_with_headers({"Authorization": f"Bearer {token}"})

        # An `aud` claim must not be mistaken for a verification failure.
        assert _bucket_user_id(request) == "user-5"

    def test_returns_none_without_authorization_header(self):
        request = _request_with_headers({})
        assert _bucket_user_id(request) is None

    def test_returns_none_for_non_bearer_scheme(self):
        request = _request_with_headers({"Authorization": "Basic dXNlcjpwYXNz"})
        assert _bucket_user_id(request) is None

    def test_returns_none_for_empty_bearer_token(self):
        request = _request_with_headers({"Authorization": "Bearer "})
        assert _bucket_user_id(request) is None

    def test_returns_none_for_malformed_token(self):
        request = _request_with_headers({"Authorization": "Bearer not-a-real-jwt"})
        assert _bucket_user_id(request) is None

    def test_returns_none_when_token_has_no_subject_claim(self):
        token = _bearer_token({"role": "authenticated"})
        request = _request_with_headers({"Authorization": f"Bearer {token}"})
        assert _bucket_user_id(request) is None

    def test_rejects_token_signed_with_an_unknown_secret(self):
        # The bypass this guards against: a forged token needs no signing key,
        # so honouring its subject would hand the caller a private bucket.
        token = _bearer_token(
            {"sub": "attacker-chosen"}, secret="not-our-secret-at-least-32-bytes-long"
        )
        request = _request_with_headers({"Authorization": f"Bearer {token}"})

        assert _bucket_user_id(request) is None

    def test_rejects_unsigned_alg_none_token(self):
        token = jwt.encode({"sub": "attacker-chosen"}, key="", algorithm="none")
        request = _request_with_headers({"Authorization": f"Bearer {token}"})

        assert _bucket_user_id(request) is None

    def test_rejects_expired_token(self):
        token = _bearer_token({"sub": "user-7", "exp": 1})
        request = _request_with_headers({"Authorization": f"Bearer {token}"})

        assert _bucket_user_id(request) is None

    def test_returns_none_when_no_local_secret_is_configured(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        token = _bearer_token({"sub": "user-42"})
        request = _request_with_headers({"Authorization": f"Bearer {token}"})

        assert _bucket_user_id(request) is None


class TestGetClientIdentifier:
    def test_keys_by_user_when_verified_bearer_token_present(self):
        limiter = RateLimiter()
        token = _bearer_token({"sub": "user-99"})
        request = _request_with_headers({"Authorization": f"Bearer {token}"})

        assert limiter._get_client_identifier(request) == "user:user-99"

    def test_falls_back_to_ip_without_a_token(self):
        limiter = RateLimiter()
        request = _request_with_headers({}, client_host="198.51.100.7")

        assert limiter._get_client_identifier(request) == "ip:198.51.100.7"

    def test_forged_token_cannot_escape_the_ip_bucket(self):
        # Rotating a forged `sub` must not yield a fresh counter per request.
        limiter = RateLimiter()
        identifiers = set()
        for index in range(3):
            token = _bearer_token(
                {"sub": f"rotating-{index}"}, secret="not-our-secret-at-least-32-bytes-long"
            )
            request = _request_with_headers(
                {"Authorization": f"Bearer {token}"}, client_host="198.51.100.9"
            )
            identifiers.add(limiter._get_client_identifier(request))

        assert identifiers == {"ip:198.51.100.9"}
