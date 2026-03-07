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

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid
import asyncio
import json
import time
from datetime import datetime

from .storage import conversation_store
from .providers.dispatcher_fixed import invoke_provider
from .services.retrieval_service import RetrievalService, ContextBuilder
from .services.context_assembly_service import context_assembly_service
from api.config.system_prompt import system_prompt_manager
from .services.embedding_service import embedding_worker
from .services.message_classifier import classification_pipeline, MessageType
from .services.write_time_matrix import write_time_intelligence
from .input_validation import InputSanitizer
from .storage.conversations import Conversation, ConversationMessage
from .auth.router import get_current_user, User as AuthenticatedUser

router = APIRouter(prefix="/chat", tags=["chat"])


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


class SendMessageResponse(BaseModel):
    message_id: str
    response: str
    provider: str
    model: str
    timestamp: str
    usage: Optional[Dict[str, Any]] = None
    cost_usd: Optional[float] = None
    correlation_id: Optional[str] = None


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
        print(f"Error creating conversation: {e}")
        import traceback

        traceback.print_exc()
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
):
    """Update conversation title

    Title update strategy:
    - Updates only the conversation title
    - Preserves all existing messages
    - Updates updated_at timestamp
    - Returns success/failure status
    """
    try:
        await _require_owned_conversation(conversation_id, current_user)
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
):
    """Delete a conversation

    Deletion strategy:
    - Permanently removes conversation and all messages
    - No soft-delete (data is irrecoverable)
    - Returns success/failure for client confirmation
    """
    try:
        await _require_owned_conversation(conversation_id, current_user)
        success = await conversation_store.delete_conversation(conversation_id)

        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")

        return {"success": True, "message": "Conversation deleted successfully"}
    except HTTPException:
        raise
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
        write_time_result = await write_time_intelligence.process_message(
            message_id=message_id,
            content=sanitized_message,  # Use sanitized content for processing
            role="user",
            user_id=conversation.user_id,
            conversation_id=conversation_id,
            metadata=request.metadata,
        )

        # Extract classification and decision results
        classification = write_time_result["classification"]
        decision = write_time_result["decision"]
        execution = write_time_result["execution"]

        # Build message metadata with Write-Time Intelligence results and input validation
        message_metadata = {
            "classification": classification,
            "decision": decision,
            "write_time_execution": execution,
            "memory_type": classification["type"],
            "confidence": classification["confidence"],
            "actions_taken": execution["actions_executed"],
            "processed_at": write_time_result["processed_at"],
            "input_validation": message_validation,  # Store validation metadata
        }

        # Add original metadata if provided
        if request.metadata:
            message_metadata.update(request.metadata)

        # Add message to conversation history (store sanitized content for display safety)
        await conversation_store.add_message_to_conversation(
            conversation_id=conversation_id,
            role="user",
            content=sanitized_message,  # Store sanitized content
            metadata=message_metadata,
            message_id=message_id,
        )

        # Step 3: Prepare conversation context for provider
        # Convert stored messages to provider-expected format
        conversation = await _require_owned_conversation(conversation_id, current_user)
        messages = [
            {"role": msg.role, "content": msg.content} for msg in conversation.messages
        ]

        # Step 4: Invoke AI provider via dispatcher
        # Provider selection strategy:
        # - request.provider=None lets dispatcher choose best available
        # - request.model=None uses provider's default model
        # - 30-second timeout prevents hanging requests

        start_time = time.time()
        payload = {
            "messages": messages,
            "model": request.model,
        }
        try:
            provider_response = await invoke_provider(
                pid=request.provider,
                model=request.model,
                payload=payload,
                timeout_ms=30000,
                stream=request.stream,
            )
        except Exception:
            raise

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
                error_msg = provider_response.get("error", "unknown-error")
                raise HTTPException(
                    status_code=500, detail=f"AI Provider error: {error_msg}"
                )

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
        if usage:
            assistant_metadata["usage"] = usage
        if cost_usd is not None:
            assistant_metadata["cost_usd"] = cost_usd
        if correlation_id:
            assistant_metadata["correlation_id"] = correlation_id

        await conversation_store.add_message_to_conversation(
            conversation_id=conversation_id,
            role="assistant",
            content=response_content,
            metadata=assistant_metadata,
            message_id=response_message_id,
        )

        # Step 7: Return standardized response
        return SendMessageResponse(
            message_id=response_message_id,
            response=response_content,
            provider=used_provider,
            model=used_model,
            timestamp=datetime.utcnow().isoformat(),
            usage=usage,
            cost_usd=cost_usd,
            correlation_id=correlation_id,
        )

    except HTTPException:
        raise
    except HTTPException:
        raise
    except Exception as e:
        # Error details are now handled by ErrorHandlingMiddleware
        raise HTTPException(status_code=500, detail="Failed to send message")


