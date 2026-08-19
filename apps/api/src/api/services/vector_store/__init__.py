"""Vector store abstraction for Goblin Assistant.

Production uses PgVectorStore (PostgreSQL + pgvector).
ChromaStore (HTTP) is an optional alternative when CHROMA_URL is set.

Usage:
    from api.services.vector_store import create_vector_store

    store = create_vector_store()          # PgVectorStore by default
    result = await store.export_user_data(user_id)
"""

from ._chroma import ChromaStore
from ._factory import create_vector_store
from ._pg import PgVectorStore
from ._protocol import VectorSearchResult, VectorStore

__all__ = [
    "VectorStore",
    "VectorSearchResult",
    "PgVectorStore",
    "ChromaStore",
    "create_vector_store",
]
