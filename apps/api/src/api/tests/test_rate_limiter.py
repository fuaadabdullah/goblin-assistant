"""Unit tests for api.middleware.rate_limiter's client-identification helpers.

_bucket_user_id() replaced a dead request.state.user_id check (never set by
anything, and unreachable before this middleware runs even if it were) with a
real one: an unverified read of the bearer token's `sub` claim, used only to
choose a rate-limit bucket, not for authorization.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import jwt

from api.middleware.rate_limiter import RateLimiter, _bucket_user_id


def _request_with_headers(headers: dict[str, str], client_host: str = "203.0.113.5") -> MagicMock:
    request = MagicMock()
    request.headers = headers
    request.client = MagicMock(host=client_host)
    return request


def _bearer_token(payload: dict) -> str:
    return jwt.encode(payload, "test-signing-secret-not-verified", algorithm="HS256")


class TestBucketUserId:
    def test_extracts_subject_from_unverified_bearer_token(self):
        token = _bearer_token({"sub": "user-42"})
        request = _request_with_headers({"Authorization": f"Bearer {token}"})

        assert _bucket_user_id(request) == "user-42"

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

    def test_does_not_verify_signature(self):
        # An expired/garbage-signed token still yields its subject: this
        # helper is for bucketing only, not an authorization decision.
        token = _bearer_token({"sub": "user-7", "exp": 1})
        request = _request_with_headers({"Authorization": f"Bearer {token}"})
        assert _bucket_user_id(request) == "user-7"


class TestGetClientIdentifier:
    def test_keys_by_user_when_bearer_token_present(self):
        limiter = RateLimiter()
        token = _bearer_token({"sub": "user-99"})
        request = _request_with_headers({"Authorization": f"Bearer {token}"})

        assert limiter._get_client_identifier(request) == "user:user-99"

    def test_falls_back_to_ip_without_a_token(self):
        limiter = RateLimiter()
        request = _request_with_headers({}, client_host="198.51.100.7")

        assert limiter._get_client_identifier(request) == "ip:198.51.100.7"
