"""Database repository layer for memory persistence operations."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import select

from ...storage.database import get_db_context
from ...storage.vector_models import EmbeddingModel, MemoryFactModel
from ..memory_contract import confidence_band_from_score, importance_band_from_score
from .classification import _merge_memory_state, _normalize_scope
from .entity_graph import _persist_entity_graph
from .models import (
    MemoryKind,
    MemoryLifecycleState,
    MemoryRecord,
    MemorySensitivity,
    _safe_memory_kind,
    _safe_memory_state,
    _safe_sensitivity,
)


async def _deprecate_conflicting_records(
    session: Any,
    *,
    user_id: str,
    memory_ids: Sequence[str],
    reason: str,
    replacement_memory_id: Optional[str],
    metadata: Dict[str, Any],
) -> int:
    updated = 0
    now = datetime.now(timezone.utc)
    for memory_id in memory_ids:
        if not memory_id:
            continue
        result = await session.execute(
            select(MemoryFactModel).where(
                MemoryFactModel.id == memory_id,
                MemoryFactModel.user_id == user_id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            continue
        current_meta = dict(row.metadata_ or {})
        current_meta.update(
            {
                "deprecated_reason": reason,
                "deprecated_at": now.isoformat(),
                "replacement_memory_id": replacement_memory_id,
                "conflict_metadata": metadata,
                "memory_state": MemoryLifecycleState.DEPRECATED.value,
                "state": MemoryLifecycleState.DEPRECATED.value,
                "status": MemoryLifecycleState.DEPRECATED.value,
            }
        )
        row.memory_state = MemoryLifecycleState.DEPRECATED.value
        row.is_archived = False
        row.metadata_ = current_meta
        row.updated_at = now.replace(tzinfo=None)
        updated += 1
    return updated


def _record_from_model(row: MemoryFactModel) -> MemoryRecord:
    created_at = row.created_at
    updated_at = row.updated_at or row.created_at
    last_accessed_at = row.last_accessed_at
    expires_at = row.expires_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    if updated_at and updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)
    if last_accessed_at and last_accessed_at.tzinfo is None:
        last_accessed_at = last_accessed_at.replace(tzinfo=timezone.utc)
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    metadata = dict(row.metadata_ or {})
    scope = str(
        getattr(row, "scope", None)
        or metadata.get("scope")
        or _normalize_scope(metadata, row.source_kind or "memory")
    )
    memory_state = _safe_memory_state(
        getattr(row, "memory_state", None)
        or metadata.get("memory_state")
        or metadata.get("state")
        or ("archived" if row.is_archived else None)
    )
    confidence = float(row.confidence or metadata.get("confidence") or 0.0)
    importance = float(
        metadata.get("importance")
        if metadata.get("importance") is not None
        else row.salience_score or metadata.get("salience_score") or 0.0
    )
    confidence_band = str(metadata.get("confidence_band") or confidence_band_from_score(confidence))
    importance_band = str(metadata.get("importance_band") or importance_band_from_score(importance))
    authored = bool(metadata.get("authored"))
    inferred = bool(metadata.get("inferred"))
    direct_correction = bool(metadata.get("direct_correction"))
    contradiction = bool(metadata.get("contradiction"))
    later_contradicted = bool(metadata.get("later_contradicted"))
    repetition_count = int(metadata.get("repetition_count") or row.confirmation_count or 1)
    explicitness_score = float(metadata.get("explicitness_score") or 0.0)
    confidence_reason = str(metadata.get("confidence_reason") or "")
    importance_reason = str(metadata.get("importance_reason") or "")

    return MemoryRecord(
        id=row.id,
        user_id=row.user_id,
        content=row.fact_text,
        memory_type=_safe_memory_kind(row.memory_type or row.category),
        category=row.category,
        source_kind=row.source_kind or "memory",
        source_id=row.source_id,
        confidence=confidence,
        salience_score=float(row.salience_score or importance),
        sensitivity_level=_safe_sensitivity(row.sensitivity_level),
        state=memory_state,
        retention_days=int(row.retention_days or 0),
        created_at=created_at,
        updated_at=updated_at or created_at,
        expires_at=expires_at,
        last_accessed_at=last_accessed_at,
        confirmation_count=int(row.confirmation_count or 0),
        is_archived=bool(
            row.is_archived
            or memory_state
            in {
                MemoryLifecycleState.ARCHIVED,
                MemoryLifecycleState.DELETED,
            }
        ),
        embedding_id=metadata.get("embedding_id"),
        related_memory_ids=list(row.related_memory_ids or []),
        entity_refs=list(row.entity_refs or []),
        metadata=metadata,
        scope=scope,
        confidence_band=confidence_band,
        confidence_reason=confidence_reason,
        importance=importance,
        importance_band=importance_band,
        importance_reason=importance_reason,
        authored=authored,
        inferred=inferred,
        direct_correction=direct_correction,
        contradiction=contradiction,
        later_contradicted=later_contradicted,
        repetition_count=repetition_count,
        explicitness_score=explicitness_score,
    )


async def _upsert_memory_record(
    embedding_service: Any,
    *,
    user_id: str,
    text: str,
    source_kind: str,
    source_id: Optional[str],
    memory_type: MemoryKind,
    category: Optional[str],
    confidence: float,
    confidence_band: str,
    confidence_reason: str,
    importance: float,
    importance_band: str,
    importance_reason: str,
    salience_score: float,
    sensitivity: MemorySensitivity,
    memory_state: MemoryLifecycleState,
    retention_days: int,
    metadata: Dict[str, Any],
    related_memory_ids: List[str],
    entity_refs: List[Dict[str, Any]],
    scope: str,
    authored: bool,
    inferred: bool,
    direct_correction: bool,
    contradiction: bool,
    later_contradicted: bool,
    repetition_count: int,
    explicitness_score: float,
) -> Optional[MemoryRecord]:
    import structlog  # noqa: PLC0415

    from ..embedding_service import EmbeddingProviderUnavailableError  # noqa: PLC0415

    logger = structlog.get_logger(__name__)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=retention_days) if retention_days > 0 else None
    async with get_db_context() as session:
        conflicting_ids = [
            str(memory_id)
            for memory_id in (
                metadata.get("supersedes_memory_ids")
                or metadata.get("conflicting_memory_ids")
                or []
            )
            if str(memory_id).strip()
        ]
        if conflicting_ids:
            await _deprecate_conflicting_records(
                session,
                user_id=user_id,
                memory_ids=conflicting_ids,
                reason=str(metadata.get("conflict_reason") or "superseded by newer memory"),
                replacement_memory_id=metadata.get("replacement_memory_id"),
                metadata=metadata,
            )
        result = await session.execute(
            select(MemoryFactModel).where(
                MemoryFactModel.user_id == user_id,
                MemoryFactModel.fact_text == text,
                MemoryFactModel.memory_type == memory_type.value,
            )
        )
        existing = result.scalar_one_or_none()

        embedding: Optional[List[float]] = None
        embedding_id: Optional[str] = None
        try:
            embedding = await embedding_service.embed_text(text)
        except EmbeddingProviderUnavailableError as exc:
            logger.warning("memory_embedding_unavailable", user_id=user_id, error=str(exc))
        except Exception as exc:
            logger.warning("memory_embedding_failed", user_id=user_id, error=str(exc))

        if existing is not None:
            existing.category = category
            existing.source_kind = source_kind
            existing.source_id = source_id
            existing.confidence = confidence
            existing.salience_score = salience_score
            existing.sensitivity_level = sensitivity.value
            existing.memory_state = _merge_memory_state(existing.memory_state, memory_state).value
            existing.retention_days = retention_days
            existing.expires_at = expires_at
            existing.last_accessed_at = now
            existing.confirmation_count = int(existing.confirmation_count or 0) + max(
                1, repetition_count
            )
            existing.related_memory_ids = related_memory_ids
            existing.entity_refs = entity_refs
            existing.scope = scope
            current_meta = dict(existing.metadata_ or {})
            current_meta.update(metadata)
            current_meta["scope"] = scope
            current_meta["confidence"] = confidence
            current_meta["confidence_band"] = confidence_band
            current_meta["confidence_reason"] = confidence_reason
            current_meta["importance"] = importance
            current_meta["importance_band"] = importance_band
            current_meta["importance_reason"] = importance_reason
            current_meta["memory_type"] = memory_type.value
            current_meta["sensitivity_level"] = sensitivity.value
            current_meta["salience_score"] = salience_score
            current_meta["retention_days"] = retention_days
            current_meta["authored"] = authored
            current_meta["inferred"] = inferred
            current_meta["direct_correction"] = direct_correction
            current_meta["contradiction"] = contradiction
            current_meta["later_contradicted"] = later_contradicted
            current_meta["repetition_count"] = repetition_count
            current_meta["explicitness_score"] = explicitness_score
            current_meta["memory_state"] = existing.memory_state
            current_meta["state"] = existing.memory_state
            current_meta["status"] = existing.memory_state
            if existing.metadata_ and isinstance(existing.metadata_, dict):
                embedding_id = existing.metadata_.get("embedding_id")
            existing.metadata_ = current_meta
            if embedding:
                existing.fact_embedding = embedding
            existing.is_archived = existing.memory_state in {
                MemoryLifecycleState.ARCHIVED.value,
                MemoryLifecycleState.DELETED.value,
            }
            existing.updated_at = now
            await session.flush()
            try:
                await _persist_entity_graph(
                    session,
                    user_id=user_id,
                    memory_fact_id=existing.id,
                    entity_refs=entity_refs,
                    related_memory_ids=related_memory_ids,
                    memory_type=memory_type,
                    scope=scope,
                )
            except Exception as exc:
                logger.warning("entity_graph_persist_failed", user_id=user_id, error=str(exc))
            await session.refresh(existing)
            return _record_from_model(existing)

        record = MemoryFactModel(
            user_id=user_id,
            fact_text=text,
            fact_embedding=embedding,
            category=category,
            memory_type=memory_type.value,
            source_kind=source_kind,
            source_id=source_id,
            salience_score=salience_score,
            confidence=confidence,
            memory_state=memory_state.value,
            scope=scope,
            metadata_=dict(
                metadata,
                scope=scope,
                confidence=confidence,
                confidence_band=confidence_band,
                confidence_reason=confidence_reason,
                importance=importance,
                importance_band=importance_band,
                importance_reason=importance_reason,
                memory_type=memory_type.value,
                sensitivity_level=sensitivity.value,
                salience_score=salience_score,
                retention_days=retention_days,
                source_kind=source_kind,
                source_id=source_id,
                authored=authored,
                inferred=inferred,
                direct_correction=direct_correction,
                contradiction=contradiction,
                later_contradicted=later_contradicted,
                repetition_count=repetition_count,
                explicitness_score=explicitness_score,
                memory_state=memory_state.value,
                state=memory_state.value,
                status=memory_state.value,
                embedding_id=embedding_id,
            ),
            sensitivity_level=sensitivity.value,
            retention_days=retention_days,
            expires_at=expires_at,
            last_accessed_at=now,
            confirmation_count=1,
            is_archived=memory_state
            in {
                MemoryLifecycleState.ARCHIVED,
                MemoryLifecycleState.DELETED,
            },
            related_memory_ids=related_memory_ids,
            entity_refs=entity_refs,
            created_at=now.replace(tzinfo=None),
        )
        session.add(record)
        await session.flush()

        try:
            await _persist_entity_graph(
                session,
                user_id=user_id,
                memory_fact_id=record.id,
                entity_refs=entity_refs,
                related_memory_ids=related_memory_ids,
                memory_type=memory_type,
                scope=scope,
            )
        except Exception as exc:
            logger.warning("entity_graph_persist_failed", user_id=user_id, error=str(exc))

        if embedding:
            embedding_row = EmbeddingModel(
                user_id=user_id,
                conversation_id=metadata.get("conversation_id"),
                source_type="memory",
                source_id=record.id,
                embedding=embedding,
                content=text,
                metadata_=dict(
                    metadata,
                    memory_type=memory_type.value,
                    category=category,
                    salience_score=salience_score,
                    sensitivity_level=sensitivity.value,
                    memory_state=memory_state.value,
                ),
            )
            session.add(embedding_row)
            await session.flush()
            embedding_id = embedding_row.id
            record.metadata_ = dict(record.metadata_ or {}, embedding_id=embedding_id)
            record.updated_at = now

        await session.commit()
        await session.refresh(record)
        return _record_from_model(record)
