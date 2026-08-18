"""Shared fixtures for sandbox API runtime tests."""

from __future__ import annotations

import importlib
import sys

sys.modules.pop("api.sandbox_api", None)
sandbox_api = importlib.import_module("api.sandbox_api")


class _FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, dict[str, str]] = {}
        self._scalars: dict[str, int] = {}
        self.deleted: list[str] = []
        self.should_fail_ping = False

    def hset(self, key: str, *args, mapping=None):
        if mapping is not None:
            self.store.setdefault(key, {})
            for k, v in mapping.items():
                self.store[key][str(k)] = str(v)
            return
        field, value = args
        self.store.setdefault(key, {})
        self.store[key][str(field)] = str(value)

    def hgetall(self, key: str):
        payload = self.store.get(key, {})
        return {k.encode("utf-8"): v.encode("utf-8") for k, v in payload.items()}

    def get(self, key: str):
        val = self._scalars.get(key)
        return str(val).encode("utf-8") if val is not None else None

    def incr(self, key: str) -> int:
        self._scalars[key] = self._scalars.get(key, 0) + 1
        return self._scalars[key]

    def decr(self, key: str) -> int:
        self._scalars[key] = self._scalars.get(key, 0) - 1
        return self._scalars[key]

    def expire(self, key: str, seconds: int) -> bool:
        return True

    def delete(self, key: str):
        self.deleted.append(key)
        self.store.pop(key, None)
        self._scalars.pop(key, None)

    def scan_iter(self, _pattern: str):
        for key in self.store:
            if key.startswith("sandbox:job:"):
                yield key.encode("utf-8")

    def ping(self):
        if self.should_fail_ping:
            raise ConnectionError("redis down")
        return True


class _FakeQueue:
    def __init__(self) -> None:
        self.enqueued: list[dict] = []
        self.depth = 0

    def enqueue(self, *args, **kwargs):
        self.enqueued.append({"args": args, "kwargs": kwargs})

    def __len__(self) -> int:
        return self.depth
