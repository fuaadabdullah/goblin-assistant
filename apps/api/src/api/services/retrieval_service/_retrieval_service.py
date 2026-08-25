"""
Orchestrating RetrievalService class.

This is the public face of the retrieval_service package.  It coordinates
the retrieval pipeline:
  1. Embed the query
  2. Run stratified retrieval (SQL queries in ``_sql_retrieval``)
  3. Optionally trace to observability
  4. Assemble a context bundle (via ``_context_bundle``)
"""

import time
from datetime import datetime, timezone
from math import sqrt
from typing import Any, Dict, List, Optional, Tuple

import structlog
from sqlalchemy import select, text

from ...storage.database import get_readonly_db_context
from ..context_builder import LegacyContextBuilder
from ..embedding_service import EmbeddingProviderUnavailableError, EmbeddingService
from ..memory_contract import _normalize_embedding, canonicalize_memory_item
from ._context_bundle import build_context_bundle
from ._limits import clamp_prompt_retrieval_k
from ._sql_retrieval import (
    retrieve_by_source_type,
    retrieve_graph_expanded_memories,
    retrieve_memory_facts_stratified,
    retrieve_messages_stratified,
    retrieve_recent_messages,
    retrieve_summaries_stratified,
)

logger = structlog.get_logger()


def _coerce_naive_datetime(value: Any) -> Optional[datetime]:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _cosine_similarity(lhs: List[float], rhs: List[float]) -> float:
    left = [float(value) for value in lhs if value is not None]
    right = [float(value) for value in rhs if value is not None]
    if not left or not right:
        return 0.0

    length = min(len(left), len(right))
    left = left[:length]
    right = right[:length]
    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return 0.0

    return sum(lv * rv for lv, rv in zip(left, right)) / (left_norm * right_norm)


def _memory_state_rank(value: Optional[str]) -> int:
    state = (value or "").strip().lower()
    return {
        "verified": 4,
        "active": 3,
        "candidate": 2,
        "deprecated": 1,
    }.get(state, 0)


def _confidence_rank(value: float) -> int:
    if value >= 0.90:
        return 3
    if value >= 0.70:
        return 2
    if value >= 0.40:
        return 1
    return 0


