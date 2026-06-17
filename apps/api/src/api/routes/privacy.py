"""
Privacy API Router for GDPR/CCPA compliance.

Implements user rights:
- Article 20: Right to data portability (export)
- Article 17: Right to erasure (deletion)
- Article 15: Right of access (list data)

Usage:
    POST /api/privacy/export - Export all user data
    DELETE /api/privacy/delete - Delete all user data
    GET /api/privacy/data-summary - Get summary of stored data
"""

import importlib.util
import logging
import os
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

# Import auth dependencies
from ..auth.router import get_current_user
from ..services.telemetry import EventType, log_conversation_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/privacy", tags=["privacy", "gdpr", "ccpa"])

_VECTOR_STORE_DEFAULT = (
    "false" if os.getenv("ENVIRONMENT", "development").lower() == "production" else "true"
)
VECTOR_STORE_AVAILABLE = (
    os.getenv("ENABLE_VECTOR_STORE", _VECTOR_STORE_DEFAULT).strip().lower()
    in {"1", "true", "yes", "on"}
    and importlib.util.find_spec("chromadb") is not None
)
_vector_store = None


def _get_vector_store():
    global _vector_store

    if not VECTOR_STORE_AVAILABLE:
        return None

    if _vector_store is None:
        from ..services.safe_vector_store import SafeVectorStore

        _vector_store = SafeVectorStore(collection_name="goblin_rag")

    return _vector_store


@router.post("/export", response_model=Dict[str, Any])
async def export_user_data(
    user_id: str = Depends(get_current_user),
    include_vectors: bool = True,
    include_conversations: bool = True,
    include_preferences: bool = True,
) -> Dict[str, Any]:
    """
    Export all user data (GDPR Article 20 - Right to Data Portability).

    Returns a comprehensive export of all data stored about the user:
    - Vector store documents (RAG data)
    - Conversation history
    - User preferences
    - Account metadata

    Args:
        user_id: Authenticated user ID
        include_vectors: Include vector store documents
        include_conversations: Include conversation history
        include_preferences: Include user preferences

    Returns:
        Dictionary with all user data

    Example:
        POST /api/privacy/export
        Authorization: Bearer <token>

        Response:
        {
            "user_id": "user_123",
            "exported_at": "2026-01-10T12:00:00Z",
            "data": {
                "vectors": [...],
                "conversations": [...],
                "preferences": {...}
            }
        }
    """
    logger.info("Data export requested by user: %s", user_id)

    export_data = {
        "user_id": user_id,
        "exported_at": datetime.utcnow().isoformat(),
        "export_version": "1.0",
        "data": {},
    }

    try:
        vector_store = _get_vector_store()

        # Export vector store documents
        if include_vectors and vector_store is not None:
            vector_export = await vector_store.export_user_data(user_id)
            if vector_export["success"]:
                export_data["data"]["vectors"] = {
                    "document_count": vector_export["document_count"],
                    "documents": vector_export["documents"],
                }
                logger.info(
                    "Exported %s vectors for user %s", vector_export["document_count"], user_id
                )
            else:
                export_data["data"]["vectors"] = {
                    "error": vector_export.get("error", "Unknown error")
                }

        # Export conversations from database
        if include_conversations:
            try:
                from ..storage.conversations import DatabaseConversationStore

                conversation_store = DatabaseConversationStore()
                conversations = await conversation_store.list_conversations(
                    user_id=user_id, limit=1000
                )
                export_data["data"]["conversations"] = {
                    "count": len(conversations),
                    "conversations": [
                        {
                            "conversation_id": conv.conversation_id,
                            "title": conv.title,
                            "created_at": conv.created_at.isoformat(),
                            "updated_at": conv.updated_at.isoformat(),
                            "messages": [
                                {
                                    "message_id": msg.message_id,
                                    "role": msg.role,
                                    "content": msg.content,
                                    "timestamp": msg.timestamp.isoformat(),
                                    "metadata": msg.metadata,
                                }
                                for msg in conv.messages
                            ],
                        }
                        for conv in conversations
                    ],
                }
                logger.info("Exported %s conversations for user %s", len(conversations), user_id)
            except Exception as conv_error:
                logger.error("Conversation export error: %s", conv_error)
                export_data["data"]["conversations"] = {
                    "error": str(conv_error),
                    "count": 0,
                }

        # Export user preferences from database
        if include_preferences:
            try:
                from ..storage.preferences_service import preferences_service

                prefs = await preferences_service.get_preferences(user_id)
                export_data["data"]["preferences"] = prefs if prefs else {}
                logger.info("Exported preferences for user %s", user_id)
            except Exception as pref_error:
                logger.error("Preferences export error: %s", pref_error)
                export_data["data"]["preferences"] = {
                    "error": str(pref_error),
                }

        # Export memory records
        try:
            from ..services.memory_core import memory_core_service

            memory_export = await memory_core_service.export_user_memory(user_id)
            if memory_export:
                export_data["data"]["memory"] = {
                    "count": len(memory_export),
                    "records": memory_export,
                }
                logger.info("Exported %s memory records for user %s", len(memory_export), user_id)
        except Exception as memory_error:
            logger.error("Memory export error: %s", memory_error)

        # Log privacy export
        total_items = export_data["data"].get("vectors", {}).get("document_count", 0)
        logger.info("Privacy export completed: %s items for user %s", total_items, user_id)

        return export_data

    except Exception as e:
        logger.error("Export failed for user %s: %s", user_id, e)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.delete("/delete", response_model=Dict[str, Any])
