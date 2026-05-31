"""
Semantic chat router for Goblin Assistant
Enhanced chat endpoints with semantic retrieval and context-aware responses
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional, Tuple
import uuid
from datetime import datetime
import structlog

from .storage.conversations import conversation_store
from .providers.dispatcher import invoke_provider
from .input_validation import InputSanitizer
from .assistant_tools.registry import export_openai_tools
from .assistant_tools.executor import run_tool_loop, extract_tool_calls
from .chat_router.helpers import _raise_structured_provider_error

logger = structlog.get_logger()


router = APIRouter(prefix="/semantic-chat", tags=["semantic-chat"])
DEFAULT_MODEL = "gpt-3.5-turbo"


def _get_context_builder():
    from .services.context_builder import ContextBuilder

    return ContextBuilder()


def _get_embedding_worker():
    from .services.embedding_service import embedding_worker

    return embedding_worker


def _get_retrieval_singleton():
    from .services.retrieval_service import retrieval_service

    return retrieval_service


class SemanticSendMessageRequest(BaseModel):
    message: str
    provider: Optional[str] = None  # None = let dispatcher choose
    model: Optional[str] = None  # None = use provider default
    stream: Optional[bool] = False
    metadata: Optional[Dict[str, Any]] = None
    # Semantic retrieval options
    use_semantic_retrieval: bool = True
    retrieval_k: int = 5
    max_context_tokens: int = 1500
    max_age_hours: int = 168  # 7 days


class SemanticSendMessageResponse(BaseModel):
    message_id: str
    response: str
    provider: str
    model: str
    timestamp: str
    context_used: bool
    context_details: Optional[Dict[str, Any]] = None


class ContextBundleResponse(BaseModel):
    query: str
    user_id: str
    conversation_id: Optional[str]
    retrieved_at: str
    summaries: List[Dict[str, Any]]
    messages: List[Dict[str, Any]]
    ephemeral_messages: List[Dict[str, Any]]
    tasks: List[Dict[str, Any]]
    memory_facts: List[Dict[str, Any]]
    total_tokens: int
    metadata: Dict[str, Any]


async def _get_conversation_or_404(conversation_id: str):
    conversation = await conversation_store.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if not conversation.user_id:
        raise HTTPException(status_code=400, detail="Conversation has no user_id")
    return conversation


def _context_has_content(context_bundle: Dict[str, Any]) -> bool:
    return any(
        len(context_bundle.get(bucket, [])) > 0
        for bucket in ("summaries", "messages", "ephemeral_messages", "tasks", "memory_facts")
    )


def _build_recent_messages(conversation, limit: int = 10) -> List[Dict[str, str]]:
    return [{"role": msg.role, "content": msg.content} for msg in conversation.messages[-limit:]]


async def _invoke_semantic_provider(
    enhanced_messages: List[Dict[str, Any]], request: SemanticSendMessageRequest
):
    payload: Dict[str, Any] = {"messages": enhanced_messages, "model": request.model}
    sem_tools = export_openai_tools()
    if sem_tools:
        payload["tools"] = sem_tools

    provider_response = await invoke_provider(
        pid=None,
        model=request.model,
        payload=payload,
        timeout_ms=60000,
        stream=request.stream,
    )

    if (
        isinstance(provider_response, dict)
        and provider_response.get("ok")
        and extract_tool_calls(provider_response)
    ):
        provider_response = await run_tool_loop(
            messages=list(enhanced_messages),
            invoke_fn=invoke_provider,
            provider=None,
            model=request.model,
            tools=sem_tools if sem_tools else None,
            timeout_ms=60000,
        )

    return provider_response


def _normalize_provider_response(
    provider_response: Any, request: SemanticSendMessageRequest
) -> Tuple[Dict[str, Any], str, str, str]:
    if isinstance(provider_response, dict) and provider_response.get("ok"):
        result_data = provider_response.get("result", {}) or {}
        return (
            result_data,
            result_data.get("text", ""),
            provider_response.get("provider", request.provider or "unknown"),
            provider_response.get("model", request.model or "unknown"),
        )

    if isinstance(provider_response, dict) and "choices" in provider_response:
        return (
            {},
            provider_response["choices"][0]["message"]["content"],
            provider_response.get("provider", request.provider or "unknown"),
            provider_response.get("model", request.model or "unknown"),
        )

    if isinstance(provider_response, dict) and not provider_response.get("ok"):
        _raise_structured_provider_error(provider_response)

    return (
        {},
        str(provider_response),
        request.provider or "unknown",
        request.model or "unknown",
    )


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=SemanticSendMessageResponse,
)
async def semantic_send_message(conversation_id: str, request: SemanticSendMessageRequest):
    """
    Send a message with semantic retrieval and context-aware responses

    Enhanced message processing flow:
    1. Validate conversation exists
    2. Add user message to conversation history
    3. Retrieve relevant context using semantic search
    4. Build contextual prompt with retrieved information
    5. Invoke AI provider with enhanced context
    6. Store embeddings asynchronously
    7. Return response with context details
    """
    try:
        retrieval_singleton = _get_retrieval_singleton()
        conversation = await _get_conversation_or_404(conversation_id)
        user_id = conversation.user_id

        # Step 2: Sanitize user input
        sanitized_message, message_validation = InputSanitizer.sanitize_chat_message(
            request.message
        )

        # Step 3: Add user message to conversation history (store sanitized content)
        user_message_id = str(uuid.uuid4())
        message_metadata = request.metadata or {}
        message_metadata["input_validation"] = message_validation

        await conversation_store.add_message_to_conversation(
            conversation_id=conversation_id,
            role="user",
            content=sanitized_message,  # Store sanitized content
            metadata=message_metadata,
        )

        # Step 3: Retrieve relevant context (if enabled)
        context_bundle = None
        context_used = False

        if request.use_semantic_retrieval:
            try:
                context_bundle = await retrieval_singleton.get_context_bundle(
                    query=request.message,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    max_tokens=request.max_context_tokens,
                )
                context_used = _context_has_content(context_bundle)
            except Exception as e:
                logger.warning(
                    "semantic_retrieval_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                    conversation_id=conversation_id,
                )
                context_used = False

        # Step 4: Prepare conversation context for provider
        recent_messages = _build_recent_messages(conversation, limit=10)

        # Build enhanced prompt with semantic context
        if context_used and context_bundle:
            # Use semantic context builder
            context_builder = _get_context_builder()
            enhanced_messages = await context_builder.build_contextual_prompt(
                user_id=user_id,
                user_message=request.message,
                context_bundle=context_bundle,
                conversation_history=recent_messages,
                max_context_tokens=request.max_context_tokens,
            )
        else:
            # Fallback to standard conversation history
            enhanced_messages = recent_messages

        # Step 5-6: Invoke provider and normalize result
        provider_response = await _invoke_semantic_provider(enhanced_messages, request)
        result_data, response_content, used_provider, used_model = _normalize_provider_response(
            provider_response, request
        )

        # Step 7: Store AI response with metadata
        usage = result_data.get("usage") or {}
        cost_usd = result_data.get("cost_usd")
        input_tokens = usage.get("prompt_tokens") or usage.get("input_tokens") or 0
        output_tokens = usage.get("completion_tokens") or usage.get("output_tokens") or 0

        response_message_id = str(uuid.uuid4())
        await conversation_store.add_message_to_conversation(
            conversation_id=conversation_id,
            role="assistant",
            content=response_content,
            metadata={
                "provider": used_provider,
                "model": used_model,
                "message_id": response_message_id,
                "semantic_context_used": context_used,
                "context_tokens": (context_bundle.get("total_tokens", 0) if context_used else 0),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": cost_usd,
            },
        )

        # Step 8: Queue embeddings for async processing
        if context_used:
            embedding_worker = _get_embedding_worker()
            # Queue user message embedding
            await embedding_worker.queue_message_embedding(
                user_id=user_id,
                conversation_id=conversation_id,
                message_id=user_message_id,
                content=request.message,
                metadata=request.metadata,
            )

            # Queue assistant response embedding
            await embedding_worker.queue_message_embedding(
                user_id=user_id,
                conversation_id=conversation_id,
                message_id=response_message_id,
                content=response_content,
                metadata={"provider": used_provider, "model": used_model},
            )

        # Step 9: Return enhanced response
        context_details = None
        if context_used and context_bundle:
            context_details = {
                "summaries_count": len(context_bundle.get("summaries", [])),
                "messages_count": len(context_bundle.get("messages", [])),
                "ephemeral_messages_count": len(context_bundle.get("ephemeral_messages", [])),
                "tasks_count": len(context_bundle.get("tasks", [])),
                "memory_facts_count": len(context_bundle.get("memory_facts", [])),
                "total_tokens": context_bundle.get("total_tokens", 0),
                "retrieved_at": context_bundle.get("retrieved_at"),
            }

        return SemanticSendMessageResponse(
            message_id=response_message_id,
            response=response_content,
            provider=used_provider,
            model=used_model,
            timestamp=datetime.utcnow().isoformat(),
            context_used=context_used,
            context_details=context_details,
        )

    except HTTPException:
        raise
    except Exception:
        # Error details are now handled by ErrorHandlingMiddleware
        raise HTTPException(status_code=500, detail="Failed to send semantic message")


@router.get("/conversations/{conversation_id}/context")
async def get_context_bundle(
    conversation_id: str, query: str, k: int = 5, max_age_hours: int = 168
):
    """Retrieve semantic context for a conversation and query"""
    try:
        retrieval_singleton = _get_retrieval_singleton()
        conversation = await _get_conversation_or_404(conversation_id)
        user_id = conversation.user_id

        # Retrieve context
        context_bundle = await retrieval_singleton.get_context_bundle(
            query=query,
            user_id=user_id,
            conversation_id=conversation_id,
            max_tokens=2000,
        )

        return context_bundle

    except HTTPException:
        raise
    except Exception:
        # Error details are now handled by ErrorHandlingMiddleware
        raise HTTPException(status_code=500, detail="Failed to retrieve context")


@router.post("/conversations/{conversation_id}/summarize")
async def summarize_conversation(
    conversation_id: str,
    summary_length: int = 300,  # Target length in words
):
    """Generate and store a summary of the conversation"""
    try:
        retrieval_singleton = _get_retrieval_singleton()
        conversation = await _get_conversation_or_404(conversation_id)

        # Build summary prompt
        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in conversation.messages[-20:]  # Last 20 messages
        ]

        summary_prompt = f"""Please summarize this conversation in approximately {summary_length} words. 
