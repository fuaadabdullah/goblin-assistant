from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock


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
