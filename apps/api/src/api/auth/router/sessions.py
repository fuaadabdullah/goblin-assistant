"""Session lifecycle: cache key derivation, DB-backed create/check/revoke.

The Redis cache is a soft path — the DB is the source of truth for validity.
Legacy sync helpers (`revoke_session`, `is_session_valid`) remain as no-ops
so older callers keep importing without breaking.
"""

import secrets
from datetime import datetime
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ...storage.cache import cache
from ...storage.models import UserSessionModel
from .config import REFRESH_MAX_AGE, SESSION_CACHE_PREFIX


def _session_cache_key(session_id: str) -> str:
    return f"{SESSION_CACHE_PREFIX}:{session_id}"


def _session_ttl_seconds(expires_at: Optional[datetime]) -> int:
    if not expires_at:
        return REFRESH_MAX_AGE
    remaining = int((expires_at - datetime.utcnow()).total_seconds())
    return max(1, remaining)


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
        created_at=datetime.utcnow(),
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
    """Return True if the session exists and has not been revoked.

    Returns True for sessions not yet in DB — graceful fallback for pre-DB
    sessions still floating around in JWTs.
    """
    cached = await cache.get(_session_cache_key(session_id))
    if isinstance(cached, dict) and "revoked" in cached:
        return not bool(cached.get("revoked"))

    result = await db.execute(
        select(UserSessionModel).where(UserSessionModel.session_id == session_id)
    )
    record = result.scalar_one_or_none()
    if record is None:
        return True

    await cache.set(
        _session_cache_key(session_id),
        {"user_id": record.user_id, "revoked": bool(record.is_revoked)},
        expire=_session_ttl_seconds(record.expires_at),
    )
    return not record.is_revoked


async def _db_revoke_session(session_id: str, db: AsyncSession) -> bool:
    """Mark a session as revoked. Returns True if the row existed."""
    result = await db.execute(
        update(UserSessionModel)
        .where(UserSessionModel.session_id == session_id)
        .values(is_revoked=True)
    )
    await db.commit()

    await cache.set(
        _session_cache_key(session_id),
        {"revoked": True},
        expire=REFRESH_MAX_AGE,
    )
    return result.rowcount > 0


def create_session_id(user_id: str) -> str:
    """Create a unique session ID.

    Session persistence is handled by `_db_create_session`.
    """
    _ = user_id  # kept for backward-compatible signature
    return secrets.token_urlsafe(32)


def revoke_session(session_id: str) -> bool:
    """Legacy compatibility helper (no-op).

    Use `_db_revoke_session` for durable revocation.
    """
    _ = session_id
    return False


def is_session_valid(session_id: str) -> bool:
    """Legacy compatibility helper.

    Synchronous callers cannot perform DB/Redis I/O, so this returns True and
    auth enforcement must go through async `_db_is_session_valid`.
    """
    _ = session_id
    return True
