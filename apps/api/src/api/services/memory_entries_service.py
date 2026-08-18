"""Semantic corpus for repo docs, code, and prior agent runs."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence

import structlog
from sqlalchemy import bindparam, select, text

from ..storage.database import get_db_context, get_readonly_db_context
from ..storage.vector_models import MemoryEntryModel
from .embedding_service import EmbeddingProviderUnavailableError, EmbeddingService

logger = structlog.get_logger(__name__)

DEFAULT_CHUNK_TOKENS = 320
DEFAULT_CHUNK_OVERLAP = 40


def chunk_text(
    text_value: str,
    *,
    chunk_tokens: int = DEFAULT_CHUNK_TOKENS,
    overlap_tokens: int = DEFAULT_CHUNK_OVERLAP,
) -> List[str]:
    """Chunk text into overlapping token windows using a simple word-based splitter."""

    cleaned = " ".join((text_value or "").split())
    if not cleaned:
        return []

    words = cleaned.split(" ")
    if len(words) <= chunk_tokens:
        return [cleaned]

    overlap = max(0, min(overlap_tokens, chunk_tokens // 2))
    step = max(1, chunk_tokens - overlap)
    chunks: List[str] = []
    for start in range(0, len(words), step):
        window = words[start : start + chunk_tokens]
        if not window:
            break
        chunks.append(" ".join(window))
        if start + chunk_tokens >= len(words):
            break
    return chunks


def _chunk_hash(source_kind: str, source_id: str, chunk_index: int, chunk_text_value: str) -> str:
    payload = f"{source_kind}:{source_id}:{chunk_index}:{chunk_text_value}"
    return hashlib.sha256(payload.encode("utf-8", errors="replace")).hexdigest()


@dataclass(slots=True)
class MemoryEntrySearchFilter:
    user_id: str
    source_kinds: Optional[Sequence[str]] = None
    conversation_id: Optional[str] = None
    session_id: Optional[str] = None
    repository: Optional[str] = None
    commit_sha: Optional[str] = None
    run_id: Optional[str] = None
    limit: int = 8


class MemoryEntriesService:
    def __init__(self) -> None:
        self.embedding_service = EmbeddingService()

    async def index_text(
        self,
        *,
        user_id: str,
        source_kind: str,
        source_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        repository: Optional[str] = None,
        commit_sha: Optional[str] = None,
        run_id: Optional[str] = None,
        session_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        chunk_tokens: int = DEFAULT_CHUNK_TOKENS,
        overlap_tokens: int = DEFAULT_CHUNK_OVERLAP,
    ) -> List[str]:
        """Chunk, embed, and persist semantic memory entries."""

        metadata = dict(metadata or {})
        chunks = chunk_text(content, chunk_tokens=chunk_tokens, overlap_tokens=overlap_tokens)
        if not chunks:
            return []

        embeddings = await self.embedding_service.embed_batch(chunks)
        if len(embeddings) != len(chunks):
            raise RuntimeError("embedding batch size mismatch for memory entries")

        entry_ids: List[str] = []
        async with get_db_context() as session:
            for index, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                chunk_hash = _chunk_hash(source_kind, source_id, index, chunk)
                existing_q = await session.execute(
                    select(MemoryEntryModel).where(
                        MemoryEntryModel.user_id == user_id,
                        MemoryEntryModel.source_kind == source_kind,
                        MemoryEntryModel.source_id == source_id,
                        MemoryEntryModel.chunk_hash == chunk_hash,
                    )
                )
                existing = existing_q.scalar_one_or_none()
                if existing is not None:
                    existing.chunk_text = chunk
                    existing.chunk_embedding = embedding
                    existing.repository = repository
                    existing.commit_sha = commit_sha
                    existing.run_id = run_id
                    existing.session_id = session_id
                    existing.conversation_id = conversation_id
                    current_meta = dict(existing.metadata_ or {})
                    current_meta.update(metadata)
                    existing.metadata_ = current_meta
                    entry_ids.append(existing.id)
                    continue

                entry = MemoryEntryModel(
                    user_id=user_id,
                    source_kind=source_kind,
                    source_id=source_id,
                    chunk_index=index,
                    chunk_text=chunk,
                    chunk_embedding=embedding,
                    chunk_hash=chunk_hash,
                    repository=repository,
                    commit_sha=commit_sha,
                    run_id=run_id,
                    session_id=session_id,
                    conversation_id=conversation_id,
                    metadata_=metadata,
                )
                session.add(entry)
                await session.flush()
                entry_ids.append(entry.id)
        return entry_ids

    async def index_repo_document(
        self,
        *,
        user_id: str,
        repository: str,
        source_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        commit_sha: Optional[str] = None,
    ) -> List[str]:
        return await self.index_text(
            user_id=user_id,
            source_kind="repo_doc",
            source_id=source_id,
            content=content,
            metadata=metadata,
            repository=repository,
            commit_sha=commit_sha,
        )

    async def index_repo_code(
        self,
        *,
        user_id: str,
        repository: str,
        source_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        commit_sha: Optional[str] = None,
    ) -> List[str]:
        return await self.index_text(
            user_id=user_id,
            source_kind="repo_code",
            source_id=source_id,
            content=content,
            metadata=metadata,
            repository=repository,
            commit_sha=commit_sha,
        )

    async def index_agent_run(
        self,
        *,
        user_id: str,
        run_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> List[str]:
        return await self.index_text(
            user_id=user_id,
            source_kind="agent_run",
            source_id=run_id,
            content=content,
            metadata=metadata,
            run_id=run_id,
            session_id=session_id,
        )

    async def search(
        self,
        query: str,
        *,
        user_id: str,
        source_kinds: Optional[Sequence[str]] = None,
        conversation_id: Optional[str] = None,
        session_id: Optional[str] = None,
        repository: Optional[str] = None,
        commit_sha: Optional[str] = None,
        run_id: Optional[str] = None,
        limit: int = 8,
    ) -> List[Dict[str, Any]]:
        query = (query or "").strip()
        if not query or not user_id:
            return []

        try:
            query_embedding = await self.embedding_service.embed_text(query)
        except EmbeddingProviderUnavailableError:
            query_embedding = []
        except Exception as exc:
            logger.warning("memory_entry_query_embedding_failed", error=str(exc))
            query_embedding = []

        if query_embedding:
            return await self._vector_search(
                query_embedding=query_embedding,
                filters=MemoryEntrySearchFilter(
                    user_id=user_id,
                    source_kinds=source_kinds,
                    conversation_id=conversation_id,
                    session_id=session_id,
                    repository=repository,
                    commit_sha=commit_sha,
                    run_id=run_id,
                    limit=limit,
                ),
            )
        return await self._sql_fallback_search(
            query=query,
            filters=MemoryEntrySearchFilter(
                user_id=user_id,
                source_kinds=source_kinds,
                conversation_id=conversation_id,
                session_id=session_id,
                repository=repository,
                commit_sha=commit_sha,
                run_id=run_id,
                limit=limit,
            ),
        )

    async def _vector_search(
        self,
        *,
        query_embedding: List[float],
        filters: MemoryEntrySearchFilter,
    ) -> List[Dict[str, Any]]:
        conditions = ["me.user_id = :user_id"]
        params: Dict[str, Any] = {
            "user_id": filters.user_id,
            "query_embedding": query_embedding,
            "limit": filters.limit,
            "recent_7d_cutoff": datetime.utcnow() - timedelta(days=7),
            "recent_30d_cutoff": datetime.utcnow() - timedelta(days=30),
        }
        if filters.source_kinds:
            conditions.append("me.source_kind IN :source_kinds")
            params["source_kinds"] = list(filters.source_kinds)
        if filters.conversation_id:
            conditions.append("me.conversation_id = :conversation_id")
            params["conversation_id"] = filters.conversation_id
        if filters.session_id:
            conditions.append("me.session_id = :session_id")
            params["session_id"] = filters.session_id
        if filters.repository:
            conditions.append("me.repository = :repository")
            params["repository"] = filters.repository
        if filters.commit_sha:
            conditions.append("me.commit_sha = :commit_sha")
            params["commit_sha"] = filters.commit_sha
        if filters.run_id:
            conditions.append("me.run_id = :run_id")
            params["run_id"] = filters.run_id

        where_clause = " AND ".join(conditions)
        query_sql = text(
            f"""
            SELECT
                me.id,
                me.user_id,
                me.source_kind,
                me.source_id,
                me.chunk_index,
                me.chunk_text,
                me.repository,
                me.commit_sha,
                me.run_id,
                me.session_id,
                me.conversation_id,
                me.metadata,
                me.created_at,
                (1 - (me.chunk_embedding <=> :query_embedding))
                    + CASE
                        WHEN me.created_at > :recent_7d_cutoff THEN 0.08
                        WHEN me.created_at > :recent_30d_cutoff THEN 0.04
                        ELSE 0.0
                      END AS score
            FROM memory_entries me
            WHERE {where_clause}
            ORDER BY score DESC, me.created_at DESC
            LIMIT :limit
            """
        )
        if filters.source_kinds:
            query_sql = query_sql.bindparams(bindparam("source_kinds", expanding=True))

        try:
            async with get_readonly_db_context() as session:
                result = await session.execute(query_sql, params)
                rows = result.fetchall()
        except Exception as exc:
            logger.warning("memory_entry_vector_search_failed", error=str(exc))
            return []

        return [self._row_to_dict(row, filters.user_id) for row in rows]

    async def _sql_fallback_search(
        self,
        *,
        query: str,
        filters: MemoryEntrySearchFilter,
    ) -> List[Dict[str, Any]]:
        conditions = ["me.user_id = :user_id", "me.chunk_text ILIKE :query"]
        params: Dict[str, Any] = {
            "user_id": filters.user_id,
            "query": f"%{query[:128]}%",
            "limit": filters.limit,
            "recent_7d_cutoff": datetime.utcnow() - timedelta(days=7),
            "recent_30d_cutoff": datetime.utcnow() - timedelta(days=30),
        }
        if filters.source_kinds:
            conditions.append("me.source_kind IN :source_kinds")
            params["source_kinds"] = list(filters.source_kinds)
        if filters.conversation_id:
            conditions.append("me.conversation_id = :conversation_id")
            params["conversation_id"] = filters.conversation_id
        if filters.session_id:
            conditions.append("me.session_id = :session_id")
            params["session_id"] = filters.session_id
        if filters.repository:
            conditions.append("me.repository = :repository")
            params["repository"] = filters.repository
        if filters.commit_sha:
            conditions.append("me.commit_sha = :commit_sha")
            params["commit_sha"] = filters.commit_sha
        if filters.run_id:
            conditions.append("me.run_id = :run_id")
            params["run_id"] = filters.run_id

        where_clause = " AND ".join(conditions)
        query_sql = text(
            f"""
            SELECT
                me.id,
                me.user_id,
                me.source_kind,
                me.source_id,
                me.chunk_index,
                me.chunk_text,
                me.repository,
                me.commit_sha,
                me.run_id,
                me.session_id,
                me.conversation_id,
                me.metadata,
                me.created_at,
                0.5
                    + CASE
                        WHEN me.created_at > :recent_7d_cutoff THEN 0.08
                        WHEN me.created_at > :recent_30d_cutoff THEN 0.04
                        ELSE 0.0
                      END AS score
            FROM memory_entries me
            WHERE {where_clause}
            ORDER BY score DESC, me.created_at DESC
            LIMIT :limit
            """
        )
        if filters.source_kinds:
            query_sql = query_sql.bindparams(bindparam("source_kinds", expanding=True))

        try:
            async with get_readonly_db_context() as session:
                result = await session.execute(query_sql, params)
                rows = result.fetchall()
        except Exception as exc:
            logger.warning("memory_entry_sql_search_failed", error=str(exc))
            return []

        return [self._row_to_dict(row, filters.user_id) for row in rows]

    @staticmethod
    def _row_to_dict(row: Any, user_id: str) -> Dict[str, Any]:
        return {
            "id": row.id,
            "user_id": user_id,
            "source_kind": row.source_kind,
            "source_id": row.source_id,
            "chunk_index": int(row.chunk_index or 0),
            "content": row.chunk_text,
            "repository": row.repository,
            "commit_sha": row.commit_sha,
            "run_id": row.run_id,
            "session_id": row.session_id,
            "conversation_id": row.conversation_id,
            "metadata": dict(row.metadata or {}),
            "created_at": row.created_at.isoformat() if getattr(row, "created_at", None) else None,
            "score": float(getattr(row, "score", 0.0) or 0.0),
        }


memory_entries_service = MemoryEntriesService()
