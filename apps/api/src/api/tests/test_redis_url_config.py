"""Contract tests for canonical Redis URL validation."""

from __future__ import annotations

import pytest

from api.config.redis_url import DEFAULT_REDIS_URL, resolve_redis_url


@pytest.mark.parametrize(
    "url",
    [
        "redis://localhost:6379/0",
        "rediss://user:secret@example.test:6379/0",
        "unix:///tmp/redis.sock",
    ],
)
def test_resolve_redis_url_accepts_supported_schemes(url: str) -> None:
    assert resolve_redis_url(url, component="test") == url


@pytest.mark.parametrize("url", [None, "", "  ", "https://example.test", "not-a-url"])
def test_resolve_redis_url_falls_back_for_missing_or_unsupported_urls(url: str | None) -> None:
    assert resolve_redis_url(url, component="test") == DEFAULT_REDIS_URL


def test_resolve_redis_url_does_not_log_credentials(monkeypatch) -> None:
    events: list[tuple[str, dict[str, str]]] = []

    class CapturingLogger:
        def warning(self, event: str, **fields: str) -> None:
            events.append((event, fields))

    def _get_logger() -> CapturingLogger:
        return CapturingLogger()

    monkeypatch.setattr("api.config.redis_url.structlog.get_logger", _get_logger)
    secret_url = "https://admin:do-not-log@example.test/redis"

    assert resolve_redis_url(secret_url, component="test") == DEFAULT_REDIS_URL
    assert events == [
        (
            "redis_url_invalid",
            {
                "component": "test",
                "configured_scheme": "https",
                "fallback_scheme": "redis",
            },
        )
    ]
    assert "do-not-log" not in repr(events)
