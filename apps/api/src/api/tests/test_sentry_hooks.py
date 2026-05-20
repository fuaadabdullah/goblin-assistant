"""Tests for Sentry privacy hooks."""

from api.services.sentry_hooks import sentry_before_breadcrumb, sentry_before_send


def test_before_send_redacts_request_and_user_data():
    event = {
        "request": {
            "headers": {
                "Authorization": "Bearer secret-token",
                "Content-Type": "application/json",
            },
            "data": {"email": "user@example.com", "token": "topsecret"},
            "cookies": {"session": "abcd"},
        },
        "user": {
            "id": "user_123",
            "email": "user@example.com",
            "ip_address": "127.0.0.1",
            "username": "alice",
        },
        "extra": {"auth_token": "sk-12345678901234567890"},
    }

    sanitized = sentry_before_send(event, None)

    assert sanitized is not None
    assert sanitized["request"]["headers"]["Authorization"] == "[REDACTED]"
    assert sanitized["request"]["headers"]["Content-Type"] == "application/json"
    assert "REDACTED" in sanitized["request"]["data"]["email"]
    assert "REDACTED" in sanitized["request"]["data"]["token"]
    assert sanitized["request"]["cookies"] == "[REDACTED]"

    assert "email" not in sanitized["user"]
    assert "ip_address" not in sanitized["user"]
    assert "username" not in sanitized["user"]
    assert sanitized["user"]["id"] == "user_123"

    assert "REDACTED" in sanitized["extra"]["auth_token"]


def test_before_breadcrumb_redacts_sensitive_payloads():
    breadcrumb = {
        "category": "http",
        "message": "user email is person@example.com",
        "data": {"token": "my-secret-token", "status": 500},
    }

    sanitized = sentry_before_breadcrumb(breadcrumb, None)

    assert sanitized is not None
    assert "REDACTED" in sanitized["message"]
    assert "REDACTED" in sanitized["data"]["token"]
    assert sanitized["data"]["status"] == 500
