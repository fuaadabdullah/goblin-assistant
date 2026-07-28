"""Memory compaction and lifecycle garbage collection."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict

from sqlalchemy import delete, select, update

from ...storage.database import get_db_context
from ...storage.vector_models import EmbeddingModel, MemoryFactModel
from .classification import _is_pinned
from .models import MemoryLifecycleState, _safe_memory_state


async def compact_user_memory(
    *,
    user_id: str,
    archive_after_days: int = 90,
    delete_after_days: int = 365,
    min_salience: float = 0.25,
) -> Dict[str, int]:
    """Archive or delete stale low-salience records."""
    import structlog  # noqa: PLC0415

    logger = structlog.get_logger(__name__)
    archived = 0
    deleted = 0
    now = datetime.now(timezone.utc)
    tombstone_retention_days = 7

    async with get_db_context() as session:
        result = await session.execute(
            select(MemoryFactModel).where(MemoryFactModel.user_id == user_id)
        )
        rows = list(result.scalars())
        for row in rows:
            created_at = row.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            expires_at = row.expires_at
            if expires_at and expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            metadata = dict(row.metadata_ or {})
            pinned = _is_pinned(metadata)
            memory_state = _safe_memory_state(
                getattr(row, "memory_state", None)
                or metadata.get("memory_state")
                or metadata.get("state")
                or ("archived" if row.is_archived else None)
            )
            age_days = max(0.0, (now - created_at).total_seconds() / 86400.0)
            access_age_days = age_days
            if row.last_accessed_at:
                last_accessed = row.last_accessed_at
                if last_accessed.tzinfo is None:
                    last_accessed = last_accessed.replace(tzinfo=timezone.utc)
                access_age_days = max(0.0, (now - last_accessed).total_seconds() / 86400.0)
            expired = bool(expires_at and expires_at < now)
            effective_importance = float(
                metadata.get("importance")
                if metadata.get("importance") is not None
                else row.salience_score or 0.0
            )
            low_usage = (
                access_age_days >= archive_after_days and int(row.confirmation_count or 0) < 2
            )
            stale = (
                not pinned
                and access_age_days >= archive_after_days
                and (effective_importance < min_salience or low_usage)
            )
            terminal = age_days >= delete_after_days or (
                expired and age_days >= archive_after_days * 2
            )

            if memory_state == MemoryLifecycleState.DELETED and metadata.get("deleted_at"):
                try:
                    deleted_at = datetime.fromisoformat(
                        str(metadata["deleted_at"]).replace("Z", "+00:00")
                    )
                    if deleted_at.tzinfo is None:
                        deleted_at = deleted_at.replace(tzinfo=timezone.utc)
                    if (now - deleted_at).total_seconds() / 86400.0 < tombstone_retention_days:
                        continue
                except Exception:
                    pass
                await session.execute(delete(MemoryFactModel).where(MemoryFactModel.id == row.id))
                await session.execute(
                    delete(EmbeddingModel).where(
                        EmbeddingModel.user_id == user_id,
                        EmbeddingModel.source_type == "memory",
                        EmbeddingModel.source_id == row.id,
                    )
                )
                deleted += 1
                continue

            if stale and memory_state not in {
                MemoryLifecycleState.DEPRECATED,
                MemoryLifecycleState.ARCHIVED,
            }:
                metadata.update(
                    {
                        "memory_state": MemoryLifecycleState.DEPRECATED.value,
                        "state": MemoryLifecycleState.DEPRECATED.value,
                        "status": MemoryLifecycleState.DEPRECATED.value,
                        "deprecated_at": now.isoformat(),
                    }
                )
                await session.execute(
                    update(MemoryFactModel)
                    .where(MemoryFactModel.id == row.id)
                    .values(
                        memory_state=MemoryLifecycleState.DEPRECATED.value,
                        is_archived=False,
                        metadata_=metadata,
                        updated_at=now,
                    )
                )
                continue

            if memory_state == MemoryLifecycleState.DEPRECATED and (
                age_days >= archive_after_days * 2 or terminal
            ):
                await session.execute(
                    update(MemoryFactModel)
                    .where(MemoryFactModel.id == row.id)
                    .values(
                        memory_state=MemoryLifecycleState.ARCHIVED.value,
                        is_archived=True,
                        metadata_={**metadata, "archived_at": now.isoformat()},
                        updated_at=now,
                    )
                )
                archived += 1
                continue

            if terminal and memory_state != MemoryLifecycleState.DELETED:
                await session.execute(
                    update(MemoryFactModel)
                    .where(MemoryFactModel.id == row.id)
                    .values(
                        memory_state=MemoryLifecycleState.DELETED.value,
                        is_archived=True,
                        metadata_={**metadata, "deleted_at": now.isoformat()},
                        updated_at=now,
                    )
                )
                deleted += 1
                continue

        await session.commit()

    logger.info(
        "memory_compaction_completed",
        user_id=user_id,
        archived=archived,
        deleted=deleted,
    )
    return {"archived": archived, "deleted": deleted}