class RetrievalService:
    """Service for semantic retrieval with hybrid scoring"""

    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.semantic_weight = 0.7
        self.recency_weight = 0.2
        self.source_priority_weight = 0.1
        self._degraded_mode = False
        self._degraded_reason: Optional[str] = None

    def get_degraded_status(self) -> Dict[str, Any]:
        return {
            "degraded_mode": self._degraded_mode,
            "reason": self._degraded_reason,
        }

    def _set_degraded(self, reason: str) -> None:
        self._degraded_mode = True
        self._degraded_reason = reason

    def _clear_degraded(self) -> None:
        self._degraded_mode = False
        self._degraded_reason = None

    async def _retrieve_memory_facts_sqlite(
        self,
        *,
        query_embedding: List[float],
        user_id: str,
        categories: Optional[List[str]],
        k: int,
    ) -> List[Dict[str, Any]]:
        from ...storage.vector_models import MemoryFactModel  # noqa: PLC0415

        category_filter = {
            str(category).strip() for category in (categories or []) if str(category).strip()
        }
        now = datetime.utcnow()

        async with get_readonly_db_context() as session:
            result = await session.execute(
                select(MemoryFactModel).where(MemoryFactModel.user_id == user_id)
            )
            rows = result.scalars().all()

        scored_rows: List[tuple[tuple[int, int, float, float, float], Dict[str, Any]]] = []
        for row in rows:
            row_category = getattr(row, "category", None)
            if category_filter and row_category not in category_filter:
                continue

            row_metadata = dict(getattr(row, "metadata_", None) or {})
            state = str(
                getattr(row, "memory_state", None)
                or row_metadata.get("memory_state")
                or row_metadata.get("state")
                or "active"
            )
            if state.lower() in {"archived", "deleted"} or bool(getattr(row, "is_archived", False)):
                continue

            expires_at = _coerce_naive_datetime(getattr(row, "expires_at", None))
            if expires_at is not None and expires_at <= now:
                continue

            row_embedding_value = getattr(row, "fact_embedding", None)
            if row_embedding_value is None:
                row_embedding_value = row_metadata.get("embedding")
            if row_embedding_value is None:
                row_embedding_value = row_metadata.get("fact_embedding")
            row_embedding = _normalize_embedding(row_embedding_value)
            similarity_score = _cosine_similarity(query_embedding, row_embedding)
            confidence_value = getattr(row, "confidence", None)
            if confidence_value is None:
                confidence_value = row_metadata.get("confidence")
            salience_value = getattr(row, "salience_score", None)
            if salience_value is None:
                salience_value = row_metadata.get("salience_score")
            confidence = float(confidence_value or 0.0)
            salience = float(salience_value or 0.0)
            created_at = _coerce_naive_datetime(getattr(row, "created_at", None)) or datetime.min

            scored_rows.append(
                (
                    (
                        _memory_state_rank(state),
                        _confidence_rank(confidence),
                        similarity_score,
                        salience,
                        created_at.timestamp() if created_at != datetime.min else 0.0,
                    ),
                    canonicalize_memory_item(
                        {
                            "id": row.id,
                            "fact_text": row.fact_text,
                            "content": row.fact_text,
                            "embedding": row_embedding,
                            "category": row_category,
                            "memory_type": getattr(row, "memory_type", None) or row_category,
                            "source_kind": getattr(row, "source_kind", None),
                            "source_id": getattr(row, "source_id", None),
                            "salience_score": salience,
                            "confidence": confidence,
                            "memory_state": state,
                            "sensitivity_level": getattr(row, "sensitivity_level", None),
                            "retention_days": getattr(row, "retention_days", None),
                            "expires_at": getattr(row, "expires_at", None),
                            "last_accessed_at": getattr(row, "last_accessed_at", None),
                            "confirmation_count": getattr(row, "confirmation_count", None),
                            "is_archived": bool(getattr(row, "is_archived", False)),
                            "related_memory_ids": getattr(row, "related_memory_ids", None),
                            "entity_refs": getattr(row, "entity_refs", None),
                            "metadata": row_metadata,
                            "created_at": getattr(row, "created_at", None),
                            "score": similarity_score,
                        },
                        user_id=user_id,
                        source_type="memory",
                    ),
                )
            )

        scored_rows.sort(key=lambda item: item[0], reverse=True)
        return [item[1] for item in scored_rows[:k]]

    async def retrieve_context(
        self,
        query: str,
        user_id: str,
        conversation_id: Optional[str] = None,
        k: int = 5,
        max_age_hours: int = 168,  # 7 days default
        context_scope: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant context using memory stratification priority

        Args:
            query: User query to find relevant context for
            user_id: User identifier for isolation
            conversation_id: Optional conversation to limit scope
            k: Number of results to return
            max_age_hours: Maximum age of embeddings to consider
        """
        if not query or not user_id:
            return []
        self._clear_degraded()

        try:
            # Generate query embedding
            try:
                query_embedding = await self.embedding_service.embed_text(query)
            except EmbeddingProviderUnavailableError as embed_err:
                self._set_degraded(str(embed_err))
                return []
            except Exception as embed_err:
                self._set_degraded(str(embed_err))
                return []

            if not query_embedding:
                return []

            # Retrieve context using stratified priority
            results, tier_timings = await self._stratified_retrieval(
                query_embedding=query_embedding,
                query=query,
                user_id=user_id,
                conversation_id=conversation_id,
                k=k,
                max_age_hours=max_age_hours,
                context_scope=context_scope,
            )
            try:
                from ..retrieval_metrics_service import retrieval_metrics_service

                retrieval_metrics_service.record_retrieval_timing(user_id, tier_timings)
            except Exception:
                pass

            # Log retrieval trace to observability system
            try:
                # Import here to avoid circular imports
                from ..observability_service import observability_service

                # Build retrieval trace data
                total_tokens_used = sum(len(r.get("content", "")) // 4 for r in results)
                retrieval_trace_data = {
                    "request_id": f"retrieval_{datetime.utcnow().isoformat()}",
                    "user_id": user_id,
                    "model_selected": "retrieval_service",
                    "token_budget": total_tokens_used,
                    "retrieval_result": {
                        "layers": [
                            {
                                "name": result.get("source_type", "unknown"),
                                "tokens": len(result.get("content", ""))
                                // 4,  # Rough token estimation
                                "score": result.get("score", 0.0),
                                "original_tokens": len(result.get("content", "")) // 4,
                            }
                            for result in results
                        ]
                    },
                }

                observability_service.log_retrieval_trace(**retrieval_trace_data)
            except Exception as e:
                logger.warning(
                    "failed to log retrieval trace to observability",
                    error=str(e),
                    user_id=user_id,
                    conversation_id=conversation_id,
                )

            return results

        except Exception as e:
            logger.error(
                "error in retrieve_context",
                error=str(e),
                user_id=user_id,
                conversation_id=conversation_id,
            )
            return []

    async def _stratified_retrieval(
        self,
        query_embedding: List[float],
        query: str,
        user_id: str,
        conversation_id: Optional[str] = None,
        k: int = 5,
        max_age_hours: int = 168,
        context_scope: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, float]]:
        """Retrieve context using memory stratification priority.

        Returns (results, tier_timings_ms).
        """
        all_results: List[Dict[str, Any]] = []
        timings: Dict[str, float] = {}

        t0 = time.perf_counter()
        all_results.extend(
            await retrieve_memory_facts_stratified(
                query_embedding=query_embedding,
                user_id=user_id,
                k=min(k, 3),
            )
        )
        timings["long_term"] = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        all_results.extend(
            await retrieve_summaries_stratified(
                query_embedding=query_embedding,
                user_id=user_id,
                conversation_id=conversation_id,
                k=min(k, 2),
            )
        )
        timings["summary"] = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        for stype in ["document", "code", "research", "task"]:
            all_results.extend(
                await retrieve_by_source_type(
                    query_embedding=query_embedding,
                    user_id=user_id,
                    source_type=stype,
                    k=min(k, 3),
                )
            )
        timings["index"] = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        try:
            from ..memory_entries_service import memory_entries_service  # noqa: PLC0415

            all_results.extend(
                await memory_entries_service.search(
                    query,
                    user_id=user_id,
                    source_kinds=["repo_doc", "repo_code", "agent_run"],
                    limit=min(k, 4),
                )
            )
        except Exception:
            pass
        _memory_entries_elapsed_ms = (time.perf_counter() - t0) * 1000

        # Stage 4: Graph expansion — find memory facts connected via entity relations
        t0 = time.perf_counter()
        seed_ids = [
            r["id"] for r in all_results if r.get("id") and r.get("source_type") == "memory"
        ]
        if seed_ids:
            graph_results = await retrieve_graph_expanded_memories(
                user_id=user_id,
                seed_memory_ids=seed_ids,
                k=min(k, 3),
            )
            existing_ids = {r["id"] for r in all_results}
            all_results.extend(gr for gr in graph_results if gr.get("id") not in existing_ids)
        _graph_elapsed_ms = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        all_results.extend(
            await retrieve_messages_stratified(
                query_embedding=query_embedding,
                user_id=user_id,
                conversation_id=conversation_id,
                k=min(k, 3),
            )
        )
        timings["messages"] = (time.perf_counter() - t0) * 1000

        remaining_k = k - len(all_results)
        t0 = time.perf_counter()
        if remaining_k > 0:
            all_results.extend(
                await retrieve_recent_messages(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    k=remaining_k,
                )
            )
        timings["recent"] = (time.perf_counter() - t0) * 1000

        # Attach context_scope to each result so the reranker can compute scope_match
        if context_scope:
            for r in all_results:
                meta = r.get("metadata")
                if isinstance(meta, dict):
                    meta["_context_scope"] = context_scope
                else:
                    r["metadata"] = {"_context_scope": context_scope}

        all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return all_results[:k], timings

    async def retrieve_conversation_summaries(
        self,
        user_id: str,
        conversation_ids: List[str],
        k: int = 3,
    ) -> List[Dict[str, Any]]:
        """Retrieve summaries for specific conversations"""
        if not conversation_ids:
            return []

        async with get_readonly_db_context() as session:
            query = text(
                """
                SELECT
                    cs.id,
                    cs.conversation_id,
                    cs.summary_text,
                    cs.created_at
                FROM conversation_summaries cs
                WHERE cs.conversation_id = ANY(:conversation_ids)
                ORDER BY cs.created_at DESC
                LIMIT :k
            """
            )

            result = await session.execute(query, {"conversation_ids": conversation_ids, "k": k})
            rows = result.fetchall()

            return [
                {
                    "id": row.id,
                    "conversation_id": row.conversation_id,
                    "summary_text": row.summary_text,
                    "created_at": row.created_at,
                    "source_type": "summary",
                }
                for row in rows
            ]

    async def retrieve_memory_facts(
        self,
        user_id: str,
        query: str,
        categories: Optional[List[str]] = None,
        k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant memory facts"""
        if not query:
            return []

        try:
            try:
                query_embedding = await self.embedding_service.embed_text(query)
            except EmbeddingProviderUnavailableError as embed_err:
                self._set_degraded(str(embed_err))
                return []
            except Exception as embed_err:
                self._set_degraded(str(embed_err))
                return []

            if not query_embedding:
                return []

            async with get_readonly_db_context() as session:
                dialect_name = getattr(getattr(session, "bind", None), "dialect", None)
                if getattr(dialect_name, "name", "") == "sqlite":
                    return await self._retrieve_memory_facts_sqlite(
                        query_embedding=query_embedding,
                        user_id=user_id,
                        categories=categories,
                        k=k,
                    )

                where_clauses = ["mf.user_id = :user_id"]
                params = {
                    "user_id": user_id,
                    "query_embedding": query_embedding,
                    "k": k,
                }

                if categories:
                    where_clauses.append("mf.category = ANY(:categories)")
                    params["categories"] = categories

                where_clause = " AND ".join(where_clauses)

                stmt = text(
                    f"""
                    SELECT
                        mf.id,
                        mf.fact_text,
                        mf.fact_embedding,
                        mf.category,
                        mf.memory_type,
                        mf.source_kind,
                        mf.source_id,
                        mf.salience_score,
                        mf.confidence,
                        mf.memory_state,
                        mf.sensitivity_level,
                        mf.retention_days,
                        mf.expires_at,
                        mf.last_accessed_at,
                        mf.confirmation_count,
                        mf.is_archived,
                        mf.related_memory_ids,
                        mf.entity_refs,
                        mf.metadata,
                        mf.created_at,
                        (1 - (mf.fact_embedding <=> :query_embedding)) as similarity_score
                    FROM memory_facts mf
                    WHERE {where_clause}
                      AND COALESCE(mf.memory_state, 'active') NOT IN ('archived', 'deleted')
                      AND (mf.expires_at IS NULL OR mf.expires_at > NOW())
                    ORDER BY
                    CASE
                        WHEN COALESCE(mf.memory_state, 'active') = 'verified' THEN 4
                        WHEN COALESCE(mf.memory_state, 'active') = 'active' THEN 3
                        WHEN COALESCE(mf.memory_state, 'active') = 'candidate' THEN 2
                        WHEN COALESCE(mf.memory_state, 'active') = 'deprecated' THEN 1
                        ELSE 0
                    END DESC,
                    CASE
                        WHEN COALESCE(mf.confidence, 0) >= 0.90 THEN 3
                        WHEN COALESCE(mf.confidence, 0) >= 0.70 THEN 2
                        WHEN COALESCE(mf.confidence, 0) >= 0.40 THEN 1
                        ELSE 0
                    END DESC,
                    similarity_score DESC
                    , COALESCE(mf.salience_score, 0) DESC
                    , mf.created_at DESC
                    LIMIT :k
                """
                )

                result = await session.execute(stmt, params)
                rows = result.fetchall()

                return [
                    canonicalize_memory_item(
                        {
                            "id": row.id,
                            "fact_text": row.fact_text,
                            "embedding": row.fact_embedding,
                            "category": row.category,
                            "memory_type": row.memory_type or row.category,
                            "source_kind": row.source_kind,
                            "source_id": row.source_id,
                            "salience_score": row.salience_score,
                            "confidence": row.confidence,
                            "memory_state": row.memory_state,
                            "sensitivity_level": row.sensitivity_level,
                            "retention_days": row.retention_days,
                            "expires_at": row.expires_at,
                            "last_accessed_at": row.last_accessed_at,
                            "confirmation_count": row.confirmation_count,
                            "is_archived": row.is_archived,
                            "related_memory_ids": row.related_memory_ids,
                            "entity_refs": row.entity_refs,
                            "metadata": row.metadata,
                            "created_at": row.created_at,
                            "score": (float(row.similarity_score) if row.similarity_score else 0.0),
                            "source_type": "memory",
                        },
                        user_id=user_id,
                        source_type="memory",
                    )
                    for row in rows
                ]

        except Exception as e:
            logger.error(
                "error retrieving memory facts",
                error=str(e),
                user_id=user_id,
                categories=categories,
            )
            return []

    async def retrieve_by_index(
        self,
        index_name: str,
        query: str,
        user_id: str,
        k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Targeted retrieval from a single named index.

        Lets individual goblins query one index directly without pulling the
        full stratified stack. *index_name* maps to ``source_type`` in the
        embeddings table (e.g. "document", "code", "research", "task").
        """
        if not query or not user_id:
            return []

        try:
            query_embedding = await self.embedding_service.embed_text(query)
        except EmbeddingProviderUnavailableError as exc:
            self._set_degraded(str(exc))
            return []
        except Exception as exc:
            self._set_degraded(str(exc))
            return []

        if not query_embedding:
            return []

        return await retrieve_by_source_type(
            query_embedding=query_embedding,
            user_id=user_id,
            source_type=index_name,
            k=k,
        )

    async def get_context_bundle(
        self,
        query: str,
        user_id: str,
        conversation_id: Optional[str] = None,
        max_tokens: int = 2000,
        k: int = 10,
    ) -> Dict[str, Any]:
        """
        Get a complete context bundle for a query

        Returns a structured bundle with different types of context
        """
        k = clamp_prompt_retrieval_k(k)

        # Retrieve all context
        all_context = await self.retrieve_context(
            query=query,
            user_id=user_id,
            conversation_id=conversation_id,
            k=k,
        )

        # Build the structured bundle (pure assembly + budget enforcement)
        context_bundle = build_context_bundle(
            query=query,
            user_id=user_id,
            conversation_id=conversation_id,
            all_context=all_context,
            max_tokens=max_tokens,
            degraded_status=self.get_degraded_status(),
        )

        # Attach financial profile when available
        try:
            from ..tool_result_memory_service import get_financial_profile

            fin_profile = await get_financial_profile(user_id, retrieval_svc=self)
            if any(fin_profile.values()):
                context_bundle["financial_profile"] = fin_profile
        except Exception as e:
            logger.warning("financial_profile_attach_failed", error=str(e))

        return context_bundle


# Backward-compatible sync ContextBuilder export.
ContextBuilder = LegacyContextBuilder

# Module-level singleton — reuse across imports
retrieval_service = RetrievalService()
