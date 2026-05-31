"""
SQL retrieval functions for the RetrievalService.

Each function encapsulates a specific SQL query + row-mapping pattern.
All are async functions that accept explicit parameters and return
``List[Dict[str, Any]]``.
"""

from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy import text

from ...storage.database import get_db

logger = structlog.get_logger()

# Finance categories that receive retrieval score boosts
FINANCE_CATEGORIES = {
    "instrument",
    "risk_signal",
    "regulatory_constraint",
    "portfolio_action",
    "macro_event",
}
FINANCE_BOOST_FACTOR = 1.8
GENERIC_BOOST_FACTOR = 1.5
SUMMARY_BOOST_FACTOR = 1.2


async def retrieve_memory_facts_stratified(
    query_embedding: List[float],
    user_id: str,
    k: int = 3,
) -> List[Dict[str, Any]]:
    """Retrieve long-term memory facts with priority scoring.

    Finance-category facts receive a higher similarity boost
    (1.8x) than generic facts (1.5x) so that domain knowledge
    surfaces ahead of general conversation artifacts.
    """
    try:
        async with get_db() as session:
            query_sql = text(
                """
                SELECT
                    mf.id,
                    mf.fact_text as content,
                    mf.category,
                    mf.metadata,
                    mf.created_at,
                    (1 - (mf.fact_embedding <=> :query_embedding))
                        * CASE
                            WHEN mf.category IN ('instrument','risk_signal',
                                'regulatory_constraint','portfolio_action',
                                'macro_event')
                            THEN :finance_boost
                            ELSE :generic_boost
                          END
                        AS score
                FROM memory_facts mf
                WHERE mf.user_id = :user_id
                ORDER BY score DESC
                LIMIT :k
            """
            )

            result = await session.execute(
                query_sql,
                {
                    "query_embedding": query_embedding,
                    "user_id": user_id,
                    "k": k,
                    "finance_boost": FINANCE_BOOST_FACTOR,
                    "generic_boost": GENERIC_BOOST_FACTOR,
                },
            )

            rows = result.fetchall()

            return [
                {
                    "id": row.id,
                    "content": row.content,
                    "source_type": "memory",
                    "source_id": row.id,
                    "metadata": {
                        "category": row.category,
                        "source": "long_term_memory",
                        "finance_boosted": row.category in FINANCE_CATEGORIES,
                    },
                    "created_at": row.created_at,
                    "score": float(row.score) if row.score else 0.0,
                }
                for row in rows
            ]

    except Exception as e:
        logger.error(
            "error retrieving memory facts (stratified)",
            error=str(e),
            user_id=user_id,
        )
        return []


async def retrieve_summaries_stratified(
    query_embedding: List[float],
    user_id: str,
    conversation_id: Optional[str] = None,
    k: int = 2,
) -> List[Dict[str, Any]]:
    """Retrieve working memory summaries."""
    try:
        async with get_db() as session:
            where_clauses = ["cs.user_id = :user_id"]
            params = {
                "user_id": user_id,
                "query_embedding": query_embedding,
                "k": k,
                "summary_boost": SUMMARY_BOOST_FACTOR,
            }

            if conversation_id:
                where_clauses.append("cs.conversation_id = :conversation_id")
                params["conversation_id"] = conversation_id

            where_clause = " AND ".join(where_clauses)

            query_sql = text(
                f"""
                SELECT
                    cs.id,
                    cs.conversation_id,
                    cs.summary_text as content,
                    cs.created_at,
                    (1 - (cs.summary_embedding <=> :query_embedding)) * :summary_boost as score
                FROM conversation_summaries cs
                WHERE {where_clause}
                ORDER BY score DESC
                LIMIT :k
            """
            )

            result = await session.execute(query_sql, params)
            rows = result.fetchall()

            return [
                {
                    "id": row.id,
                    "content": row.content,
                    "source_type": "summary",
                    "source_id": row.conversation_id,
                    "metadata": {
                        "conversation_id": row.conversation_id,
                        "source": "working_memory",
                    },
                    "created_at": row.created_at,
                    "score": float(row.score) if row.score else 0.0,
                }
                for row in rows
            ]

    except Exception as e:
        logger.error(
            "error retrieving summaries (stratified)",
            error=str(e),
            user_id=user_id,
            conversation_id=conversation_id,
        )
        return []


async def retrieve_messages_stratified(
    query_embedding: List[float],
    user_id: str,
    conversation_id: Optional[str] = None,
    k: int = 3,
) -> List[Dict[str, Any]]:
    """Retrieve relevant messages with semantic search."""
    try:
        async with get_db() as session:
            where_clauses = ["e.user_id = :user_id", "e.source_type = 'message'"]
            params = {
                "user_id": user_id,
                "query_embedding": query_embedding,
                "k": k,
            }

            if conversation_id:
                where_clauses.append("e.conversation_id = :conversation_id")
                params["conversation_id"] = conversation_id

            where_clause = " AND ".join(where_clauses)

            query_sql = text(
                f"""
                SELECT
                    e.id,
                    e.content,
                    e.conversation_id,
                    e.metadata,
                    e.created_at,
                    (
                        0.8 * (1 - (e.embedding <=> :query_embedding)) +
                        0.2 * EXP(-0.001 * EXTRACT(EPOCH FROM (NOW() - e.created_at)))
                    ) as score
                FROM embeddings e
                WHERE {where_clause}
                ORDER BY score DESC
                LIMIT :k
            """
            )

            result = await session.execute(query_sql, params)
            rows = result.fetchall()

            return [
                {
                    "id": row.id,
                    "content": row.content,
                    "source_type": "message",
                    "source_id": row.conversation_id,
                    "metadata": row.metadata,
                    "created_at": row.created_at,
                    "score": float(row.score) if row.score else 0.0,
                }
                for row in rows
            ]

    except Exception as e:
        logger.error(
            "error retrieving messages (stratified)",
            error=str(e),
            user_id=user_id,
            conversation_id=conversation_id,
        )
        return []


async def retrieve_recent_messages(
    user_id: str,
    conversation_id: Optional[str] = None,
    k: int = 2,
) -> List[Dict[str, Any]]:
    """Retrieve recent ephemeral messages."""
    try:
        async with get_db() as session:
            where_clauses = ["m.user_id = :user_id"]
            params = {"user_id": user_id, "k": k}

            if conversation_id:
                where_clauses.append("m.conversation_id = :conversation_id")
                params["conversation_id"] = conversation_id

            where_clause = " AND ".join(where_clauses)

            query_sql = text(
                f"""
                SELECT
                    m.id,
                    m.content,
                    m.conversation_id,
                    m.role,
                    m.created_at
                FROM messages m
                WHERE {where_clause}
                ORDER BY m.created_at DESC
                LIMIT :k
            """
            )

            result = await session.execute(query_sql, params)
            rows = result.fetchall()

            return [
                {
                    "id": row.id,
                    "content": row.content,
                    "source_type": "ephemeral",
                    "source_id": row.conversation_id,
                    "metadata": {"role": row.role, "source": "ephemeral_memory"},
                    "created_at": row.created_at,
                    "score": 0.1,
                }
                for row in rows
            ]

    except Exception as e:
        logger.error(
            "error retrieving recent messages",
            error=str(e),
            user_id=user_id,
            conversation_id=conversation_id,
        )
        return []