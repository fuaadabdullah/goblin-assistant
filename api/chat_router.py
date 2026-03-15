"""
Chat router for Goblin Assistant
Provides conversation management and chat completion endpoints

This module handles the full conversation lifecycle:
1. Conversation creation and persistence
2. Message threading and history management
3. Provider response normalization
4. OpenAI-compatible API endpoints

Key architectural patterns:
- Stateless API with conversation store for persistence
- Message threading with chronological ordering
- Provider-agnostic response normalization
- Graceful degradation for missing conversations
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid
import asyncio
import hashlib
import json
import os
import time
from datetime import datetime

from .storage import conversation_store
from .providers.dispatcher import invoke_provider
from .services.retrieval_service import RetrievalService, ContextBuilder
from .services.context_assembly_service import context_assembly_service
from api.config.system_prompt import system_prompt_manager, EDUCATION_SYSTEM_ADDENDUM
from .services.embedding_service import embedding_worker
from .services.message_classifier import classification_pipeline, message_classifier, MessageType
from .services.write_time_matrix import write_time_intelligence
from .input_validation import InputSanitizer
from .providers.base import ProviderErrorCategory
from .assistant_tools.registry import export_openai_tools
from .assistant_tools.executor import run_tool_loop, extract_tool_calls
from .storage.conversations import Conversation, ConversationMessage
from .storage.database import get_db
from .auth.router import get_current_user, User as AuthenticatedUser
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/chat", tags=["chat"])

# File upload configuration
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_MIME_TYPES = frozenset({
    "text/plain", "text/markdown", "text/csv", "text/html",
    "application/json", "application/pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/png", "image/jpeg", "image/gif", "image/webp",
})
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")

class ChatMessage(BaseModel):
    role: str  # "user", "assistant", "system"
    content: str
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None


class CreateConversationRequest(BaseModel):
    user_id: Optional[str] = None
    title: Optional[str] = None


class CreateConversationResponse(BaseModel):
    conversation_id: str
    title: str
    created_at: str


class SendMessageRequest(BaseModel):
    message: str
    provider: Optional[str] = None  # None = let dispatcher choose
    model: Optional[str] = None  # None = use provider default
    stream: Optional[bool] = False
    metadata: Optional[Dict[str, Any]] = None
    enable_context_assembly: Optional[bool] = True  # Inject RAG context like contextual-chat
    attachment_ids: Optional[List[str]] = None  # IDs from /chat/upload-file


class SendMessageResponse(BaseModel):
    message_id: str
    response: str
    provider: str
    model: str
    timestamp: str
    usage: Optional[Dict[str, Any]] = None
    cost_usd: Optional[float] = None
    correlation_id: Optional[str] = None
    visualizations: Optional[List[Dict[str, Any]]] = None


class ConversationInfo(BaseModel):
    conversation_id: str
    user_id: Optional[str]
    title: str
    message_count: int
    snippet: Optional[str] = None
    created_at: str
    updated_at: str


class UpdateConversationTitleRequest(BaseModel):
    title: str


class ImportConversationRequest(BaseModel):
    messages: List[ChatMessage]


class SSEErrorEvent(BaseModel):
    """Server-Sent Event error payload"""
    type: str = "error"  # "error", "warning", "info"
    code: str  # Machine-readable error code
    message: str  # User-friendly error message
    is_recoverable: bool = False  # Whether client can retry
    details: Optional[Dict[str, Any]] = None  # Additional context


class SSEDataEvent(BaseModel):
    """Generic Server-Sent Event data payload"""
    content: Optional[str] = None  # Streaming text chunk
    token_count: Optional[int] = None
    cost_delta: Optional[float] = None
    done: bool = False
    # Result fields (on completion)
    result: Optional[str] = None
    cost: Optional[float] = None
    tokens: Optional[int] = None
    model: Optional[str] = None
    provider: Optional[str] = None
    duration_ms: Optional[int] = None
    message_id: Optional[str] = None
    # Error fields
    error: Optional[str] = None
    error_code: Optional[str] = None
    is_recoverable: Optional[bool] = None


def _latest_snippet(conversation: Conversation) -> Optional[str]:
    if not conversation.messages:
        return None

    latest = conversation.messages[-1].content.strip()
    if not latest:
        return None

    if len(latest) <= 160:
        return latest
    return f"{latest[:157].rstrip()}..."


async def _require_owned_conversation(
    conversation_id: str, current_user: AuthenticatedUser
) -> Conversation:
    conversation = await conversation_store.get_conversation(conversation_id)
    if not conversation or conversation.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


async def _assert_conversation_owned(
    conversation_id: str,
    current_user: AuthenticatedUser,
    db: AsyncSession,
) -> None:
    """Lightweight ownership check — no message loading. Raises 404 if not owned."""
    if not await conversation_store.check_conversation_owner(
        conversation_id, current_user.id, db=db
    ):
        raise HTTPException(status_code=404, detail="Conversation not found")


def _extract_usage_and_cost(
    provider_response: Any,
) -> tuple[Optional[Dict[str, Any]], Optional[float], Optional[str]]:
    if not isinstance(provider_response, dict):
        return None, None, None

    result_data = provider_response.get("result")
    raw = result_data.get("raw") if isinstance(result_data, dict) else None
    if not isinstance(raw, dict):
        return None, None, None

    usage = raw.get("usage") if isinstance(raw.get("usage"), dict) else None

    cost_value = raw.get("cost_usd", raw.get("cost"))
    cost_usd = float(cost_value) if isinstance(cost_value, (int, float)) else None

    correlation_value = raw.get("correlation_id")
    correlation_id = correlation_value if isinstance(correlation_value, str) else None

    return usage, cost_usd, correlation_id


def _raise_structured_provider_error(provider_response: Dict[str, Any]) -> None:
    error_msg = str(provider_response.get("error") or "unknown-error")
    category_raw = provider_response.get("error_category")
    category = str(category_raw or ProviderErrorCategory.UNKNOWN.value)
    used_provider = str(provider_response.get("provider") or "unknown")

    if category == ProviderErrorCategory.AUTH.value:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "AUTHENTICATION_REQUIRED",
                "category": category,
                "message": "Authentication failed while contacting the AI provider.",
                "provider": used_provider,
                "provider_error": error_msg,
            },
        )

    if category == ProviderErrorCategory.RATE_LIMIT.value:
        raise HTTPException(
            status_code=429,
            detail={
                "code": "CHAT_RATE_LIMITED",
                "category": category,
                "message": "The AI provider is rate limiting requests. Please retry shortly.",
                "provider": used_provider,
                "provider_error": error_msg,
                "retry_after": 2,
            },
        )

    if category == ProviderErrorCategory.TIMEOUT.value:
        raise HTTPException(
            status_code=504,
            detail={
                "code": "CHAT_TIMEOUT",
                "category": category,
                "message": "The AI provider took too long to respond.",
                "provider": used_provider,
                "provider_error": error_msg,
            },
        )

    if category == ProviderErrorCategory.MODEL_ERROR.value:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "CHAT_PROVIDER_UNAVAILABLE",
                "category": category,
                "message": "The selected model or provider could not process this request.",
                "provider": used_provider,
                "provider_error": error_msg,
            },
        )

    if category in {
        ProviderErrorCategory.SERVER_ERROR.value,
        ProviderErrorCategory.CONNECTION.value,
    }:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "CHAT_BACKEND_UNAVAILABLE",
                "category": category,
                "message": "The AI backend is temporarily unavailable. Please retry in a moment.",
                "provider": used_provider,
                "provider_error": error_msg,
            },
        )

    raise HTTPException(
        status_code=502,
        detail={
            "code": "CHAT_PROVIDER_ERROR",
            "category": category,
            "message": "The AI provider returned an unexpected error.",
            "provider": used_provider,
            "provider_error": error_msg,
        },
    )


@router.post("/conversations", response_model=CreateConversationResponse)
async def create_conversation(
    request: CreateConversationRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Create a new conversation

    Conversation creation strategy:
    - Auto-generates UUID for conversation_id
    - Optional user_id for multi-tenant support
    - Auto-generates title if not provided
    - Sets created_at timestamp for ordering
    """
    try:
        # Sanitize and validate inputs
        sanitized_title = (
            InputSanitizer.sanitize_conversation_title(request.title)
            if request.title
            else None
        )
        conversation = await conversation_store.create_conversation(
            user_id=current_user.id, title=sanitized_title
        )

        return CreateConversationResponse(
            conversation_id=conversation.conversation_id,
            title=conversation.title,
            created_at=conversation.created_at.isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        # Error details are now handled by ErrorHandlingMiddleware
        logger.exception("error creating conversation", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create conversation")


@router.get("/conversations", response_model=List[ConversationInfo])
async def list_conversations(
    limit: int = 50,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """List conversations for a user

    Conversation listing strategy:
    - Filters by user_id when provided (multi-tenant)
    - Limits results for performance (default 50)
    - Returns metadata only (not full message history)
    - Ordered by updated_at (most recent first)
    """
    try:
        conversations = await conversation_store.list_conversations(
            user_id=current_user.id, limit=limit
        )

        return [
            ConversationInfo(
                conversation_id=conv.conversation_id,
                user_id=conv.user_id,
                title=conv.title,
                message_count=len(conv.messages),
                snippet=_latest_snippet(conv),
                created_at=conv.created_at.isoformat(),
                updated_at=conv.updated_at.isoformat(),
            )
            for conv in conversations
        ]
    except Exception as e:
        # Error details are now handled by ErrorHandlingMiddleware
        raise HTTPException(status_code=500, detail="Failed to list conversations")


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Get a conversation with all messages

    Full conversation retrieval:
    - Returns complete message history for context
    - Messages ordered chronologically (oldest first)
    - Includes metadata for debugging/analytics
    - 404 if conversation doesn't exist
    """
    try:
        conversation = await _require_owned_conversation(conversation_id, current_user)

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
                for msg in conversation.messages
            ],
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat(),
            "metadata": conversation.metadata,
        }
    except HTTPException:
        raise
    except Exception as e:
        # Error details are now handled by ErrorHandlingMiddleware
        raise HTTPException(status_code=500, detail="Failed to get conversation")


@router.put("/conversations/{conversation_id}/title")
async def update_conversation_title(
    conversation_id: str,
    request: UpdateConversationTitleRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update conversation title

    Title update strategy:
    - Updates only the conversation title
    - Preserves all existing messages
    - Updates updated_at timestamp
    - Returns success/failure status
    """
    try:
        await _assert_conversation_owned(conversation_id, current_user, db)
        success = await conversation_store.update_conversation_title(
            conversation_id=conversation_id, title=request.title
        )

        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")

        return {"success": True, "message": "Title updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        # Error details are now handled by ErrorHandlingMiddleware
        raise HTTPException(status_code=500, detail="Failed to update title")


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a conversation

    Deletion strategy:
    - Permanently removes conversation and all messages
    - No soft-delete (data is irrecoverable)
    - Returns success/failure for client confirmation
    """
    try:
        await _assert_conversation_owned(conversation_id, current_user, db)
        success = await conversation_store.delete_conversation(conversation_id)

        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")

        return {"success": True, "message": "Conversation deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        # Error details are now handled by ErrorHandlingMiddleware
        raise HTTPException(status_code=500, detail="Failed to delete conversation")


@router.post(
    "/conversations/{conversation_id}/messages", response_model=SendMessageResponse
)
async def send_message(
    conversation_id: str,
    request: SendMessageRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Send a message to a conversation and get AI response

    Message processing flow:
    1. Validate conversation exists
    2. Sanitize user input
    3. Add user message to conversation history
    4. Prepare conversation context for provider
    5. Invoke AI provider via dispatcher
    6. Normalize provider response format
    7. Store AI response with metadata
    8. Return standardized response

    Provider response normalization:
    - Supports OpenAI-style responses (choices[0].message.content)
    - Fallback to string conversion for other formats
    - Preserves provider/model information for tracking
    """
    try:
        # Step 1: Validate conversation exists
        conversation = await _require_owned_conversation(conversation_id, current_user)

        # Step 2: Sanitize user input
        sanitized_message, message_validation = InputSanitizer.sanitize_chat_message(
            request.message
        )

        # Step 3: Apply Write-Time Intelligence (The Anti-Rot Layer)
        # Use sanitized content for processing but store both original and sanitized
        message_id = str(uuid.uuid4())

        # Process message through Write-Time Intelligence using sanitized content
        # Wrapped in try-except: classification failures must not block chat
        message_metadata: Dict[str, Any] = {
            "input_validation": message_validation,
        }
        try:
            write_time_result = await write_time_intelligence.process_message(
                message_id=message_id,
                content=sanitized_message,
                role="user",
                user_id=conversation.user_id,
                conversation_id=conversation_id,
                metadata=request.metadata,
            )

            classification = write_time_result["classification"]
            decision = write_time_result["decision"]
            execution = write_time_result["execution"]

            message_metadata.update({
                "classification": classification,
                "decision": decision,
                "write_time_execution": execution,
                "memory_type": classification["type"],
                "confidence": classification["confidence"],
                "actions_taken": execution["actions_executed"],
                "processed_at": write_time_result["processed_at"],
            })
        except Exception as wti_err:
            logger.error(
                "write_time_intelligence_failed",
                message_id=message_id,
                conversation_id=conversation_id,
                user_id=current_user.id,
                error_type=type(wti_err).__name__,
                error=str(wti_err),
            )
            message_metadata["write_time_error"] = str(wti_err)

        # Add original metadata if provided
        if request.metadata:
            message_metadata.update(request.metadata)

        # Link pending file uploads to this message
        if request.attachment_ids:
            attachments_meta = []
            for aid in request.attachment_ids:
                upload = _pending_uploads.pop(aid, None)
                if upload and upload["user_id"] == current_user.id:
                    attachments_meta.append(
                        {
                            "id": upload["file_id"],
                            "filename": upload["filename"],
                            "mime_type": upload["mime_type"],
                            "size_bytes": upload["size_bytes"],
                        }
                    )
            if attachments_meta:
                message_metadata["attachments"] = attachments_meta

        # Add message to conversation history (store sanitized content for display safety)
        user_msg_saved = await conversation_store.add_message_to_conversation(
            conversation_id=conversation_id,
            role="user",
            content=sanitized_message,  # Store sanitized content
            metadata=message_metadata,
            message_id=message_id,
        )
        if not user_msg_saved:
            raise HTTPException(status_code=404, detail="Conversation not found when saving user message")

        # Step 3: Prepare conversation context for provider
        # Convert stored messages to provider-expected format
        conversation = await _require_owned_conversation(conversation_id, current_user)
        history_messages = [
            {"role": msg.role, "content": msg.content} for msg in conversation.messages
        ]

        # Step 3b: Assemble RAG context (same as contextual-chat)
        # Classify message to determine if an education addendum is needed
        msg_classification = message_classifier.classify_message(sanitized_message, "user")
        education_addendum = (
            EDUCATION_SYSTEM_ADDENDUM
            if msg_classification.message_type == MessageType.LEARNING
            else ""
        )

        context_metadata = {}
        if request.enable_context_assembly:
            try:
                assembly_result = await context_assembly_service.assemble_context(
                    query=sanitized_message,
                    user_id=current_user.id,
                    conversation_id=conversation_id,
                    conversation_history=history_messages[-10:],
                    model=request.model,
                )
                context_text = assembly_result.get("context", "")
                system_prompt = system_prompt_manager.get_complete_prompt_with_addendum(
                    context=context_text, user_query=sanitized_message, addendum=education_addendum
                )
                messages = [
                    {"role": "system", "content": system_prompt},
                ] + history_messages
                context_metadata = {
                    "context_assembly_enabled": True,
                    "context_assembly_layers": len(assembly_result.get("layers", [])),
                    "total_tokens_used": assembly_result.get("total_tokens_used", 0),
                    "degraded_mode": assembly_result.get("degraded_mode", False),
                    "degraded_reason": assembly_result.get("degraded_reason"),
                    "truncation_warnings": assembly_result.get("truncation_warnings", []),
                    "summary_fallback_applied": assembly_result.get("summary_fallback_applied", False),
                }
            except Exception as ctx_err:
                logger.warning(
                    "context_assembly_failed_in_send_message",
                    conversation_id=conversation_id,
                    error=str(ctx_err),
                )
                messages = history_messages
                context_metadata = {"context_assembly_enabled": False, "context_assembly_error": str(ctx_err)}
        else:
            messages = history_messages

        # Step 4: Invoke AI provider via dispatcher
        # Provider selection strategy:
        # - request.provider=None lets dispatcher choose best available
        # - request.model=None uses provider's default model
        # - 30-second timeout prevents hanging requests

        payload = {
            "messages": messages,
            "model": request.model,
        }

        # Inject registered tools for native function calling
        registered_tools = export_openai_tools()
        if registered_tools:
            payload["tools"] = registered_tools

        # If streaming requested, return SSE response via generate_chat_stream
        if request.stream:
            return StreamingResponse(
                generate_chat_stream(
                    message=request.message,
                    conversation_id=conversation_id,
                    current_user=current_user,
                    provider=request.provider,
                    model=request.model,
                ),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
            )

        start_time = time.time()
        try:
            provider_response = await invoke_provider(
                pid=request.provider,
                model=request.model,
                payload=payload,
                timeout_ms=30000,
                stream=False,
            )
        except Exception:
            raise

        # Step 4b: Tool-calling loop — if the LLM returned tool_calls,
        # execute them and re-invoke until we get a text response.
        if (isinstance(provider_response, dict)
                and provider_response.get("ok")
                and extract_tool_calls(provider_response)):
            provider_response = await run_tool_loop(
                messages=list(messages),
                invoke_fn=invoke_provider,
                provider=request.provider,
                model=request.model,
                tools=registered_tools if registered_tools else None,
                timeout_ms=30000,
                user_id=current_user.id,
                conversation_id=conversation_id,
            )

        # Step 5: Normalize provider response format
        # Different providers return different response structures
        if isinstance(provider_response, dict) and provider_response.get("ok"):
            # Standardized outcome from our dispatcher
            result_data = provider_response.get("result", {})
            response_content = result_data.get("text", "")
            used_provider = provider_response.get(
                "provider", request.provider or "unknown"
            )
            used_model = provider_response.get("model", request.model or "unknown")
        elif isinstance(provider_response, dict) and "choices" in provider_response:
            # OpenAI-style response format: choices[0].message.content
            response_content = provider_response["choices"][0]["message"]["content"]
            used_provider = provider_response.get(
                "provider", request.provider or "unknown"
            )
            used_model = provider_response.get("model", request.model or "unknown")
        else:
            # Check for error in dispatcher response
            if isinstance(provider_response, dict) and not provider_response.get("ok"):
                _raise_structured_provider_error(provider_response)

            # Fallback for non-standard response formats
            # Ensures we always return a usable response
            response_content = str(provider_response)
            used_provider = request.provider or "unknown"
            used_model = request.model or "unknown"

        usage, cost_usd, correlation_id = _extract_usage_and_cost(provider_response)

        # Step 6: Store AI response with metadata
        # Store for conversation continuity and analytics
        response_message_id = str(uuid.uuid4())
        assistant_metadata: Dict[str, Any] = {
            "provider": used_provider,
            "model": used_model,
            "message_id": response_message_id,
        }
        if context_metadata:
            assistant_metadata.update(context_metadata)
        if usage:
            assistant_metadata["usage"] = usage
        if cost_usd is not None:
            assistant_metadata["cost_usd"] = cost_usd
        if correlation_id:
            assistant_metadata["correlation_id"] = correlation_id

        asst_msg_saved = await conversation_store.add_message_to_conversation(
            conversation_id=conversation_id,
            role="assistant",
            content=response_content,
            metadata=assistant_metadata,
            message_id=response_message_id,
        )
        if not asst_msg_saved:
            logger.warning(
                "failed to persist assistant message",
                conversation_id=conversation_id,
                message_id=response_message_id,
            )

        # Step 7: Return standardized response
        # Include any chart-ready visualizations extracted during tool execution
        visualizations = None
        if isinstance(provider_response, dict) and provider_response.get("visualizations"):
            visualizations = provider_response["visualizations"]

        return SendMessageResponse(
            message_id=response_message_id,
            response=response_content,
            provider=used_provider,
            model=used_model,
            timestamp=datetime.utcnow().isoformat(),
            usage=usage,
            cost_usd=cost_usd,
            correlation_id=correlation_id,
            visualizations=visualizations,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "error in send_message",
            error=str(e),
            conversation_id=conversation_id,
            user_id=current_user.id,
        )
        raise HTTPException(status_code=500, detail="Failed to send message")


@router.post("/conversations/{conversation_id}/import")
async def import_conversation_messages(
    conversation_id: str,
    request: ImportConversationRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await _assert_conversation_owned(conversation_id, current_user, db)

        imported_messages = [
            ConversationMessage(
                role=message.role,
                content=message.content,
                metadata=message.metadata,
                timestamp=datetime.fromisoformat(message.timestamp.replace("Z", "+00:00"))
                if message.timestamp
                else None,
            )
            for message in request.messages
        ]

        success = await conversation_store.import_messages_to_conversation(
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


# ---------- File Upload Endpoints ----------

# In-memory store for pending uploads (keyed by file_id).
# In production this should be Redis; keeping it simple for MVP.
_pending_uploads: Dict[str, Dict[str, Any]] = {}


class FileUploadResponse(BaseModel):
    file_id: str
    filename: str
    mime_type: str
    size_bytes: int


class AttachmentInfo(BaseModel):
    id: str
    filename: str
    mime_type: str
    size_bytes: int
    url: str


@router.post("/upload-file", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Upload a file for later attachment to a chat message."""
    # Validate MIME type
    mime = file.content_type or "application/octet-stream"
    if mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail=f"File type not allowed: {mime}")

    # Read file content (enforcing size limit)
    contents = await file.read()
    if len(contents) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)} MB",
        )

    file_id = str(uuid.uuid4())
    safe_filename = os.path.basename(file.filename or "untitled")
    file_hash = hashlib.sha256(contents).hexdigest()
    storage_key = f"chat-uploads/{current_user.id}/{file_id}/{safe_filename}"

    # Persist to local uploads directory (swap for S3 in production)
    dest_dir = os.path.join(UPLOAD_DIR, current_user.id, file_id)
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, safe_filename)
    with open(dest_path, "wb") as f:
        f.write(contents)

    # Register pending upload for later association with a message
    _pending_uploads[file_id] = {
        "file_id": file_id,
        "user_id": current_user.id,
        "filename": safe_filename,
        "mime_type": mime,
        "size_bytes": len(contents),
        "storage_key": storage_key,
        "upload_hash": file_hash,
        "path": dest_path,
    }

    logger.info(
        "file_uploaded",
        file_id=file_id,
        filename=safe_filename,
        size_bytes=len(contents),
        user_id=current_user.id,
    )

    return FileUploadResponse(
        file_id=file_id,
        filename=safe_filename,
        mime_type=mime,
        size_bytes=len(contents),
    )


@router.get("/files/{file_id}")
async def download_file(
    file_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Download an uploaded file. Only the owning user can access it."""
    from fastapi.responses import FileResponse

    meta = _pending_uploads.get(file_id)
    if not meta or meta["user_id"] != current_user.id:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = meta["path"]
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        path=file_path,
        filename=meta["filename"],
        media_type=meta["mime_type"],
    )
async def chat_completion(request: Dict[str, Any]):
    """OpenAI-compatible chat completions endpoint

    Compatibility strategy:
    - Mirrors OpenAI Chat Completions API format
    - Supports messages, model, and stream parameters
    - Uses provider dispatcher for backend routing
    - Returns provider response directly (no normalization)

    Use cases:
    - Direct integration with OpenAI-compatible clients
    - Bypass conversation management for simple requests
    - Testing and debugging provider responses
    """
    try:
        messages = request.get("messages", [])
        model = request.get("model")
        stream = request.get("stream", False)

        # Use provider dispatcher to handle the completion
        # Let dispatcher choose optimal provider based on model/load
        payload = {
            "messages": messages,
            "model": model,
        }
        response = await invoke_provider(
            pid=None,  # Let dispatcher choose best provider
            model=model,
            payload=payload,
            timeout_ms=30000,
            stream=stream,
        )

        # For OpenAI compatibility, return the raw response if available
        if isinstance(response, dict) and response.get("ok"):
            result_data = response.get("result", {})
            if "raw" in result_data:
                # Add metadata if available
                raw_response = result_data["raw"]
                if isinstance(raw_response, dict):
                    raw_response["provider"] = response.get("provider", "unknown")
                    raw_response["model"] = response.get("model", model or "unknown")
                return raw_response

        return response

    except HTTPException:
        raise
    except Exception as e:
        # Error details are now handled by ErrorHandlingMiddleware
        raise HTTPException(status_code=500, detail="Chat completion failed")


class ContextualChatRequest(BaseModel):
    """Request for contextual chat with advanced context assembly"""

    message: str
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    stream: Optional[bool] = False
    metadata: Optional[Dict[str, Any]] = None
    enable_context_assembly: bool = True  # Toggle for new context assembly


class ContextualChatResponse(BaseModel):
    """Response for contextual chat with context assembly details"""

    message_id: str
    response: str
    provider: str
    model: str
    timestamp: str
    context_assembly: Optional[Dict[str, Any]] = None
    token_usage: Optional[Dict[str, Any]] = None
    visualizations: Optional[List[Dict[str, Any]]] = None


@router.post("/contextual-chat", response_model=ContextualChatResponse)
async def contextual_chat(
    request: ContextualChatRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Advanced chat endpoint with Retrieval Ordering + Token Budgeting

    This endpoint uses the new ContextAssemblyService to provide:
    1. Fixed retrieval stack order (System  Long-term  Working  Semantic  Ephemeral)
    2. Strict token budgeting with hard stops
    3. Deterministic context assembly
    4. Comprehensive logging and debugging

    Args:
        request: Contextual chat request with optional context assembly
    """
    try:
        # Step 1: Derive user_id from authenticated user; validate conversation ownership
        user_id = current_user.id
        conversation_id = request.conversation_id

        if conversation_id:
            await _assert_conversation_owned(conversation_id, current_user, db)

        # Step 2: Assemble context using new system (if enabled)
        # Classify message to determine if an education addendum is needed
        msg_classification = message_classifier.classify_message(request.message, "user")
        education_addendum = (
            EDUCATION_SYSTEM_ADDENDUM
            if msg_classification.message_type == MessageType.LEARNING
            else ""
        )

        context_assembly = None
        if request.enable_context_assembly and user_id:
            # Get recent conversation history for ephemeral memory
            conversation_history = []
            if conversation_id:
                conversation = await conversation_store.get_conversation(
                    conversation_id
                )
                if conversation:
                    conversation_history = [
                        {"role": msg.role, "content": msg.content}
                        for msg in conversation.messages[-10:]  # Last 10 messages
                    ]

            # Assemble context with new system
            assembly_result = await context_assembly_service.assemble_context(
                query=request.message,
                user_id=user_id,
                conversation_id=conversation_id,
                conversation_history=conversation_history,
                model=request.model,
            )

            context_assembly = assembly_result
            context_text = assembly_result.get("context", "")

            # Get system prompt with context
            system_prompt = system_prompt_manager.get_complete_prompt_with_addendum(
                context=context_text, user_query=request.message, addendum=education_addendum
            )

            # Build messages for provider
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.message},
            ]

            # Track token usage
            token_usage = {
                "total_tokens_used": assembly_result.get("total_tokens_used", 0),
                "remaining_tokens": assembly_result.get("remaining_tokens", 0),
                "layers_assembled": len(assembly_result.get("layers", [])),
                "assembly_time": assembly_result.get("assembly_log", {}).get(
                    "assembly_time"
                ),
                "degraded_mode": assembly_result.get("degraded_mode", False),
                "degraded_reason": assembly_result.get("degraded_reason"),
                "truncation_warnings": assembly_result.get("truncation_warnings", []),
                "summary_fallback_applied": assembly_result.get("summary_fallback_applied", False),
            }

        else:
            # Fallback to simple system prompt
            system_prompt = system_prompt_manager.get_complete_prompt_with_addendum(
                user_query=request.message, addendum=education_addendum
            )
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.message},
            ]
            token_usage = {"method": "fallback"}

        # Step 3: Invoke provider with assembled context
        start_time = time.time()
        payload = {
            "messages": messages,
            "model": request.model,
        }

        # Inject registered tools for native function calling
        ctx_tools = export_openai_tools()
        if ctx_tools:
            payload["tools"] = ctx_tools

        # If streaming requested, return SSE response
        if request.stream:
            # contextual_chat doesn't require conversation_id, create one if needed
            stream_conv_id = conversation_id
            if not stream_conv_id:
                new_conv = await conversation_store.create_conversation(
                    user_id=user_id, title=request.message[:50]
                )
                stream_conv_id = new_conv.conversation_id
            return StreamingResponse(
                generate_chat_stream(
                    message=request.message,
                    conversation_id=stream_conv_id,
                    current_user=current_user,
                    provider=request.provider,
                    model=request.model,
                ),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
            )

        try:
            provider_response = await invoke_provider(
                pid=request.provider,
                model=request.model,
                payload=payload,
                timeout_ms=30000,
                stream=False,
            )

            # Tool-calling loop for contextual chat
            if (isinstance(provider_response, dict)
                    and provider_response.get("ok")
                    and extract_tool_calls(provider_response)):
                provider_response = await run_tool_loop(
                    messages=list(messages),
                    invoke_fn=invoke_provider,
                    provider=request.provider,
                    model=request.model,
                    tools=ctx_tools if ctx_tools else None,
                    timeout_ms=30000,
                    user_id=user_id,
                    conversation_id=conversation_id,
                )

            duration = time.time() - start_time
            success = isinstance(provider_response, dict) and provider_response.get(
                "ok", True
            )
            error = None if success else str(provider_response.get("error", "unknown"))
        except Exception as e:
            duration = time.time() - start_time
            raise

        # Step 4: Normalize response
        if isinstance(provider_response, dict) and provider_response.get("ok"):
            # Standardized outcome from our dispatcher
            result_data = provider_response.get("result", {})
            response_content = result_data.get("text", "")
            used_provider = provider_response.get(
                "provider", request.provider or "unknown"
            )
            used_model = provider_response.get("model", request.model or "unknown")
        elif isinstance(provider_response, dict) and "choices" in provider_response:
            response_content = provider_response["choices"][0]["message"]["content"]
            used_provider = provider_response.get(
                "provider", request.provider or "unknown"
            )
            used_model = provider_response.get("model", request.model or "unknown")
        else:
            # Check for error in dispatcher response
            if isinstance(provider_response, dict) and not provider_response.get("ok"):
                error_msg = provider_response.get("error", "unknown-error")
                raise HTTPException(
                    status_code=500, detail=f"AI Provider error: {error_msg}"
                )

            response_content = str(provider_response)
            used_provider = request.provider or "unknown"
            used_model = request.model or "unknown"

        # Step 5: Store conversation if IDs provided
        message_id = str(uuid.uuid4())
        response_message_id = str(uuid.uuid4())

        if conversation_id:
            # Add user message
            await conversation_store.add_message_to_conversation(
                conversation_id=conversation_id,
                role="user",
                content=request.message,
                metadata={
                    "context_assembly_enabled": request.enable_context_assembly,
                    "context_assembly_layers": len(context_assembly.get("layers", []))
                    if context_assembly
                    else 0,
                    "metadata": request.metadata,
                }
                if request.enable_context_assembly
                else request.metadata,
            )

            # Add assistant response
            await conversation_store.add_message_to_conversation(
                conversation_id=conversation_id,
                role="assistant",
                content=response_content,
                metadata={
                    "provider": used_provider,
                    "model": used_model,
                    "context_assembly_used": request.enable_context_assembly,
                    "token_usage": token_usage,
                },
            )

        # Step 6: Return response with context assembly details
        visualizations = None
        if isinstance(provider_response, dict) and provider_response.get("visualizations"):
            visualizations = provider_response["visualizations"]

        return ContextualChatResponse(
            message_id=response_message_id,
            response=response_content,
            provider=used_provider,
            model=used_model,
            timestamp=datetime.utcnow().isoformat(),
            context_assembly=context_assembly,
            token_usage=token_usage,
            visualizations=visualizations,
        )

    except HTTPException:
        raise
    except HTTPException:
        raise
    except Exception as e:
        # Error details are now handled by ErrorHandlingMiddleware
        raise HTTPException(status_code=500, detail="Contextual chat failed")


@router.get("/debug/context-assembly")
async def debug_context_assembly():
    """Debug endpoint to inspect context assembly configuration"""
    try:
        debug_info = {
            "context_assembly": context_assembly_service.get_debug_info(),
            "system_prompt": system_prompt_manager.get_debug_info(),
            "timestamp": datetime.utcnow().isoformat(),
        }
        return debug_info
    except Exception as e:
        # Error details are now handled by ErrorHandlingMiddleware
        raise HTTPException(status_code=500, detail="Debug endpoint failed")


async def generate_chat_stream(
    message: str,
    conversation_id: str,
    current_user: AuthenticatedUser,
    provider: Optional[str] = None,
    model: Optional[str] = None,
):
    """Generate server-sent events for chat streaming via real provider.
    
    Error Handling:
    - Auth errors (401): Sent immediately with is_recoverable=false
    - Provider timeouts: Fallback to non-streaming with is_recoverable=true
    - Provider errors: Send error event with provider details
    - DB write failures: Send error but conversationHistory already persisted
    - Stream interruptions: Attempt reconnect or fallback
    
    Ensures:
    - User message always stored (before provider call)
    - Partial responses recoverable on retry
    - Specific error codes for client handling
    """
    # Send initial status
    yield f"data: {json.dumps({'status': 'started', 'message': 'Processing your request...'})}\n\n"

    accumulated_text = ""
    total_tokens = 0
    total_cost = 0.0
    used_provider = provider or "unknown"
    used_model = model or "unknown"
    start_time = time.time()
    user_message_stored = False
    response_message_id = str(uuid.uuid4())

    try:
        # Validate conversation ownership (auth check first)
        try:
            conversation = await _require_owned_conversation(conversation_id, current_user)
        except HTTPException as auth_exc:
            # Auth/authorization error — user not allowed to access this conversation
            error_event = {
                "type": "error",
                "code": "auth-failed",
                "message": "You do not have permission to access this conversation.",
                "is_recoverable": False,
                "done": True,
            }
            yield f"data: {json.dumps(error_event)}\n\n"
            return

        # Sanitize input
        sanitized_message, _ = InputSanitizer.sanitize_chat_message(message)

        # Store user message FIRST (before provider call)
        # This ensures the message persists even if the provider call fails
        try:
            await conversation_store.add_message_to_conversation(
                conversation_id=conversation_id,
                role="user",
                content=sanitized_message,
            )
            user_message_stored = True
        except Exception as db_exc:
            logger.error("db_write_error", exc=db_exc, stage="user_message_store")
            error_event = {
                "type": "error",
                "code": "db-write-error",
                "message": "Failed to save your message. Please retry.",
                "is_recoverable": True,
                "details": {"stage": "message_storage"},
                "done": True,
            }
            yield f"data: {json.dumps(error_event)}\n\n"
            return

        # Build message payload from conversation history
        try:
            conversation = await _require_owned_conversation(conversation_id, current_user)
            messages = [
                {"role": msg.role, "content": msg.content} for msg in conversation.messages
            ]
            payload = {"messages": messages, "model": model}
        except Exception as build_exc:
            logger.error("message_build_error", exc=build_exc)
            error_event = {
                "type": "error",
                "code": "message-build-error",
                "message": "Failed to build conversation context.",
                "is_recoverable": False,
                "done": True,
            }
            yield f"data: {json.dumps(error_event)}\n\n"
            return

        # Invoke provider with streaming
        try:
            provider_response = await invoke_provider(
                pid=provider,
                model=model,
                payload=payload,
                timeout_ms=30000,
                stream=True,
            )
        except asyncio.TimeoutError as timeout_exc:
            logger.warning("provider_timeout", provider=provider, model=model)
            error_event = {
                "type": "error",
                "code": "provider-timeout",
                "message": f"Provider {provider or 'default'} did not respond in time. Your message was saved.",
                "is_recoverable": True,
                "details": {"provider": provider, "timeout_ms": 30000},
                "done": True,
            }
            yield f"data: {json.dumps(error_event)}\n\n"
            return
        except Exception as provider_connect_exc:
            logger.error("provider_connection_error", exc=provider_connect_exc, provider=provider)
            error_event = {
                "type": "error",
                "code": "provider-connection-error",
                "message": f"Could not reach provider {provider or 'default'}. Your message was saved.",
                "is_recoverable": True,
                "details": {"provider": provider},
                "done": True,
            }
            yield f"data: {json.dumps(error_event)}\n\n"
            return

        # Check if provider returned success
        if not isinstance(provider_response, dict) or not provider_response.get("ok"):
            # Provider returned an error
            provider_error = provider_response.get("error", "unknown-error") if isinstance(provider_response, dict) else "provider-error"
            logger.warning("provider_error", error=provider_error, provider=provider)
            
            # Try fallback to non-streaming
            try:
                fallback_response = await invoke_provider(
                    pid=provider, model=model, payload=payload,
                    timeout_ms=30000, stream=False,
                )
                if isinstance(fallback_response, dict) and fallback_response.get("ok"):
                    result_data = fallback_response.get("result", {})
                    accumulated_text = result_data.get("text", str(fallback_response))
                    used_provider = fallback_response.get("provider", used_provider)
                    used_model = fallback_response.get("model", used_model)
                    # Send fallback result
                    yield f"data: {json.dumps({'content': accumulated_text, 'token_count': 0, 'cost_delta': 0, 'done': False})}\n\n"
                else:
                    # Fallback also failed
                    fallback_error = fallback_response.get("error", "unknown") if isinstance(fallback_response, dict) else "unknown"
                    logger.error("provider_fallback_failed", error=fallback_error)
                    error_event = {
                        "type": "error",
                        "code": "provider-error",
                        "message": f"Provider could not process your request: {provider_error}. Your message was saved.",
                        "is_recoverable": True,
                        "details": {"provider_error": provider_error},
                        "done": True,
                    }
                    yield f"data: {json.dumps(error_event)}\n\n"
                    return
            except asyncio.TimeoutError:
                logger.error("provider_fallback_timeout", provider=provider)
                error_event = {
                    "type": "error",
                    "code": "provider-timeout",
                    "message": f"Provider fallback timed out. Your message was saved.",
                    "is_recoverable": True,
                    "done": True,
                }
                yield f"data: {json.dumps(error_event)}\n\n"
                return
            except Exception as fallback_exc:
                logger.error("provider_fallback_error", exc=fallback_exc)
                error_event = {
                    "type": "error",
                    "code": "provider-error",
                    "message": "Provider unavailable. Your message was saved.",
                    "is_recoverable": True,
                    "done": True,
                }
                yield f"data: {json.dumps(error_event)}\n\n"
                return

        elif provider_response.get("stream"):
            # Real streaming path — consume async generator from provider
            try:
                stream_gen = provider_response["stream"]
                async for chunk in stream_gen:
                    try:
                        chunk_text = chunk.get("text", "") if isinstance(chunk, dict) else str(chunk)
                        if not chunk_text:
                            continue
                        accumulated_text += chunk_text
                        token_estimate = max(1, len(chunk_text) // 4)
                        total_tokens += token_estimate
                        yield f"data: {json.dumps({'content': chunk_text, 'token_count': token_estimate, 'cost_delta': 0, 'done': False})}\n\n"
                    except Exception as chunk_exc:
                        logger.error("chunk_processing_error", exc=chunk_exc)
                        # Continue with next chunk instead of failing entire stream
                        continue
            except asyncio.TimeoutError:
                logger.warning("stream_timeout", partial_response_len=len(accumulated_text))
                error_event = {
                    "type": "error",
                    "code": "stream-timeout",
                    "message": "Stream interrupted mid-response. Partial response received.",
                    "is_recoverable": True,
                    "details": {"partial_response": accumulated_text[:100]},  # Send first 100 chars as preview
                    "done": True,
                }
                yield f"data: {json.dumps(error_event)}\n\n"
                return
            except Exception as stream_exc:
                logger.error("streaming_error", exc=stream_exc, partial_response_len=len(accumulated_text))
                # If we have accumulated text, send it as partial response
                if accumulated_text:
                    error_event = {
                        "type": "error",
                        "code": "stream-interrupted",
                        "message": "Response stream was interrupted. Partial response saved.",
                        "is_recoverable": True,
                        "details": {"has_partial_response": True},
                        "done": True,
                    }
                    yield f"data: {json.dumps(error_event)}\n\n"
                else:
                    error_event = {
                        "type": "error",
                        "code": "stream-error",
                        "message": "Failed to stream response. Your message was saved.",
                        "is_recoverable": True,
                        "done": True,
                    }
                    yield f"data: {json.dumps(error_event)}\n\n"
                return
        else:
            # Provider returned ok but no stream key — extract text directly
            result_data = provider_response.get("result", {})
            accumulated_text = result_data.get("text", "")
            used_provider = provider_response.get("provider", used_provider)
            used_model = provider_response.get("model", used_model)
            if accumulated_text:
                yield f"data: {json.dumps({'content': accumulated_text, 'token_count': 0, 'cost_delta': 0, 'done': False})}\n\n"

        # Store assistant response
        try:
            await conversation_store.add_message_to_conversation(
                conversation_id=conversation_id,
                role="assistant",
                content=accumulated_text,
                metadata={"provider": used_provider, "model": used_model},
                message_id=response_message_id,
            )
        except Exception as db_response_exc:
            logger.error("db_write_error", exc=db_response_exc, stage="assistant_message_store")
            # Send warning but don't fail — user already got the response
            error_event = {
                "type": "warning",
                "code": "response-storage-failed",
                "message": "Unable to save assistant response to history, but response was generated.",
                "is_recoverable": False,
                "done": True,
            }
            yield f"data: {json.dumps(error_event)}\n\n"
            return

        duration_ms = int((time.time() - start_time) * 1000)

        # Send completion event
        yield f"data: {json.dumps({'result': accumulated_text, 'cost': total_cost, 'tokens': total_tokens, 'model': used_model, 'provider': used_provider, 'duration_ms': duration_ms, 'message_id': response_message_id, 'done': True})}\n\n"

    except HTTPException as http_exc:
        # HTTP exceptions (auth, not found, etc.)
        logger.warning("http_exception", status=http_exc.status_code, detail=http_exc.detail)
        error_event = {
            "type": "error",
            "code": f"http-{http_exc.status_code}",
            "message": str(http_exc.detail),
            "is_recoverable": False,
            "done": True,
        }
        yield f"data: {json.dumps(error_event)}\n\n"
    except Exception as exc:
        # Generic exception handler
        logger.exception("streaming_error_unhandled", exc=exc)
        error_event = {
            "type": "error",
            "code": "internal-error",
            "message": "An unexpected error occurred. Your message was saved if it got this far.",
            "is_recoverable": False,
            "done": True,
        }
        yield f"data: {json.dumps(error_event)}\n\n"


class StreamChatRequest(BaseModel):
    message: str
    conversation_id: str
    provider: Optional[str] = None
    model: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@router.post("/stream")
async def stream_chat(
    request: StreamChatRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Stream chat response using Server-Sent Events"""
    try:
        return StreamingResponse(
            generate_chat_stream(
                message=request.message,
                conversation_id=request.conversation_id,
                current_user=current_user,
                provider=request.provider,
                model=request.model,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control",
            },
        )
    except Exception as e:
        # Error details are now handled by ErrorHandlingMiddleware
        raise HTTPException(status_code=500, detail="Chat streaming failed")
