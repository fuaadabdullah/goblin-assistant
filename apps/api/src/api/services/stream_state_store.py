from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, Optional, Protocol

import structlog

from ..core.redis_client import get_redis_client

logger = structlog.get_logger()


class StreamStateStore(Protocol):
    async def create_stream(self, stream_id: str, metadata: Dict[str, Any]) -> None: ...

    async def append_chunk(self, stream_id: str, chunk: Dict[str, Any]) -> None: ...

    async def mark_status(
        self,
        stream_id: str,
        *,
        status: str,
        done: bool,
        updates: Optional[Dict[str, Any]] = None,
    ) -> None: ...

    async def poll_stream(self, stream_id: str) -> Optional[Dict[str, Any]]: ...

    async def cancel_stream(self, stream_id: str) -> bool: ...


@dataclass(frozen=True)
class StreamKeySet:
    meta: str
    chunks: str


def _keys(stream_id: str) -> StreamKeySet:
    base = f"stream:task:{stream_id}"
    return StreamKeySet(meta=f"{base}:meta", chunks=f"{base}:chunks")


def _terminal(status: str) -> bool:
    return status in {"completed", "failed", "cancelled"}


class InMemoryStreamStateStore:
    def __init__(self) -> None:
        self._streams: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    async def create_stream(self, stream_id: str, metadata: Dict[str, Any]) -> None:
        with self._lock:
            now = time.time()
            self._streams[stream_id] = {
                "stream_id": stream_id,
                "status": "running",
                "done": False,
                "created_at": now,
                "updated_at": now,
                "metadata": dict(metadata),
                "chunks": [],
            }

    async def append_chunk(self, stream_id: str, chunk: Dict[str, Any]) -> None:
        with self._lock:
            stream = self._streams.get(stream_id)
            if stream is None:
                return
            stream["chunks"].append(dict(chunk))
            stream["updated_at"] = time.time()

    async def mark_status(
        self,
        stream_id: str,
        *,
        status: str,
        done: bool,
        updates: Optional[Dict[str, Any]] = None,
    ) -> None:
        with self._lock:
            stream = self._streams.get(stream_id)
            if stream is None:
                return
            stream["status"] = status
            stream["done"] = done
            stream["updated_at"] = time.time()
            if updates:
                stream["metadata"].update(dict(updates))

    async def poll_stream(self, stream_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            stream = self._streams.get(stream_id)
            if stream is None:
                return None
            chunks = list(stream.get("chunks", []))
            stream["chunks"] = []
            return {
                "stream_id": stream_id,
                "status": stream["status"],
                "chunks": chunks,
                "done": bool(stream["done"] or _terminal(stream["status"])),
            }

    async def cancel_stream(self, stream_id: str) -> bool:
        with self._lock:
            stream = self._streams.get(stream_id)
            if stream is None:
                return False
            stream["status"] = "cancelled"
            stream["done"] = True
            stream["updated_at"] = time.time()
            return True


class RedisStreamStateStore:
    def __init__(self, *, ttl_seconds: int) -> None:
        self._ttl_seconds = max(60, int(ttl_seconds))

    async def _redis(self):
        return await get_redis_client()

    async def _set_expiry(self, stream_id: str) -> None:
        redis = await self._redis()
        key_set = _keys(stream_id)
        await redis.expire(key_set.meta, self._ttl_seconds)
        await redis.expire(key_set.chunks, self._ttl_seconds)

    async def create_stream(self, stream_id: str, metadata: Dict[str, Any]) -> None:
        redis = await self._redis()
        key_set = _keys(stream_id)
        now = str(time.time())
        payload = {
            "stream_id": stream_id,
            "status": "running",
            "done": "0",
            "created_at": now,
            "updated_at": now,
            "metadata": json.dumps(metadata),
        }
        await redis.hset(key_set.meta, mapping=payload)
        await self._set_expiry(stream_id)

    async def append_chunk(self, stream_id: str, chunk: Dict[str, Any]) -> None:
        redis = await self._redis()
        key_set = _keys(stream_id)
        await redis.rpush(key_set.chunks, json.dumps(chunk))
        await redis.hset(key_set.meta, mapping={"updated_at": str(time.time())})
        await self._set_expiry(stream_id)

    async def mark_status(
        self,
        stream_id: str,
        *,
        status: str,
        done: bool,
        updates: Optional[Dict[str, Any]] = None,
    ) -> None:
        redis = await self._redis()
        key_set = _keys(stream_id)
        meta_raw = await redis.hget(key_set.meta, "metadata")
        meta = json.loads(meta_raw) if meta_raw else {}
        if updates:
            meta.update(dict(updates))
        mapping = {
            "status": status,
            "done": "1" if done else "0",
            "updated_at": str(time.time()),
            "metadata": json.dumps(meta),
        }
        await redis.hset(key_set.meta, mapping=mapping)
        await self._set_expiry(stream_id)

    async def poll_stream(self, stream_id: str) -> Optional[Dict[str, Any]]:
        try:
            redis = await self._redis()
            key_set = _keys(stream_id)
            if not await redis.exists(key_set.meta):
                return None

            meta = await redis.hgetall(key_set.meta)
            chunk_payloads = await redis.lrange(key_set.chunks, 0, -1)
            if chunk_payloads:
                await redis.ltrim(key_set.chunks, len(chunk_payloads), -1)

            chunks = []
            for payload in chunk_payloads:
                try:
                    chunks.append(json.loads(payload))
                except Exception:
                    logger.warning("stream_chunk_decode_failed", stream_id=stream_id)

            status = meta.get("status", "running")
            done = meta.get("done", "0") == "1" or _terminal(status)
            await self._set_expiry(stream_id)
            return {
                "stream_id": stream_id,
                "status": status,
                "chunks": chunks,
                "done": done,
            }
        except Exception as exc:
            logger.warning("stream_store_redis_poll_failed", stream_id=stream_id, error=str(exc))
            return None

    async def cancel_stream(self, stream_id: str) -> bool:
        try:
            redis = await self._redis()
            key_set = _keys(stream_id)
            if not await redis.exists(key_set.meta):
                return False
            await self.mark_status(stream_id, status="cancelled", done=True)
            return True
        except Exception as exc:
            logger.warning(
                "stream_store_redis_cancel_failed",
                stream_id=stream_id,
                error=str(exc),
            )
            return False


class HybridStreamStateStore:
    """Redis-first stream store with automatic in-memory fallback."""

    def __init__(self, *, ttl_seconds: int) -> None:
        self._redis_store = RedisStreamStateStore(ttl_seconds=ttl_seconds)
        self._memory_store = InMemoryStreamStateStore()
        self._redis_available: Optional[bool] = None

    async def _use_redis(self) -> bool:
        if self._redis_available is False:
            return False
        try:
            redis = await get_redis_client()
            await redis.ping()
            self._redis_available = True
            return True
        except Exception as exc:
            if self._redis_available is not False:
                logger.warning("stream_store_redis_unavailable", error=str(exc))
            self._redis_available = False
            return False

    async def create_stream(self, stream_id: str, metadata: Dict[str, Any]) -> None:
        if await self._use_redis():
            try:
                await self._redis_store.create_stream(stream_id, metadata)
                return
            except Exception as exc:
                logger.warning("stream_store_redis_create_failed", error=str(exc))
                self._redis_available = False
        await self._memory_store.create_stream(stream_id, metadata)

    async def append_chunk(self, stream_id: str, chunk: Dict[str, Any]) -> None:
        if await self._use_redis():
            try:
                await self._redis_store.append_chunk(stream_id, chunk)
                return
            except Exception as exc:
                logger.warning("stream_store_redis_append_failed", error=str(exc))
                self._redis_available = False
        await self._memory_store.append_chunk(stream_id, chunk)

    async def mark_status(
        self,
        stream_id: str,
        *,
        status: str,
        done: bool,
        updates: Optional[Dict[str, Any]] = None,
    ) -> None:
        if await self._use_redis():
            try:
                await self._redis_store.mark_status(
                    stream_id,
                    status=status,
                    done=done,
                    updates=updates,
                )
                return
            except Exception as exc:
                logger.warning("stream_store_redis_status_failed", error=str(exc))
                self._redis_available = False
        await self._memory_store.mark_status(
            stream_id,
            status=status,
            done=done,
            updates=updates,
        )

    async def poll_stream(self, stream_id: str) -> Optional[Dict[str, Any]]:
        if await self._use_redis():
            try:
                return await self._redis_store.poll_stream(stream_id)
            except Exception as exc:
                logger.warning("stream_store_redis_poll_failed", error=str(exc))
                self._redis_available = False
        return await self._memory_store.poll_stream(stream_id)

    async def cancel_stream(self, stream_id: str) -> bool:
        if await self._use_redis():
            try:
                return await self._redis_store.cancel_stream(stream_id)
            except Exception as exc:
                logger.warning("stream_store_redis_cancel_failed", error=str(exc))
                self._redis_available = False
        return await self._memory_store.cancel_stream(stream_id)


@lru_cache(maxsize=1)
def get_stream_state_store() -> StreamStateStore:
    ttl_seconds = int(os.getenv("STREAM_STATE_TTL_SECONDS", "3600"))
    fallback_env = os.getenv("STREAM_STATE_ALLOW_INMEMORY_FALLBACK")
    if fallback_env is None:
        environment = os.getenv("ENVIRONMENT", "development").strip().lower()
        allow_inmemory_fallback = environment != "production"
    else:
        allow_inmemory_fallback = fallback_env.lower() == "true"
    if allow_inmemory_fallback:
        return HybridStreamStateStore(ttl_seconds=ttl_seconds)
    return RedisStreamStateStore(ttl_seconds=ttl_seconds)
