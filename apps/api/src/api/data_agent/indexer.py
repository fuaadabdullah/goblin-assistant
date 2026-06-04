"""Document indexer for the ADK data agent."""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger()


class DocumentIndexer:
    """Indexes documents into named collections for agent grounding.

    Delegates to embedding_worker so every document lands in pgvector and is
    immediately visible to search_router endpoints — no separate sync step is
    needed. The old in-memory _collections + sync_with_search_collections
    pattern was removed when search_router migrated to pgvector.
    """

    async def add_document(
        self,
        content: str,
        collection_name: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        document_id: Optional[str] = None,
    ) -> str:
        from api.services.embedding_service import embedding_worker  # noqa: PLC0415

        doc_id = document_id or self._generate_id(content)
        await embedding_worker.queue_index_item(
            user_id=user_id,
            source_type=collection_name,
            source_id=doc_id,
            content=content,
            metadata=metadata,
        )
        logger.debug(
            "agent_document_indexed",
            doc_id=doc_id,
            collection=collection_name,
            user_id=user_id,
        )
        return doc_id

    async def add_documents(
        self,
        documents: List[Dict[str, Any]],
        collection_name: str,
        user_id: str,
    ) -> List[str]:
        return [
            await self.add_document(
                content=doc.get("content", doc.get("document", "")),
                collection_name=collection_name,
                user_id=user_id,
                metadata=doc.get("metadata"),
                document_id=doc.get("id"),
            )
            for doc in documents
        ]

    @staticmethod
    def _generate_id(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


indexer = DocumentIndexer()
