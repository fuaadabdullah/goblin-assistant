"""Conversation CRUD + bulk-import routes."""

from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.router import User as AuthenticatedUser
from ..auth.router import get_current_user
from ..core.contracts import SuccessEnvelope
from ..input_validation import InputSanitizer
from ..storage.conversations import ConversationMessage
from ..storage.database import get_readonly_db
from . import _runtime as _cr
from .schemas import (
    ConversationInfo,
    CreateConversationRequest,
    CreateConversationResponse,
    ImportConversationRequest,
    UpdateConversationTitleRequest,
)

logger = structlog.get_logger()

router = APIRouter()


@router.post("/conversations", response_model=SuccessEnvelope[CreateConversationResponse])
async def create_conversation(
    request: CreateConversationRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Create a new conversation.

    Auto-generates UUID + title when not provided; user_id comes from
    the authenticated principal (multi-tenant).
    """
    try:
        sanitized_title = (
            InputSanitizer.sanitize_conversation_title(request.title) if request.title else None
        )
        conversation = await _cr.conversation_store.create_conversation(
            user_id=current_user.id, title=sanitized_title
        )

        return SuccessEnvelope(
            data=CreateConversationResponse(
                conversation_id=conversation.conversation_id,
                title=conversation.title,
                created_at=conversation.created_at.isoformat(),
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("error creating conversation", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create conversation")


@router.get("/conversations", response_model=SuccessEnvelope[list[ConversationInfo]])
async def list_conversations(
    limit: int = 50,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """List conversations for the authenticated user.

    Returns metadata only (not message history). Ordered by updated_at desc.
    """
    try:
        conversations = await _cr.conversation_store.list_conversations(
            user_id=current_user.id, limit=limit
        )

        return SuccessEnvelope(
            data=[
                ConversationInfo(
                    conversation_id=conv.conversation_id,
                    user_id=conv.user_id,
                    title=conv.title,
                    message_count=len(conv.messages),
                    snippet=_cr._latest_snippet(conv),
                    created_at=conv.created_at.isoformat(),
                    updated_at=conv.updated_at.isoformat(),
                )
                for conv in conversations
            ]
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to list conversations")


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    offset: int = 0,
    limit: int = 50,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Get a conversation with paginated messages.

    Query Parameters:
    - offset: messages to skip (default 0)
    - limit: max messages to return (default 50, capped at 500)
    """
    try:
        conversation = await _cr._require_owned_conversation(conversation_id, current_user)

        offset = max(0, min(offset, len(conversation.messages)))
        limit = max(1, min(limit, 500))

        paginated_messages = conversation.messages[offset : offset + limit]
        total_messages = len(conversation.messages)

        return {
            "conversation_id": conversation.conversation_id,
            "user_id": conversation.user_id,
            "title": conversation.title,
            "messages": [
                {
                    "message_id": msg.message_id,
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "metadata": msg.metadata,
                }
                for msg in paginated_messages
            ],
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat(),
            "metadata": conversation.metadata,
            "pagination": {
                "offset": offset,
                "limit": limit,
                "total": total_messages,
                "returned": len(paginated_messages),
                "has_more": offset + limit < total_messages,
            },
        }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to get conversation")


@router.put("/conversations/{conversation_id}/title")
async def update_conversation_title(
    conversation_id: str,
    request: UpdateConversationTitleRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_readonly_db),
):
    """Update conversation title (preserves messages + bumps updated_at)."""
    try:
        await _cr._assert_conversation_owned(conversation_id, current_user, db)
        success = await _cr.conversation_store.update_conversation_title(
            conversation_id=conversation_id, title=request.title
        )

        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")

        return {"success": True, "message": "Title updated successfully"}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to update title")


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_readonly_db),
):
    """Delete a conversation permanently (no soft-delete)."""
    try:
        await _cr._assert_conversation_owned(conversation_id, current_user, db)
        success = await _cr.conversation_store.delete_conversation(conversation_id)

        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")

        return {"success": True, "message": "Conversation deleted successfully"}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to delete conversation")


@router.post("/conversations/{conversation_id}/import")
async def import_conversation_messages(
    conversation_id: str,
    request: ImportConversationRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_readonly_db),
):
    try:
        await _cr._assert_conversation_owned(conversation_id, current_user, db)

        imported_messages = [
            ConversationMessage(
                role=message.role,
                content=message.content,
                metadata=message.metadata,
                timestamp=(
                    datetime.fromisoformat(message.timestamp.replace("Z", "+00:00"))
                    if message.timestamp
                    else None
                ),
            )
            for message in request.messages
        ]

        success = await _cr.conversation_store.import_messages_to_conversation(
            conversation_id, imported_messages
        )
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")

        return {"success": True, "imported_count": len(imported_messages)}
    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid message timestamp")
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to import conversation")