@router.post("/conversations/{conversation_id}/import")
async def import_conversation_messages(
    conversation_id: str,
    request: ImportConversationRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    try:
        await _require_owned_conversation(conversation_id, current_user)

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


@router.post("/completions")
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


@router.post("/contextual-chat", response_model=ContextualChatResponse)
async def contextual_chat(request: ContextualChatRequest):
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
        # Step 1: Validate user/conversation if provided
        user_id = request.user_id
        conversation_id = request.conversation_id

        if conversation_id and not user_id:
            # Try to get user_id from conversation
            conversation = await conversation_store.get_conversation(conversation_id)
            if conversation:
                user_id = conversation.user_id

        # Step 2: Assemble context using new system (if enabled)
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
            )

            context_assembly = assembly_result
            context_text = assembly_result.get("context", "")

            # Get system prompt with context
            system_prompt = system_prompt_manager.get_complete_prompt(
                context=context_text, user_query=request.message
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
            }

        else:
            # Fallback to simple system prompt
            system_prompt = system_prompt_manager.get_complete_prompt(
                user_query=request.message
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

        try:
            provider_response = await invoke_provider(
                pid=request.provider,  # Use specified provider or let dispatcher choose
                model=request.model,
                payload=payload,
                timeout_ms=30000,
                stream=request.stream,
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
        return ContextualChatResponse(
            message_id=response_message_id,
            response=response_content,
            provider=used_provider,
            model=used_model,
            timestamp=datetime.utcnow().isoformat(),
            context_assembly=context_assembly,
            token_usage=token_usage,
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


async def generate_chat_stream(message: str, conversation_id: Optional[str] = None):
    """Generate server-sent events for chat streaming"""
    # Send initial status
    yield f"data: {json.dumps({'status': 'started', 'message': 'Processing your request...'})}\n\n"
    await asyncio.sleep(0.5)

    # Simulate streaming response
    response_text = f"Response to: {message}"

    # Send chunks
    words = response_text.split()
    total_tokens = 0
    total_cost = 0

    for i, word in enumerate(words):
        await asyncio.sleep(0.1)  # Simulate processing delay

        chunk_data = {
            "content": word + (" " if i < len(words) - 1 else ""),
            "token_count": len(word) // 4 + 1,
            "cost_delta": 0.001,
            "done": False,
        }

        total_tokens += chunk_data["token_count"]
        total_cost += chunk_data["cost_delta"]

        yield f"data: {json.dumps(chunk_data)}\n\n"

    # Send completion
    completion_data = {
        "result": response_text,
        "cost": total_cost,
        "tokens": total_tokens,
        "model": "chat-model",
        "provider": "chat-provider",
        "duration_ms": len(words) * 100,
        "done": True,
    }

    yield f"data: {json.dumps(completion_data)}\n\n"


@router.post("/stream")
async def stream_chat(request: Dict[str, Any]):
    """Stream chat response using Server-Sent Events"""
    try:
        message = request.get("message", "")
        conversation_id = request.get("conversation_id")

        return StreamingResponse(
            generate_chat_stream(message, conversation_id),
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
