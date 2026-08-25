"""VectorStore Protocol — the storage contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Protocol, runtime_checkable


@dataclass(frozen=True)
class VectorSearchResult:
    id: str
    content: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class VectorStore(Protocol):
    """Protocol satisfied by any concrete vector-store implementation.

    Production uses PgVectorStore (pgvector).
    ChromaStore (HTTP) is available as an optional alternative.
    """

    async def upsert(
        self,
        doc_id: str,
        content: str,
        embedding: List[float],
        user_id: str,
        metadata: Dict[str, Any] | None = None,
    ) -> None: ...

    async def query(
        self,
        embedding: List[float],
        user_id: str,
        n_results: int = 10,
    ) -> List[VectorSearchResult]: ...

    async def delete_user_data(self, user_id: str) -> Dict[str, Any]: ...

    async def export_user_data(self, user_id: str) -> Dict[str, Any]: ...

    async def get_user_document_count(self, user_id: str) -> int: ...

    async def health(self) -> Dict[str, Any]: ...
