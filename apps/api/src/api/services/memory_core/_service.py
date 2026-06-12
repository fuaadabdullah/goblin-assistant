"""Unified memory core service orchestrator."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

import structlog

from ..embedding_service import EmbeddingService
from ..memory_contract import confidence_band_from_score, importance_band_from_score
from ..sanitization import sanitize_input_for_model
from .classification import (
    _derive_memory_state,
    _normalize_kind,
    _normalize_scope,
    _sensitivity_from_flags,
)
from .compaction import compact_user_memory
from .entity_graph import _extract_entity_refs, _extract_related_ids
from .models import MemoryRecord, MemorySensitivity, _default_retention_days
from .privacy import _redact_sensitive_keywords
from .repository import _upsert_memory_record
from .scoring import (
    _clamp_score,
    _compute_memory_confidence,
    _compute_memory_importance,
    _derive_explicitness_score,
    _memory_confidence_reason,
    _memory_importance_reason,
)

logger = structlog.get_logger(__name__)


class MemoryCoreService:
    """Unified memory ingestion, retrieval, and compaction service."""

    def __init__(self) -> None:
        self.embedding_service = EmbeddingService()

    async def _upsert_memory_record(self, **kwargs: Any) -> Any:
        """Compatibility seam for tests and legacy callers."""
        return await _upsert_memory_record(self.embedding_service, **kwargs)

    async def ingest_text(
        self,
        *,
        user_id: str,
        text: str,
        source_kind: str,
        source_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        confidence: float = 0.8,
        explicit_kind: Optional[str] = None,
        allow_sensitive: bool = False,
    ) -> Optional[MemoryRecord]:
        """Ingest text into long-term memory after normalization and privacy checks."""
        if not user_id or not str(user_id).strip():
            logger.warning("memory_ingest_missing_user_id", source_kind=source_kind)
            return None
        metadata = dict(metadata or {})
        if conversation_id and "conversation_id" not in metadata:
            metadata["conversation_id"] = conversation_id
        if source_id and "source_id" not in metadata:
            metadata["source_id"] = source_id

        sanitized_text, pii_types = sanitize_input_for_model(text)
        sensitivity = _sensitivity_from_flags(text, metadata)
        if sensitivity == MemorySensitivity.HIGH and not allow_sensitive:
            metadata["sensitive_content_redacted"] = True
            metadata["pii_types"] = pii_types
            sanitized_text = _redact_sensitive_keywords(sanitized_text)
            if not sanitized_text.strip():
                logger.info(
                    "memory_ingest_skipped_sensitive",
                    user_id=user_id,
                    source_kind=source_kind,
                    source_id=source_id,
                )
                return None
            text = sanitized_text
        elif sanitized_text != text:
            text = sanitized_text
            metadata["sensitive_content_redacted"] = True
            metadata["pii_types"] = pii_types

        from ..message_classifier import MessageClassifier  # noqa: PLC0415

        classifier = MessageClassifier()
        classification = classifier.classify_message(text, "user")
        memory_type = _normalize_kind(
            explicit_kind=explicit_kind,
            message_type=classification.message_type,
            source_kind=source_kind,
            metadata=metadata,
        )
        scope = _normalize_scope(metadata, source_kind)
        retention_days = int(metadata.get("retention_days") or _default_retention_days(memory_type))
        repetition_count = int(metadata.get("repetition_count") or 1)
        authored = bool(
            metadata.get("authored")
            if metadata.get("authored") is not None
            else source_kind in {"chat", "message", "conversation", "memory"}
        )
        inferred = bool(
            metadata.get("inferred") if metadata.get("inferred") is not None else not authored
        )
        direct_correction = bool(metadata.get("direct_correction"))
        contradiction = bool(
            metadata.get("contradiction") or metadata.get("conflicts_with_existing")
        )
        later_contradicted = bool(metadata.get("later_contradicted"))
        explicitness_score = _derive_explicitness_score(text, metadata)
        conflict_penalty = _clamp_score(
            metadata.get("conflict_penalty")
            if metadata.get("conflict_penalty") is not None
            else (0.6 if contradiction else 0.0),
            0.0,
        )
        confidence_score = _compute_memory_confidence(
            base_confidence=confidence,
            explicitness=explicitness_score,
            repetition_count=repetition_count,
            authored=authored,
            inferred=inferred,
            direct_correction=direct_correction,
            contradiction=contradiction,
            later_contradicted=later_contradicted,
            conflict_penalty=conflict_penalty,
        )
        importance_score = _compute_memory_importance(
            repetition_count=repetition_count,
            use_frequency=metadata.get("use_frequency"),
            task_relevance=metadata.get("task_relevance"),
            explicit_emphasis=metadata.get("explicit_emphasis") or metadata.get("user_importance"),
            dependency_level=metadata.get("dependency_level"),
            future_behavior_impact=metadata.get("future_behavior_impact"),
            memory_type=memory_type,
            scope=scope,
        )
        confidence_band = confidence_band_from_score(confidence_score)
        importance_band = importance_band_from_score(importance_score)
        confidence_reason = _memory_confidence_reason(
            {
                **metadata,
                "authored": authored,
                "inferred": inferred,
                "direct_correction": direct_correction,
                "contradiction": contradiction,
                "later_contradicted": later_contradicted,
                "explicitness_score": explicitness_score,
                "repetition_count": repetition_count,
            }
        )
        importance_reason = _memory_importance_reason(
            {
                **metadata,
                "use_frequency": metadata.get("use_frequency") or repetition_count,
                "task_relevance": metadata.get("task_relevance"),
                "user_importance": metadata.get("explicit_emphasis")
                or metadata.get("user_importance"),
                "dependency_level": metadata.get("dependency_level"),
                "future_behavior_impact": metadata.get("future_behavior_impact"),
            }
        )
        salience_score = importance_score
        memory_state = _derive_memory_state(
            metadata=metadata,
            confidence=confidence_score,
            repetition_count=repetition_count,
            authored=authored,
            inferred=inferred,
            direct_correction=direct_correction,
            contradiction=contradiction,
            later_contradicted=later_contradicted,
            importance=importance_score,
            source_kind=source_kind,
            explicit_kind=explicit_kind,
        )
        metadata.update(
            {
                "scope": scope,
                "confidence": confidence_score,
                "confidence_band": confidence_band,
                "confidence_reason": confidence_reason,
                "importance": importance_score,
                "importance_band": importance_band,
                "importance_reason": importance_reason,
                "salience_score": salience_score,
                "authored": authored,
                "inferred": inferred,
                "direct_correction": direct_correction,
                "contradiction": contradiction,
                "later_contradicted": later_contradicted,
                "repetition_count": repetition_count,
                "explicitness_score": explicitness_score,
                "memory_state": memory_state.value,
                "state": memory_state.value,
                "status": memory_state.value,
            }
        )
        entity_refs = _extract_entity_refs(metadata)
        related_memory_ids = _extract_related_ids(metadata)

        record = await self._upsert_memory_record(
            user_id=user_id,
            text=text,
            source_kind=source_kind,
            source_id=source_id,
            memory_type=memory_type,
            category=metadata.get("category") or memory_type.value,
            confidence=confidence_score,
            confidence_band=confidence_band,
            confidence_reason=confidence_reason,
            importance=importance_score,
            importance_band=importance_band,
            importance_reason=importance_reason,
            salience_score=salience_score,
            sensitivity=sensitivity,
            memory_state=memory_state,
            retention_days=retention_days,
            metadata=metadata,
            related_memory_ids=related_memory_ids,
            entity_refs=entity_refs,
            scope=scope,
            authored=authored,
            inferred=inferred,
            direct_correction=direct_correction,
            contradiction=contradiction,
            later_contradicted=later_contradicted,
            repetition_count=repetition_count,
            explicitness_score=explicitness_score,
        )

        logger.info(
            "memory_ingested",
            user_id=user_id,
            source_kind=source_kind,
            source_id=source_id,
            memory_type=memory_type.value,
            salience_score=round(salience_score, 3),
            confidence=round(confidence_score, 3),
            confidence_band=confidence_band,
            importance=round(importance_score, 3),
            importance_band=importance_band,
            sensitivity=sensitivity.value,
        )
        return record

    async def ingest_memory_fact(
        self,
        *,
        user_id: str,
        fact_text: str,
        category: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        source_kind: str = "memory",
        source_id: Optional[str] = None,
        explicit_kind: Optional[str] = None,
        confidence: float = 0.8,
        allow_sensitive: bool = False,
    ) -> Optional[MemoryRecord]:
        metadata = dict(metadata or {})
        if category and "category" not in metadata:
            metadata["category"] = category
        return await self.ingest_text(
            user_id=user_id,
            text=fact_text,
            source_kind=source_kind,
            source_id=source_id,
            metadata=metadata,
            confidence=confidence,
            explicit_kind=explicit_kind or category,
            allow_sensitive=allow_sensitive,
        )

    async def retrieve_memory_context(
        self,
        *,
        user_id: str,
        query: str,
        limit: int = 5,
        categories: Optional[Sequence[str]] = None,
    ) -> List[Dict[str, Any]]:
        from ..memory_contract import canonicalize_memory_item  # noqa: PLC0415
        from ..memory_reranker import memory_reranker  # noqa: PLC0415
        from ..retrieval_service import retrieval_service  # noqa: PLC0415

        results = await retrieval_service.retrieve_memory_facts(
            user_id=user_id,
            query=query,
            categories=list(categories) if categories else None,
            k=limit,
        )
        if not results:
            return []
        ranked = memory_reranker.rerank(results, query=query, top_k=limit)
        return [canonicalize_memory_item(item, user_id=user_id) for item in ranked]

    async def export_user_memory(self, user_id: str) -> List[Dict[str, Any]]:
        from sqlalchemy import select  # noqa: PLC0415

        from ...storage.database import get_readonly_db_context  # noqa: PLC0415
        from ...storage.vector_models import MemoryFactModel  # noqa: PLC0415
        from .repository import _record_from_model  # noqa: PLC0415

        async with get_readonly_db_context() as session:
            result = await session.execute(
                select(MemoryFactModel)
                .where(MemoryFactModel.user_id == user_id)
                .order_by(MemoryFactModel.created_at.desc())
            )
            records = []
            for row in result.scalars():
                records.append(_record_from_model(row).to_dict())
            return records

    async def delete_user_memory(self, user_id: str) -> Dict[str, int]:
        from sqlalchemy import delete  # noqa: PLC0415

        from ...storage.database import get_db_context  # noqa: PLC0415
        from ...storage.vector_models import EmbeddingModel, MemoryFactModel  # noqa: PLC0415

        async with get_db_context() as session:
            memory_delete = await session.execute(
                delete(MemoryFactModel).where(MemoryFactModel.user_id == user_id)
            )
            embedding_delete = await session.execute(
                delete(EmbeddingModel).where(
                    EmbeddingModel.user_id == user_id,
                    EmbeddingModel.source_type == "memory",
                )
            )
            await session.commit()
        return {
            "memory_records": int(memory_delete.rowcount or 0),
            "memory_embeddings": int(embedding_delete.rowcount or 0),
        }

    async def compact_user_memory(
        self,
        *,
        user_id: str,
        archive_after_days: int = 90,
        delete_after_days: int = 365,
        min_salience: float = 0.25,
    ) -> Dict[str, int]:
        """Archive or delete stale low-salience records."""
        return await compact_user_memory(
            user_id=user_id,
            archive_after_days=archive_after_days,
            delete_after_days=delete_after_days,
            min_salience=min_salience,
        )


memory_core_service = MemoryCoreService()
