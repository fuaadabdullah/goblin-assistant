"""
Privacy-first vector store wrapper for Goblin Assistant.

This module provides a privacy layer on top of any VectorStore implementation
that enforces:
- PII detection and blocking before embedding
- User consent checks before storage
- TTL (time-to-live) for automatic data expiration
- User-scoped data isolation

Storage is delegated to a VectorStore (PgVectorStore by default, ChromaStore
when CHROMA_URL is set).  The local Chroma filesystem backend is no longer
used because ephemeral runtimes lose filesystem state on restart.

Usage:
    from api.services.safe_vector_store import SafeVectorStore

    store = SafeVectorStore()

    result = await store.add_document(
        doc_id="doc_123",
        content=user_input,
        embedding=embedding_vector,
        metadata={"source": "chat"},
        user_id="user_xyz",
        consent_given=True,
        ttl_hours=24,
    )
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from .sanitization import (
    hash_message_id,
    is_sensitive_content,
    sanitize_input_for_model,
)
from .vector_store import VectorStore, create_vector_store

logger = logging.getLogger(__name__)

# CHROMADB_AVAILABLE is kept as a public constant for backward compat with
# any external code that checked it before importing SafeVectorStore.
CHROMADB_AVAILABLE = False
try:
    import chromadb as _chromadb  # noqa: F401

    CHROMADB_AVAILABLE = True
except ImportError:
    pass


class SafeVectorStore:
    """Privacy wrapper around a VectorStore implementation.

    Add-time enforcement:
    - Consent must be explicitly granted
    - PII is detected and blocked (or stripped when force=True)
    - TTL metadata is attached so callers can expire documents

    Read/delete operations are delegated directly to the underlying store
    because they do not require consent re-verification.
    """

    def __init__(
        self,
        default_ttl_hours: int = 24,
        store: Optional[VectorStore] = None,
        # Legacy kwarg kept for call-site compat; ignored in the new implementation.
        collection_name: str = "goblin_rag",
        persist_directory: Optional[str] = None,
        embedding_model: str = "all-MiniLM-L6-v2",
    ) -> None:
        self.default_ttl_hours = default_ttl_hours
        self._store: VectorStore = store or create_vector_store()
        logger.info(
            "Initialized SafeVectorStore (backend: %s)",
            type(self._store).__name__,
        )

    async def add_document(
        self,
        doc_id: str,
        content: str,
        embedding: list,
        metadata: Dict[str, Any],
        user_id: str,
        consent_given: bool = False,
        ttl_hours: Optional[int] = None,
        force: bool = False,
    ) -> Dict[str, Any]:
        """Add a document with privacy enforcement.

        Args:
            doc_id: Unique document identifier
            content: Document text (will be sanitized)
            embedding: Pre-computed embedding vector
            metadata: Document metadata
            user_id: User ID for data isolation
            consent_given: Must be True for storage to proceed
            ttl_hours: Time-to-live in hours (default: 24h)
            force: Skip PII checks (use with caution)

        Returns:
            dict with ``success`` key indicating outcome
        """
        if not consent_given:
            logger.warning("Consent not given for doc %s by user %s", doc_id, user_id)
            return {
                "success": False,
                "error": "User consent required for RAG storage",
                "doc_id": doc_id,
                "suggestion": "Obtain explicit user consent before storing documents",
            }

        if not force and is_sensitive_content(content):
            logger.warning("Sensitive content detected in doc %s", doc_id)
            return {
                "success": False,
                "error": "Document contains sensitive content (PII/secret) — cannot embed",
                "doc_id": doc_id,
                "suggestion": "Remove PII/secrets before adding to RAG",
            }

        sanitized_content, pii_detected = sanitize_input_for_model(content)

        if pii_detected and not force:
            logger.error("PII detected in doc %s: %s", doc_id, pii_detected)
            return {
                "success": False,
                "error": f"PII detected: {', '.join(pii_detected)}",
                "doc_id": doc_id,
                "pii_types": pii_detected,
                "suggestion": "Remove detected PII before adding",
            }

        ttl = ttl_hours or self.default_ttl_hours
        created_at = datetime.utcnow()
        expires_at = created_at + timedelta(hours=ttl)

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
            await self._store.upsert(
                doc_id=doc_id,
                content=sanitized_content,
                embedding=embedding,
                user_id=user_id,
                metadata=safe_metadata,
            )
            logger.info("Added doc %s for user %s, expires %s", doc_id, user_id, expires_at)
            return {
                "success": True,
                "doc_id": doc_id,
                "user_id": user_id,
                "expires_at": expires_at.isoformat(),
                "sanitized": len(pii_detected) > 0,
                "pii_removed": pii_detected,
            }
        except Exception as exc:
            logger.error("Failed to add doc %s: %s", doc_id, exc)
            return {"success": False, "error": str(exc), "doc_id": doc_id}

    async def delete_user_data(self, user_id: str) -> Dict[str, Any]:
        """Delete all documents for a user (GDPR Article 17)."""
        return await self._store.delete_user_data(user_id)

    async def export_user_data(self, user_id: str) -> Dict[str, Any]:
        """Export all user documents (GDPR Article 20)."""
        return await self._store.export_user_data(user_id)

    async def get_user_document_count(self, user_id: str) -> int:
        """Count documents stored for a user."""
        return await self._store.get_user_document_count(user_id)

    async def health(self) -> Dict[str, Any]:
        """Return the underlying store's health status."""
        return await self._store.health()


__all__ = ["SafeVectorStore", "CHROMADB_AVAILABLE"]
