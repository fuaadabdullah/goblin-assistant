"""
Privacy-first vector store wrapper for Goblin Assistant.

This module provides a secure wrapper around Chroma DB that enforces:
- PII detection and blocking before embedding
- User consent checks before storage
- TTL (time-to-live) for automatic data expiration
- User-scoped data isolation (RLS at application level)

Usage:
    from api.services.safe_vector_store import SafeVectorStore

    store = SafeVectorStore(collection_name="goblin_rag")

    # Add document with consent check
    result = await store.add_document(
        doc_id="doc_123",
        content=user_input,
        metadata={"source": "chat"},
        user_id="user_xyz",
        consent_given=True,  # Must be True
        ttl_hours=24
    )
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging
import chromadb
from chromadb.config import Settings

# Optional: embedding functions (requires sentence-transformers)
try:
    from chromadb.utils import embedding_functions

    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    embedding_functions = None

from .sanitization import (
    sanitize_input_for_model,
    is_sensitive_content,
    hash_message_id,
)

logger = logging.getLogger(__name__)


class SafeVectorStore:
    """
    Chroma DB wrapper with privacy-first approach.

    Features:
    - Automatic PII detection and blocking
    - User consent enforcement
    - TTL-based expiration
    - Per-user data isolation
    - Audit logging
    """

    def __init__(
        self,
        collection_name: str = "goblin_rag",
        persist_directory: Optional[str] = None,
        default_ttl_hours: int = 24,
        embedding_model: str = "all-MiniLM-L6-v2",
    ):
        """
        Initialize SafeVectorStore.

        Args:
            collection_name: Name of the Chroma collection
            persist_directory: Directory for persistent storage (None = in-memory)
            default_ttl_hours: Default TTL in hours
            embedding_model: Sentence transformer model name
        """
        self.collection_name = collection_name
        self.default_ttl_hours = default_ttl_hours

        # Initialize Chroma client
        if persist_directory:
            self.client = chromadb.PersistentClient(
                path=persist_directory, settings=Settings(anonymized_telemetry=False)
            )
        else:
            self.client = chromadb.Client(settings=Settings(anonymized_telemetry=False))
        # Setup embedding function
        if EMBEDDINGS_AVAILABLE and embedding_functions is not None:
            try:
                self.embedding_fn = (
                    embedding_functions.SentenceTransformerEmbeddingFunction(
                        model_name=embedding_model
                    )
                )
            except (ValueError, ImportError) as e:
                # sentence-transformers not available (requires PyTorch)
                logger.warning(
                    f"sentence-transformers not available ({e}), using default embeddings"
                )
                self.embedding_fn = None
        else:
            # Fallback: use default embeddings
            logger.warning(
                "sentence-transformers not available, using default embeddings"
            )
            self.embedding_fn = None

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )

        logger.info(f"Initialized SafeVectorStore: {collection_name}")

    async def add_document(
        self,
        doc_id: str,
        content: str,
        metadata: Dict[str, Any],
        user_id: str,
        consent_given: bool = False,
        ttl_hours: Optional[int] = None,
        force: bool = False,
    ) -> Dict[str, Any]:
        """
        Add document with sanitization, consent check, and TTL.

        Args:
            doc_id: Unique document identifier
            content: Document content (will be sanitized)
            metadata: Document metadata
            user_id: User ID for RLS
            consent_given: User consent for RAG storage (required)
            ttl_hours: Time-to-live in hours (default: 24h)
            force: Skip PII checks (use with caution!)

        Returns:
            Dictionary with success status and details

        Example:
            >>> result = await store.add_document(
            ...     doc_id="doc_123",
            ...     content="Technical documentation...",
            ...     metadata={"source": "upload"},
            ...     user_id="user_xyz",
            ...     consent_given=True
            ... )
            >>> print(result["success"])
            True
        """
        # Check consent
        if not consent_given:
            logger.warning(f"Consent not given for doc {doc_id} by user {user_id}")
            return {
                "success": False,
                "error": "User consent required for RAG storage",
                "doc_id": doc_id,
                "suggestion": "Obtain explicit user consent before storing documents",
            }

        # Check for sensitive content (unless forced)
        if not force and is_sensitive_content(content):
            logger.warning(f"Sensitive content detected in doc {doc_id}")
            return {
                "success": False,
                "error": "Document contains sensitive content - cannot embed",
                "doc_id": doc_id,
                "suggestion": "Remove PII/secrets before adding to RAG",
            }

        # Sanitize content
        sanitized_content, pii_detected = sanitize_input_for_model(content)

        if pii_detected and not force:
            logger.error(f"PII detected in doc {doc_id}: {pii_detected}")
            return {
                "success": False,
                "error": f"PII detected: {', '.join(pii_detected)}",
                "doc_id": doc_id,
                "pii_types": pii_detected,
                "suggestion": "Remove detected PII before adding",
            }

        # Calculate expiry
        ttl = ttl_hours or self.default_ttl_hours
        created_at = datetime.utcnow()
        expires_at = created_at + timedelta(hours=ttl)

        # Add safety metadata
        safe_metadata = {
            **metadata,
            "user_id": user_id,
            "doc_id": doc_id,
            "expires_at": expires_at.isoformat(),
            "is_sensitive": False,
            "sanitized": len(pii_detected) > 0 or force,
            "created_at": created_at.isoformat(),
            "consent_given": consent_given,
            "content_hash": hash_message_id(content),
        }

        try:
            # Store in Chroma
            self.collection.add(
                documents=[sanitized_content], metadatas=[safe_metadata], ids=[doc_id]
            )

            logger.info(f"Added doc {doc_id} for user {user_id}, expires {expires_at}")

            return {
                "success": True,
                "doc_id": doc_id,
                "user_id": user_id,
                "expires_at": expires_at.isoformat(),
                "sanitized": len(pii_detected) > 0,
                "pii_removed": pii_detected,
            }

        except Exception as e:
            logger.error(f"Failed to add doc {doc_id}: {e}")
            return {"success": False, "error": str(e), "doc_id": doc_id}

    async def query_documents(
        self,
        query_text: str,
        user_id: str,
        n_results: int = 5,
        include_expired: bool = False,
    ) -> Dict[str, Any]:
        """
        Query documents for a specific user (RLS).

        Args:
            query_text: Query text
            user_id: User ID for filtering
            n_results: Number of results to return
            include_expired: Include expired documents

        Returns:
            Dictionary with query results
        """
        # Sanitize query
        sanitized_query, _ = sanitize_input_for_model(query_text)

        # Build where clause for user isolation
        where_clause = {"user_id": user_id}

        if not include_expired:
            # Filter out expired documents
            now = datetime.utcnow().isoformat()
            # Note: Chroma doesn't support date comparisons in where clause
            # We'll filter after retrieval

        try:
            results = self.collection.query(
                query_texts=[sanitized_query],
                n_results=n_results * 2,  # Get extra to filter expired
                where=where_clause,
                include=["documents", "metadatas", "distances"],
            )

            # Filter expired documents
            if not include_expired:
                now = datetime.utcnow()
                filtered_docs = []
                filtered_metas = []
                filtered_distances = []

                for doc, meta, dist in zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0],
                ):
                    expires_at = datetime.fromisoformat(meta["expires_at"])
                    if expires_at > now:
                        filtered_docs.append(doc)
                        filtered_metas.append(meta)
                        filtered_distances.append(dist)

                        if len(filtered_docs) >= n_results:
                            break

                results = {
                    "documents": [filtered_docs],
                    "metadatas": [filtered_metas],
                    "distances": [filtered_distances],
                }

            return {
                "success": True,
                "results": results,
                "count": len(results["documents"][0]) if results["documents"] else 0,
            }

        except Exception as e:
            logger.error(f"Query failed for user {user_id}: {e}")
            return {"success": False, "error": str(e), "count": 0}

    async def delete_user_data(self, user_id: str) -> Dict[str, Any]:
        """
        Delete all documents for a user (GDPR Article 17).

        Args:
            user_id: User ID

        Returns:
            Dictionary with deletion status
        """
        try:
            # Get all user documents
            results = self.collection.get(
                where={"user_id": user_id}, include=["metadatas"]
            )

            doc_ids = results["ids"]

            if doc_ids:
                self.collection.delete(ids=doc_ids)
                logger.info(f"Deleted {len(doc_ids)} documents for user {user_id}")

            return {
                "success": True,
                "deleted_count": len(doc_ids),
                "user_id": user_id,
                "deleted_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to delete user data for {user_id}: {e}")
            return {"success": False, "error": str(e), "user_id": user_id}

    async def cleanup_expired(self) -> Dict[str, Any]:
        """
        Remove documents past their TTL.

        Returns:
            Dictionary with cleanup statistics
        """
        try:
            all_docs = self.collection.get(include=["metadatas"])
            now = datetime.utcnow()

            expired_ids = []
            for doc_id, meta in zip(all_docs["ids"], all_docs["metadatas"]):
                try:
                    expires_at = datetime.fromisoformat(meta.get("expires_at"))
                    if expires_at < now:
                        expired_ids.append(doc_id)
                except (ValueError, TypeError):
                    # Invalid or missing expires_at - skip
                    logger.warning(f"Doc {doc_id} has invalid expires_at")
                    continue

            if expired_ids:
                self.collection.delete(ids=expired_ids)
                logger.info(f"Cleaned up {len(expired_ids)} expired documents")

            return {
                "success": True,
                "deleted_count": len(expired_ids),
                "cleaned_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return {"success": False, "error": str(e), "deleted_count": 0}

    async def get_user_document_count(self, user_id: str) -> int:
        """Get count of documents for a user."""
        try:
            results = self.collection.get(where={"user_id": user_id}, include=[])
            return len(results["ids"])
        except Exception as e:
            logger.error(f"Failed to count documents for {user_id}: {e}")
            return 0

    async def export_user_data(self, user_id: str) -> Dict[str, Any]:
        """
        Export all user documents (GDPR Article 20).

        Args:
            user_id: User ID

        Returns:
            Dictionary with exported data
        """
        try:
            results = self.collection.get(
                where={"user_id": user_id}, include=["documents", "metadatas"]
            )

            documents = []
            for doc_id, content, meta in zip(
                results["ids"], results["documents"], results["metadatas"]
            ):
                documents.append(
                    {
                        "doc_id": doc_id,
                        "content": content,
                        "metadata": meta,
                    }
                )

            return {
                "success": True,
                "user_id": user_id,
                "document_count": len(documents),
                "documents": documents,
                "exported_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Export failed for user {user_id}: {e}")
            return {"success": False, "error": str(e), "user_id": user_id}


# Export public API
__all__ = ["SafeVectorStore"]
