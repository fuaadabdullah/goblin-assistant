"""PgVectorStore — canonical vector store backed by PostgreSQL + pgvector."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from ...storage.database import get_db_context, get_readonly_db_context
from ._protocol import VectorSearchResult

logger = logging.getLogger(__name__)


class PgVectorStore:
    """Vector store that targets the `embeddings` table via pgvector.

    This is the canonical production backend.  It never touches the local
    filesystem, which makes it safe on ephemeral runtimes (Render Free, Fly.io).
    """

    async def upsert(
        self,
        doc_id: str,
        content: str,
        embedding: List[float],
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        async with get_db_context() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO embeddings
                        (id, user_id, source_type, source_id, embedding, content, metadata, created_at)
                    VALUES
                        (:id, :user_id, 'rag', :id, :embedding, :content, :metadata, NOW())
                    ON CONFLICT (id) DO UPDATE SET
                        content   = EXCLUDED.content,
                        embedding = EXCLUDED.embedding,
                        metadata  = EXCLUDED.metadata
                    """
                ),
                {
                    "id": doc_id,
                    "user_id": user_id,
                    "embedding": json.dumps(embedding),
                    "content": content,
                    "metadata": json.dumps(metadata or {}),
                },
            )
            await session.commit()

    async def query(
        self,
        embedding: List[float],
        user_id: str,
        n_results: int = 10,
    ) -> List[VectorSearchResult]:
        try:
            async with get_readonly_db_context() as session:
                result = await session.execute(
                    text(
                        """
                        SELECT id, content, metadata,
                               (1 - (embedding <=> :embedding)) AS score
                        FROM embeddings
                        WHERE user_id = :user_id
                        ORDER BY score DESC
                        LIMIT :n
                        """
                    ),
                    {
                        "embedding": json.dumps(embedding),
                        "user_id": user_id,
                        "n": n_results,
                    },
                )
                rows = result.fetchall()
                return [
                    VectorSearchResult(
                        id=row.id,
                        content=row.content,
                        score=float(row.score) if row.score is not None else 0.0,
                        metadata=dict(row.metadata or {}),
                    )
                    for row in rows
                ]
        except Exception as exc:
            logger.error("pgvector query failed: %s", exc)
            return []

    async def delete_user_data(self, user_id: str) -> Dict[str, Any]:
        try:
            async with get_db_context() as session:
                result = await session.execute(
                    text("DELETE FROM embeddings WHERE user_id = :user_id"),
                    {"user_id": user_id},
                )
                await session.commit()
                deleted = result.rowcount or 0
            logger.info("Deleted %d embeddings for user %s", deleted, user_id)
            return {
                "success": True,
                "deleted_count": deleted,
                "user_id": user_id,
                "deleted_at": datetime.utcnow().isoformat(),
            }
        except Exception as exc:
            logger.error("Failed to delete embeddings for user %s: %s", user_id, exc)
            return {"success": False, "error": str(exc), "user_id": user_id}

    async def export_user_data(self, user_id: str) -> Dict[str, Any]:
        try:
            async with get_readonly_db_context() as session:
                result = await session.execute(
                    text(
                        """
                        SELECT id, content, source_type, source_id, metadata, created_at
                        FROM embeddings
                        WHERE user_id = :user_id
                        ORDER BY created_at DESC
                        """
                    ),
                    {"user_id": user_id},
                )
                rows = result.fetchall()

            documents = [
                {
                    "doc_id": row.id,
                    "content": row.content,
                    "source_type": row.source_type,
                    "source_id": row.source_id,
                    "metadata": dict(row.metadata or {}),
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                }
                for row in rows
            ]
            return {
                "success": True,
                "user_id": user_id,
                "document_count": len(documents),
                "documents": documents,
                "exported_at": datetime.utcnow().isoformat(),
            }
        except Exception as exc:
            logger.error("Failed to export embeddings for user %s: %s", user_id, exc)
            return {"success": False, "error": str(exc), "user_id": user_id}

    async def get_user_document_count(self, user_id: str) -> int:
        try:
            async with get_readonly_db_context() as session:
                result = await session.execute(
                    text("SELECT COUNT(*) FROM embeddings WHERE user_id = :user_id"),
                    {"user_id": user_id},
                )
                return result.scalar() or 0
        except Exception as exc:
            logger.error("Failed to count embeddings for user %s: %s", user_id, exc)
            return 0

    async def health(self) -> Dict[str, Any]:
        try:
            async with get_readonly_db_context() as session:
                result = await session.execute(text("SELECT COUNT(*) FROM embeddings"))
                count = result.scalar() or 0
            return {
                "status": "healthy",
                "backend": "pgvector",
                "embedding_count": count,
            }
        except Exception as exc:
            return {
                "status": "degraded",
                "backend": "pgvector",
                "error": str(exc),
            }
