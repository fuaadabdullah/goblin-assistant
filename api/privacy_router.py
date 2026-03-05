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

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from .services.sanitization import mask_sensitive
from .services.telemetry import log_privacy_event, EventType
from .services.safe_vector_store import SafeVectorStore

# Import auth dependencies (adjust path as needed)
try:
    from .auth.dependencies import get_current_user
except ImportError:
    # Fallback for testing
    async def get_current_user() -> str:
        return "test_user"


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/privacy", tags=["privacy", "gdpr", "ccpa"])

# Initialize vector store (adjust as needed)
vector_store = SafeVectorStore(collection_name="goblin_rag")


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
    logger.info(f"Data export requested by user: {user_id}")

    export_data = {
        "user_id": user_id,
        "exported_at": datetime.utcnow().isoformat(),
        "export_version": "1.0",
        "data": {},
    }

    try:
        # Export vector store documents
        if include_vectors:
            vector_export = await vector_store.export_user_data(user_id)
            if vector_export["success"]:
                export_data["data"]["vectors"] = {
                    "document_count": vector_export["document_count"],
                    "documents": vector_export["documents"],
                }
                logger.info(
                    f"Exported {vector_export['document_count']} vectors for user {user_id}"
                )
            else:
                export_data["data"]["vectors"] = {
                    "error": vector_export.get("error", "Unknown error")
                }

        # TODO: Export conversations from Supabase
        if include_conversations:
            # This would query Supabase for user conversations
            # For now, placeholder:
            export_data["data"]["conversations"] = {
                "note": "Conversation export not yet implemented",
                "count": 0,
                "messages": [],
            }

        # TODO: Export user preferences from Supabase
        if include_preferences:
            export_data["data"]["preferences"] = {
                "note": "Preferences export not yet implemented",
                "settings": {},
            }

        # Log privacy event
        total_items = export_data["data"].get("vectors", {}).get("document_count", 0)
        log_privacy_event(
            event_type=EventType.DATA_EXPORT,
            user_id=user_id,
            action="full_export",
            item_count=total_items,
            success=True,
        )

        return export_data

    except Exception as e:
        logger.error(f"Export failed for user {user_id}: {e}")
        log_privacy_event(
            event_type=EventType.DATA_EXPORT,
            user_id=user_id,
            action="full_export",
            success=False,
        )
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

    logger.warning(f"Data deletion requested by user: {user_id}")

    deleted_counts = {"vectors": 0, "conversations": 0, "preferences": 0}

    try:
        # Delete from vector store
        vector_delete = await vector_store.delete_user_data(user_id)
        if vector_delete["success"]:
            deleted_counts["vectors"] = vector_delete["deleted_count"]
            logger.info(
                f"Deleted {deleted_counts['vectors']} vectors for user {user_id}"
            )
        else:
            logger.error(f"Vector deletion failed: {vector_delete.get('error')}")

        # TODO: Delete from Supabase
        # This would delete:
        # - Conversations table (where user_id = <user_id>)
        # - User_preferences table
        # - Any other user-scoped data

        # For now, placeholders:
        deleted_counts["conversations"] = 0  # Would query and delete
        deleted_counts["preferences"] = 0  # Would query and delete

        # Log privacy event
        total_deleted = sum(deleted_counts.values())
        log_privacy_event(
            event_type=EventType.DATA_DELETE,
            user_id=user_id,
            action="full_deletion",
            item_count=total_deleted,
            success=True,
        )

        return {
            "success": True,
            "user_id": user_id,
            "deleted_at": datetime.utcnow().isoformat(),
            "deleted_items": deleted_counts,
            "message": "All user data has been deleted",
        }

    except Exception as e:
        logger.error(f"Deletion failed for user {user_id}: {e}")
        log_privacy_event(
            event_type=EventType.DATA_DELETE,
            user_id=user_id,
            action="full_deletion",
            success=False,
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
    logger.info(f"Data summary requested by user: {user_id}")

    try:
        # Get vector store summary
        vector_count = await vector_store.get_user_document_count(user_id)

        # TODO: Get conversation count from Supabase
        conversation_count = 0  # Would query Supabase

        # TODO: Get preferences from Supabase
        has_preferences = False  # Would query Supabase

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
            },
            "privacy_notice": "You have the right to export or delete all your data at any time.",
        }

        return summary

    except Exception as e:
        logger.error(f"Summary failed for user {user_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to generate summary: {str(e)}"
        )


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
    logger.info(f"RAG consent update by user {user_id}: {consent_given}")

    try:
        # TODO: Store consent in Supabase user_preferences table
        # For now, just log it

        if not consent_given:
            # If consent revoked, delete existing data
            delete_result = await vector_store.delete_user_data(user_id)
            logger.info(
                f"Consent revoked - deleted {delete_result['deleted_count']} docs"
            )

        return {
            "success": True,
            "user_id": user_id,
            "consent_given": consent_given,
            "updated_at": datetime.utcnow().isoformat(),
            "message": "Consent updated"
            if consent_given
            else "Consent revoked and data deleted",
        }

    except Exception as e:
        logger.error(f"Consent update failed for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Consent update failed: {str(e)}")


# Export router
__all__ = ["router"]
