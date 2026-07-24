"""Route-safe semantic search collection persistence helpers."""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from typing import Any, Callable, Dict, List

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.storage.database import get_readonly_db_context

ReadonlySessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]


def get_readonly_search_db() -> AbstractAsyncContextManager[AsyncSession]:
    return get_readonly_db_context()


async def list_collection_names(
    user_id: str,
    *,
    db_context_factory: ReadonlySessionFactory = get_readonly_search_db,
) -> List[str]:
    async with db_context_factory() as session:
        result = await session.execute(
            text(
                """
                SELECT DISTINCT source_type
                FROM embeddings
                WHERE user_id = :user_id
                ORDER BY source_type
                """
            ),
            {"user_id": user_id},
        )
        rows = result.fetchall()
    return [row.source_type for row in rows]


async def list_collection_documents(
    *,
    user_id: str,
    source_type: str,
    limit: int,
    db_context_factory: ReadonlySessionFactory = get_readonly_search_db,
) -> List[Dict[str, Any]]:
    async with db_context_factory() as session:
        result = await session.execute(
            text(
                """
                SELECT id, content, source_type, source_id, metadata
                FROM embeddings
                WHERE user_id = :user_id AND source_type = :source_type
                ORDER BY created_at DESC
                LIMIT :limit
                """
            ),
            {
                "user_id": user_id,
                "source_type": source_type,
                "limit": limit,
            },
        )
        rows = result.fetchall()

    return [
        {
            "id": row.id,
            "content": row.content,
            "source_type": row.source_type,
            "source_id": row.source_id,
            "metadata": row.metadata,
            "score": None,
        }
        for row in rows
    ]
