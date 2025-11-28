from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import re

router = APIRouter(prefix="/search", tags=["search"])

# Simple in-memory document storage for now
# In production, this would be replaced with ChromaDB or another vector database
COLLECTIONS = {}


class SearchQuery(BaseModel):
    query: str
    collection_name: str = "documents"
    n_results: int = 10


class SearchResult(BaseModel):
    id: str
    document: str
    metadata: Optional[Dict[str, Any]] = None
    score: Optional[float] = None


class SearchResponse(BaseModel):
    results: List[SearchResult]
    total_results: int


def simple_text_search(
    query: str, documents: List[Dict], n_results: int = 10
) -> List[Dict]:
    """Simple text-based search implementation"""
    query_lower = query.lower()
    scored_docs = []

    for doc in documents:
        text = doc.get("document", "").lower()
        score = 0

        # Simple scoring based on word matches
        query_words = query_lower.split()
        for word in query_words:
            if word in text:
                score += 1

        # Boost score for exact phrase matches
        if query_lower in text:
            score += 10

        if score > 0:
            scored_docs.append(
                {
                    "id": doc.get("id", f"doc_{len(scored_docs)}"),
                    "document": doc.get("document", ""),
                    "metadata": doc.get("metadata", {}),
                    "score": score,
                }
            )

    # Sort by score and return top results
    scored_docs.sort(key=lambda x: x["score"], reverse=True)
    return scored_docs[:n_results]


@router.post("/query", response_model=SearchResponse)
async def search_documents(search_query: SearchQuery):
    """Search documents using simple text search"""
    try:
        collection_name = search_query.collection_name

        # Get documents from collection
        if collection_name not in COLLECTIONS:
            COLLECTIONS[collection_name] = []

        documents = COLLECTIONS[collection_name]

        if not documents:
            return SearchResponse(results=[], total_results=0)

        # Perform search
        results = simple_text_search(
            search_query.query, documents, search_query.n_results
        )

        # Format results
        search_results = []
        for result in results:
            search_results.append(
                SearchResult(
                    id=result["id"],
                    document=result["document"],
                    metadata=result["metadata"],
                    score=result["score"],
                )
            )

        return SearchResponse(results=search_results, total_results=len(search_results))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/collections")
async def list_collections():
    """List all available collections"""
    try:
        return {"collections": list(COLLECTIONS.keys())}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to list collections: {str(e)}"
        )


@router.post("/collections/{collection_name}/add")
async def add_document(
    collection_name: str,
    document: str,
    metadata: Optional[Dict[str, Any]] = None,
    id: Optional[str] = None,
):
    """Add a document to a collection"""
    try:
        if collection_name not in COLLECTIONS:
            COLLECTIONS[collection_name] = []

        doc_id = id or f"doc_{len(COLLECTIONS[collection_name])}"

        COLLECTIONS[collection_name].append(
            {"id": doc_id, "document": document, "metadata": metadata or {}}
        )

        return {"status": "success", "document_id": doc_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add document: {str(e)}")


@router.get("/collections/{collection_name}/documents")
async def get_collection_documents(collection_name: str):
    """Get all documents in a collection"""
    try:
        if collection_name not in COLLECTIONS:
            return {"documents": []}

        return {"documents": COLLECTIONS[collection_name]}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get documents: {str(e)}"
        )