Focus on the key topics discussed, decisions made, and any important information that should be remembered.

Conversation:
{chr(10).join([f"{msg['role']}: {msg['content']}" for msg in messages])}

Summary:"""

        # Generate summary using AI
        payload = {
            "messages": [{"role": "user", "content": summary_prompt}],
            "model": DEFAULT_MODEL,
            "max_tokens": 500,
            "temperature": 0.3,
        }

        provider_response = await invoke_provider(
            pid=None,
            model=DEFAULT_MODEL,
            payload=payload,
            timeout_ms=30000,
            stream=False,
        )

        if isinstance(provider_response, dict) and provider_response.get("ok"):
            summary_text = provider_response["result"]["text"]
        else:
            raise Exception("Failed to generate summary")

        # Store summary and its embedding
        success = await retrieval_singleton.embedding_service.store_conversation_summary(
            conversation_id=conversation_id, summary_text=summary_text
        )

        if not success:
            raise Exception("Failed to store conversation summary")

        return {
            "success": True,
            "summary": summary_text,
            "conversation_id": conversation_id,
            "stored_at": datetime.utcnow().isoformat(),
        }

    except HTTPException:
        raise
    except Exception:
        # Error details are now handled by ErrorHandlingMiddleware
        raise HTTPException(status_code=500, detail="Failed to summarize conversation")


@router.post("/users/{user_id}/memory")
async def add_memory_fact(
    user_id: str,
    fact_text: str,
    category: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
):
    """Add a long-term memory fact for a user"""
    try:
        retrieval_singleton = _get_retrieval_singleton()

        if not fact_text or not fact_text.strip():
            raise HTTPException(status_code=400, detail="Fact text cannot be empty")

        # Store memory fact and its embedding
        success = await retrieval_singleton.embedding_service.store_memory_fact(
            user_id=user_id, fact_text=fact_text, category=category, metadata=metadata
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to store memory fact")

        return {
            "success": True,
            "message": "Memory fact stored successfully",
            "user_id": user_id,
            "category": category,
            "stored_at": datetime.utcnow().isoformat(),
        }

    except HTTPException:
        raise
    except Exception:
        # Error details are now handled by ErrorHandlingMiddleware
        raise HTTPException(status_code=500, detail="Failed to add memory fact")


@router.get("/users/{user_id}/memory/search")
async def search_memory_facts(
    user_id: str, query: str, categories: Optional[List[str]] = None, k: int = 5
):
    """Search user's memory facts using semantic similarity"""
    try:
        retrieval_singleton = _get_retrieval_singleton()

        if not query or not query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")

        facts = await retrieval_singleton.retrieve_memory_facts(
            user_id=user_id, query=query, categories=categories, k=k
        )

        return {
            "user_id": user_id,
            "query": query,
            "categories": categories,
            "facts": facts,
            "count": len(facts),
            "searched_at": datetime.utcnow().isoformat(),
        }

    except HTTPException:
        raise
    except Exception:
        # Error details are now handled by ErrorHandlingMiddleware
        raise HTTPException(status_code=500, detail="Failed to search memory facts")

