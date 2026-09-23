"""Focused tests for shared outbound HTTP lifecycle, caching, and cleanup."""

from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest

from api.services import http_client


class _Response:
    def __init__(self, value: dict[str, object]):
        self._value = value
        self.text = "payload"

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self._value


class _RetryableResponse(_Response):
    def raise_for_status(self) -> None:
        raise httpx.HTTPStatusError(
            "temporary upstream failure",
            request=httpx.Request("GET", "https://example.test/search"),
            response=httpx.Response(503),
        )


@pytest.mark.asyncio
async def test_get_json_reuses_cached_result(monkeypatch):
    response = _Response({"ok": True})
    client = type("Client", (), {"get": AsyncMock(return_value=response)})()
    monkeypatch.setattr(http_client, "get_http_client", AsyncMock(return_value=client))
    http_client._cache.clear()

    first = await http_client.get_json("https://example.test/search", params={"q": "goblin"})
    second = await http_client.get_json("https://example.test/search", params={"q": "goblin"})

    assert first == second == {"ok": True}
    client.get.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_json_retries_transient_upstream_failure(monkeypatch):
    client = type("Client", (), {})()
    client.get = AsyncMock(
        side_effect=[_RetryableResponse({}), _Response({"ok": True})]
    )
    monkeypatch.setattr(http_client, "get_http_client", AsyncMock(return_value=client))
    http_client._cache.clear()

    result = await http_client.get_json("https://example.test/retry", ttl=0)

    assert result == {"ok": True}
    assert client.get.await_count == 2


@pytest.mark.asyncio
async def test_close_http_client_closes_client_and_clears_cache(monkeypatch):
    client = type("Client", (), {"is_closed": False, "aclose": AsyncMock()})()
    http_client._client = client
    http_client._cache["stale"] = (9999999999.0, {"value": 1})

    await http_client.close_http_client()

    client.aclose.assert_awaited_once()
    assert http_client._client is None
    assert http_client._cache == {}
