"""Session lifecycle: cache key derivation, DB-backed create/check/revoke.

The Redis cache is a soft path — the DB is the source of truth for validity.
Legacy auth compatibility is removed for the v0.x -> v1.0 cutoff.
"""

import secrets
from datetime import datetime, timezone
from typing import Any, Optional, cast

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ...storage.cache import cache
from ...storage.models import UserSessionModel
from .config import REFRESH_MAX_AGE, SESSION_CACHE_PREFIX

LEGACY_AUTH_REMOVAL_TARGET = "v1.0"


def _session_cache_key(session_id: str) -> str:
    return f"{SESSION_CACHE_PREFIX}:{session_id}"


def _session_ttl_seconds(expires_at: Optional[datetime]) -> int:
    if not expires_at:
        return REFRESH_MAX_AGE
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    remaining = int((expires_at - now).total_seconds())
    return max(1, remaining)


def _record_ttl_seconds(record: Any) -> int:
    expires_at = getattr(record, "expires_at", None)
    return _session_ttl_seconds(cast(Optional[datetime], expires_at))


def _result_rowcount(result: Any) -> int:
    return int(getattr(result, "rowcount", 0) or 0)


async def _db_create_session(
    session_id: str,
    user_id: str,
    db: AsyncSession,
    expires_at: Optional[datetime] = None,
    skip_commit: bool = False,
) -> None:
    """Persist a new session to the database."""
    record = UserSessionModel(
        session_id=session_id,
        user_id=user_id,
        is_revoked=False,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        expires_at=expires_at,
    )
    db.add(record)
    if not skip_commit:
        await db.commit()

    # Best-effort cache warmup; DB remains source of truth.
    await cache.set(
        _session_cache_key(session_id),
        {"user_id": user_id, "revoked": False},
        expire=_session_ttl_seconds(expires_at),
    )


async def _db_is_session_valid(session_id: str, db: AsyncSession) -> bool:
    """Return True if the session exists and has not been revoked."""
    cached = await cache.get(_session_cache_key(session_id))
    if isinstance(cached, dict) and "revoked" in cached:
        return not bool(cached.get("revoked"))

    result = await db.execute(
        select(UserSessionModel).where(UserSessionModel.session_id == session_id)
    )
    record = cast(Any, result.scalar_one_or_none())
    if record is None:
        return False

    await cache.set(
        _session_cache_key(session_id),
        {"user_id": record.user_id, "revoked": bool(record.is_revoked)},
        expire=_record_ttl_seconds(record),
    )
    return not record.is_revoked


async def _db_revoke_session(session_id: str, db: AsyncSession) -> bool:
    """Mark a session as revoked. Returns True if the row existed."""
    result = cast(
        Any,
        await db.execute(
            update(UserSessionModel)
            .where(UserSessionModel.session_id == session_id)
            .values(is_revoked=True)
        ),
    )
    await db.commit()

    await cache.set(
        _session_cache_key(session_id),
        {"revoked": True},
        expire=REFRESH_MAX_AGE,
    )
    return _result_rowcount(result) > 0


def create_session_id(user_id: str) -> str:
    """Create a unique session ID."""
    _ = user_id  # kept for backward-compatible signature
    return secrets.token_urlsafe(32)
