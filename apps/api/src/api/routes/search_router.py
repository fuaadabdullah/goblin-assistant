"""Semantic search router — pgvector-backed.

All six indexes (memory, document, code, research, task, conversation/message)
live in the ``embeddings`` table keyed by ``source_type``.  Every endpoint
requires authentication; user_id is taken from the JWT so no cross-user leakage
is possible.
"""

import uuid
from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.core.contracts import SuccessEnvelope
from api.core.errors import DomainError
from api.services.search_collection_service import (
    get_readonly_search_db,
    list_collection_documents,
    list_collection_names,
)

from ..auth.router import User as AuthenticatedUser
from ..auth.router import get_current_user
from ..services.embedding_service import EmbeddingProviderUnavailableError
from ..services.embedding_worker import embedding_worker
from ..services.retrieval_service import retrieve_by_source_type

# Compatibility seam for older tests and call sites that still patch `get_db`.
get_db = get_readonly_search_db

logger = structlog.get_logger()

router = APIRouter(prefix="/search", tags=["search"])

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

_ALL_SOURCE_TYPES = ["memory", "document", "code", "research", "task", "message"]


class SearchQuery(BaseModel):
    query: str
    source_types: Optional[List[str]] = None  # None → search all types
    k: int = 10
    # Legacy field kept for backward compat; maps to source_types=[collection_name]
    collection_name: Optional[str] = None
    n_results: Optional[int] = None  # legacy alias for k


class IndexRequest(BaseModel):
    content: str
    source_type: str = "document"
    source_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SearchResult(BaseModel):
    id: str
    document: str
    source_type: str
    source_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    score: Optional[float] = None


class SearchResponse(BaseModel):
    results: List[SearchResult]
    total_results: int


class CollectionsResponse(BaseModel):
    collections: List[str]


class IndexResponse(BaseModel):
    status: str
    source_id: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/query", response_model=SuccessEnvelope[SearchResponse])
async def search_query(
    search_query: SearchQuery,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Semantic search across one or more indexes using pgvector cosine similarity."""
    try:
        from ..services.embedding_service import EmbeddingService  # noqa: PLC0415

        embedding_svc = EmbeddingService()

        try:
            query_embedding = await embedding_svc.embed_text(search_query.query)
        except EmbeddingProviderUnavailableError as exc:
            raise DomainError(
                code="EMBEDDING_UNAVAILABLE",
                message="Embedding provider unavailable; semantic search degraded.",
                status_code=503,
                details={"reason": str(exc)},
            ) from exc

        if not query_embedding:
            return SuccessEnvelope(data=SearchResponse(results=[], total_results=0))

        # Resolve which source_types to query
        k = search_query.n_results or search_query.k
        if search_query.collection_name and not search_query.source_types:
            # Legacy callers passing collection_name
            source_types = [search_query.collection_name]
        else:
            source_types = search_query.source_types or _ALL_SOURCE_TYPES

        # Retrieve from each requested index and merge
        all_results: List[Dict[str, Any]] = []
        for stype in source_types:
            items = await retrieve_by_source_type(
                query_embedding=query_embedding,
                user_id=current_user.id,
                source_type=stype,
                k=k,
            )
            all_results.extend(items)

        # Re-rank merged results and take top-k
        all_results.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        top_results = all_results[:k]

        results = [
            SearchResult(
                id=item["id"],
                document=item["content"],
                source_type=item["source_type"],
                source_id=item.get("source_id"),
                metadata=item.get("metadata"),
                score=item.get("score"),
            )
            for item in top_results
        ]

        return SuccessEnvelope(data=SearchResponse(results=results, total_results=len(results)))

    except DomainError:
        raise
    except Exception as exc:
        logger.error("search_query_failed", error=str(exc), user_id=current_user.id)
        raise DomainError(
            code="SEARCH_QUERY_FAILED",
            message="Search failed",
            status_code=500,
            details={"reason": str(exc)},
        ) from exc


@router.post("/index", response_model=SuccessEnvelope[IndexResponse])
async def index_content(
    request: IndexRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Index any content into the named source_type for later semantic retrieval.

    Fire-and-forget: returns immediately; embedding happens in the background.
    """
    try:
        source_id = request.source_id or str(uuid.uuid4())

        if request.source_type == "memory":
            from ..services.memory_core import memory_core_service  # noqa: PLC0415

            metadata = request.metadata or {}
            await memory_core_service.ingest_memory_fact(
                user_id=current_user.id,
                fact_text=request.content,
                category=metadata.get("category") or metadata.get("memory_type"),
                metadata=metadata,
                source_kind="search_index",
                source_id=source_id,
                explicit_kind=metadata.get("memory_type") or metadata.get("category"),
                confidence=float(metadata.get("confidence", 0.8)),
            )
            return SuccessEnvelope(data=IndexResponse(status="stored", source_id=source_id))

        await embedding_worker.queue_index_item(
            user_id=current_user.id,
            source_type=request.source_type,
            source_id=source_id,
            content=request.content,
            metadata=request.metadata,
        )

        return SuccessEnvelope(data=IndexResponse(status="queued", source_id=source_id))

    except Exception as exc:
        logger.error(
            "index_content_failed",
            error=str(exc),
            user_id=current_user.id,
            source_type=request.source_type,
        )
        raise DomainError(
            code="INDEX_FAILED",
            message="Failed to queue content for indexing",
            status_code=500,
            details={"reason": str(exc)},
        ) from exc


@router.get("/collections", response_model=SuccessEnvelope[CollectionsResponse])
async def list_collections(
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """List all source_types (indexes) that have content for the current user."""
    try:
        source_types = await list_collection_names(
            current_user.id,
            db_context_factory=get_db,
        )
        return SuccessEnvelope(data=CollectionsResponse(collections=source_types))

    except Exception as exc:
        raise DomainError(
            code="SEARCH_COLLECTIONS_LIST_FAILED",
            message="Failed to list collections",
            status_code=500,
            details={"reason": str(exc)},
        ) from exc


@router.post(
    "/collections/{collection_name}/add",
    response_model=SuccessEnvelope[IndexResponse],
)
async def add_document_compat(
    collection_name: str,
    document: str,
    metadata: Optional[Dict[str, Any]] = None,
    id: Optional[str] = None,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Backward-compatible shim — maps collection_name to source_type."""
    source_id = id or str(uuid.uuid4())
    await embedding_worker.queue_index_item(
        user_id=current_user.id,
        source_type=collection_name,
        source_id=source_id,
        content=document,
        metadata=metadata,
    )
    return SuccessEnvelope(data=IndexResponse(status="queued", source_id=source_id))


@router.get(
    "/collections/{collection_name}/documents",
    response_model=SuccessEnvelope[SearchResponse],
)
async def get_collection_documents(
    collection_name: str,
    limit: int = 50,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """List the most recently indexed items in a collection (non-semantic, recency order)."""
    try:
        results = [
            SearchResult(
                id=item["id"],
                document=item["content"],
                source_type=item["source_type"],
                source_id=item.get("source_id"),
                metadata=item.get("metadata"),
                score=item.get("score"),
            )
            for item in await list_collection_documents(
                user_id=current_user.id,
                source_type=collection_name,
                limit=limit,
                db_context_factory=get_db,
            )
        ]
        return SuccessEnvelope(data=SearchResponse(results=results, total_results=len(results)))

    except Exception as exc:
        raise DomainError(
            code="SEARCH_COLLECTION_DOCUMENTS_FAILED",
            message="Failed to get documents",
            status_code=500,
            details={"reason": str(exc)},
        ) from exc