async def delete_user_data(
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user),
    confirm: bool = False,
) -> Dict[str, Any]:
    """
    Delete all user data (GDPR Article 17 - Right to Erasure).

    This is a DESTRUCTIVE operation that:
    - Deletes all vector store documents
    - Deletes conversation history
    - Deletes user preferences
    - Marks account for deletion

    Args:
        user_id: Authenticated user ID
        confirm: Must be True to proceed (safety check)

    Returns:
        Dictionary with deletion status

    Example:
        DELETE /api/privacy/delete?confirm=true
        Authorization: Bearer <token>

        Response:
        {
            "success": true,
            "deleted_at": "2026-01-10T12:00:00Z",
            "deleted_items": {
                "vectors": 15,
                "conversations": 42,
                "preferences": 1
            }
        }
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Deletion requires confirmation. Set confirm=true to proceed.",
        )

    logger.warning("Data deletion requested by user: %s", user_id)

    deleted_counts = {"vectors": 0, "conversations": 0, "preferences": 0, "memory": 0}

    try:
        vector_store = _get_vector_store()

        # Delete from vector store
        if vector_store is not None:
            vector_delete = await vector_store.delete_user_data(user_id)
            if vector_delete["success"]:
                deleted_counts["vectors"] = vector_delete["deleted_count"]
                logger.info("Deleted %s vectors for user %s", deleted_counts["vectors"], user_id)
            else:
                logger.error("Vector deletion failed: %s", vector_delete.get("error"))
        else:
            logger.info("Vector store not available, skipping vector deletion")

        # Delete conversations from database
        try:
            from ..storage.conversations import DatabaseConversationStore

            conversation_store = DatabaseConversationStore()
            conversations = await conversation_store.list_conversations(
                user_id=user_id, limit=10000
            )
            for conv in conversations:
                await conversation_store.delete_conversation(conv.conversation_id)
            deleted_counts["conversations"] = len(conversations)
            logger.info("Deleted %s conversations for user %s", len(conversations), user_id)
        except Exception as conv_error:
            logger.error("Conversation deletion error: %s", conv_error)

        # Delete user preferences from database
        try:
            from ..storage.preferences_service import preferences_service

            prefs_deleted = await preferences_service.delete_preferences(user_id)
            deleted_counts["preferences"] = 1 if prefs_deleted else 0
            logger.info("Deleted preferences for user %s", user_id)
        except Exception as pref_error:
            logger.error("Preferences deletion error: %s", pref_error)

        # Delete memory records from the unified memory core
        try:
            from ..services.memory_core import memory_core_service

            memory_deleted = await memory_core_service.delete_user_memory(user_id)
            deleted_counts["memory"] = memory_deleted.get("memory_records", 0)
            logger.info("Deleted memory records for user %s", user_id)
        except Exception as memory_error:
            logger.error("Memory deletion error: %s", memory_error)

        # Log privacy event
        total_deleted = sum(deleted_counts.values())
        log_conversation_event(
            event_type=EventType.DATA_DELETE,
            user_id=user_id,
            metadata={
                "action": "full_deletion",
                "item_count": total_deleted,
                "success": True,
            },
        )

        return {
            "success": True,
            "user_id": user_id,
            "deleted_at": datetime.utcnow().isoformat(),
            "deleted_items": deleted_counts,
            "message": "All user data has been deleted",
        }

    except Exception as e:
        logger.error("Deletion failed for user %s: %s", user_id, e)
        log_conversation_event(
            event_type=EventType.DATA_DELETE,
            user_id=user_id,
            metadata={"action": "full_deletion", "success": False},
        )
        raise HTTPException(status_code=500, detail=f"Deletion failed: {str(e)}")


@router.get("/data-summary", response_model=Dict[str, Any])
async def get_data_summary(user_id: str = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Get summary of stored user data (GDPR Article 15 - Right of Access).

    Returns counts and metadata about stored data without returning
    the actual data (use /export for full data).

    Args:
        user_id: Authenticated user ID

    Returns:
        Dictionary with data summary

    Example:
        GET /api/privacy/data-summary
        Authorization: Bearer <token>

        Response:
        {
            "user_id": "user_123",
            "data_summary": {
                "vectors": {"count": 15, "total_size_kb": 245},
                "conversations": {"count": 42, "oldest": "2025-12-01T..."},
                "preferences": {"count": 1}
            }
        }
    """
    logger.info("Data summary requested by user: %s", user_id)

    try:
        vector_store = _get_vector_store()

        # Get vector store summary
        vector_count = 0
        if vector_store is not None:
            vector_count = await vector_store.get_user_document_count(user_id)

        # Get conversation count from database
        try:
            from ..storage.conversations import DatabaseConversationStore

            conversation_store = DatabaseConversationStore()
            conversations = await conversation_store.list_conversations(
                user_id=user_id, limit=10000
            )
            conversation_count = len(conversations)
        except Exception as conv_error:
            logger.error("Conversation count error: %s", conv_error)
            conversation_count = 0

        # Get preferences from database
        try:
            from ..storage.preferences_service import preferences_service

            prefs = await preferences_service.get_preferences(user_id)
            has_preferences = prefs is not None
        except Exception as pref_error:
            logger.error("Preferences fetch error: %s", pref_error)
            has_preferences = False

        try:
            from ..services.memory_core import memory_core_service

            memory_records = await memory_core_service.export_user_memory(user_id)
            memory_count = len(memory_records)
        except Exception as memory_error:
            logger.error("Memory count error: %s", memory_error)
            memory_count = 0

        summary = {
            "user_id": user_id,
            "generated_at": datetime.utcnow().isoformat(),
            "data_summary": {
                "vectors": {
                    "count": vector_count,
                    "description": "Documents stored in RAG system",
                },
                "conversations": {
                    "count": conversation_count,
                    "description": "Chat conversations",
                },
                "preferences": {
                    "exists": has_preferences,
                    "description": "User settings and preferences",
                },
                "memory": {
                    "count": memory_count,
                    "description": "Typed long-term memory records",
                },
            },
            "privacy_notice": "You have the right to export or delete all your data at any time.",
        }

        return summary

    except Exception as e:
        logger.error("Summary failed for user %s: %s", user_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {str(e)}")


@router.post("/consent/rag", response_model=Dict[str, Any])
async def update_rag_consent(
    consent_given: bool, user_id: str = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Update user consent for RAG (vector store) storage.

    Users must explicitly consent before their data can be
    stored in the vector database for RAG.

    Args:
        consent_given: True to grant consent, False to revoke
        user_id: Authenticated user ID

    Returns:
        Dictionary with consent status
    """
    logger.info("RAG consent update by user %s: %s", user_id, consent_given)

    try:
        vector_store = _get_vector_store()

        # Store consent in database user_preferences table
        try:
            from ..storage.preferences_service import preferences_service

            await preferences_service.update_rag_consent(user_id, consent_given)
            logger.info("Stored RAG consent for user %s: %s", user_id, consent_given)
        except Exception as consent_error:
            logger.error("Failed to store RAG consent: %s", consent_error)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to store consent: {str(consent_error)}",
            )

        if not consent_given:
            # If consent revoked, delete existing data
            if vector_store is not None:
                delete_result = await vector_store.delete_user_data(user_id)
                logger.info("Consent revoked - deleted %s docs", delete_result["deleted_count"])
            else:
                logger.info("Vector store not available, skipping deletion on consent revoke")

            try:
                from ..services.memory_core import memory_core_service

                memory_delete = await memory_core_service.delete_user_memory(user_id)
                logger.info(
                    "Consent revoked - deleted %s memory records",
                    memory_delete.get("memory_records", 0),
                )
            except Exception as memory_error:
                logger.error("Memory deletion on consent revoke failed: %s", memory_error)

        return {
            "success": True,
            "user_id": user_id,
            "consent_given": consent_given,
            "updated_at": datetime.utcnow().isoformat(),
            "message": ("Consent updated" if consent_given else "Consent revoked and data deleted"),
        }

    except Exception as e:
        logger.error("Consent update failed for user %s: %s", user_id, e)
        raise HTTPException(status_code=500, detail=f"Consent update failed: {str(e)}")


# Export router
__all__ = ["router"]
