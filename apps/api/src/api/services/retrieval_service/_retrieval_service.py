"""
Orchestrating RetrievalService class.

This is the public face of the retrieval_service package.  It coordinates
the retrieval pipeline:
  1. Embed the query
  2. Run stratified retrieval (SQL queries in ``_sql_retrieval``)
  3. Optionally trace to observability
  4. Assemble a context bundle (via ``_context_bundle``)
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy import text

from ...storage.database import get_readonly_db_context
from ..context_builder import LegacyContextBuilder
from ..embedding_service import EmbeddingProviderUnavailableError, EmbeddingService
from ._context_bundle import build_context_bundle
from ._sql_retrieval import (
    retrieve_by_source_type,
    retrieve_memory_facts_stratified,
    retrieve_messages_stratified,
    retrieve_recent_messages,
    retrieve_summaries_stratified,
)

logger = structlog.get_logger()


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

    async def retrieve_context(
        self,
        query: str,
        user_id: str,
        conversation_id: Optional[str] = None,
        k: int = 5,
        max_age_hours: int = 168,  # 7 days default
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
            results = await self._stratified_retrieval(
                query_embedding=query_embedding,
                query=query,
                user_id=user_id,
                conversation_id=conversation_id,
                k=k,
                max_age_hours=max_age_hours,
            )

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
    ) -> List[Dict[str, Any]]:
        """
        Retrieve context using memory stratification priority:
        1. Long-term memory facts (highest priority)
        2. Working memory summaries
        3. Relevant vector-retrieved messages
        4. Ephemeral recent messages
        """
        all_results = []

        # 1. Long-term memory facts (highest priority)
        memory_facts = await retrieve_memory_facts_stratified(
            query_embedding=query_embedding,
            user_id=user_id,
            k=min(k, 3),
        )
        all_results.extend(memory_facts)

        # 2. Working memory summaries
        summaries = await retrieve_summaries_stratified(
            query_embedding=query_embedding,
            user_id=user_id,
            conversation_id=conversation_id,
            k=min(k, 2),
        )
        all_results.extend(summaries)

        # 3. Document/code/research/task index items
        index_source_types = ["document", "code", "research", "task"]
        for stype in index_source_types:
            index_items = await retrieve_by_source_type(
                query_embedding=query_embedding,
                user_id=user_id,
                source_type=stype,
                k=min(k, 3),
            )
            all_results.extend(index_items)

        # 4. Relevant vector-retrieved messages
        messages = await retrieve_messages_stratified(
            query_embedding=query_embedding,
            user_id=user_id,
            conversation_id=conversation_id,
            k=min(k, 3),
        )
        all_results.extend(messages)

        # 5. Ephemeral recent messages (if we still need more)
        remaining_k = k - len(all_results)
        if remaining_k > 0:
            recent_messages = await retrieve_recent_messages(
                user_id=user_id,
                conversation_id=conversation_id,
                k=remaining_k,
            )
            all_results.extend(recent_messages)

        # Sort by score and return top k
        all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return all_results[:k]

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
                        mf.category,
                        mf.metadata,
                        mf.created_at,
                        (1 - (mf.fact_embedding <=> :query_embedding)) as similarity_score
                    FROM memory_facts mf
                    WHERE {where_clause}
                    ORDER BY similarity_score DESC
                    LIMIT :k
                """
                )

                result = await session.execute(stmt, params)
                rows = result.fetchall()

                return [
                    {
                        "id": row.id,
                        "fact_text": row.fact_text,
                        "category": row.category,
                        "metadata": row.metadata,
                        "created_at": row.created_at,
                        "score": (float(row.similarity_score) if row.similarity_score else 0.0),
                        "source_type": "memory",
                    }
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
    ) -> Dict[str, Any]:
        """
        Get a complete context bundle for a query

        Returns a structured bundle with different types of context
        """
        # Retrieve all context
        all_context = await self.retrieve_context(
            query=query,
            user_id=user_id,
            conversation_id=conversation_id,
            k=10,
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
