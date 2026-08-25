"""Vector store factory — returns the configured implementation."""

from __future__ import annotations

import os

from ._protocol import VectorStore


def create_vector_store() -> VectorStore:
    """Return the configured VectorStore implementation.

    Selection order:
    1. If CHROMA_URL is set → ChromaStore (HTTP, not filesystem).
    2. Otherwise → PgVectorStore (PostgreSQL + pgvector).

    PgVectorStore is the default because pgvector is already a hard dependency
    and does not require additional infrastructure.  ChromaStore requires a
    separately deployed Chroma HTTP server.
    """
    chroma_url = os.environ.get("CHROMA_URL") or os.environ.get("CHROMA_API_URL")
    if chroma_url:
        from ._chroma import ChromaStore

        collection = os.environ.get("CHROMA_COLLECTION", "goblin_rag")
        return ChromaStore(url=chroma_url, collection_name=collection)

    from ._pg import PgVectorStore

    return PgVectorStore()
