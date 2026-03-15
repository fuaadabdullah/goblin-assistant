"""
Semantic chat router for Goblin Assistant
Enhanced chat endpoints with semantic retrieval and context-aware responses
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
import uuid
from datetime import datetime
import asyncio

from .storage.conversations import conversation_store
from .providers.dispatcher import invoke_provider
from .services.retrieval_service import RetrievalService, ContextBuilder, retrieval_service as _retrieval_singleton
from .services.embedding_service import embedding_worker
from .storage.models import MessageModel
from .input_validation import InputSanitizer
from .assistant_tools.registry import export_openai_tools
from .assistant_tools.executor import run_tool_loop, extract_tool_calls


router = APIRouter(prefix="/semantic-chat", tags=["semantic-chat"])


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
    tasks: List[Dict[str, Any]]
    memory_facts: List[Dict[str, Any]]
    total_tokens: int
    metadata: Dict[str, Any]


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=SemanticSendMessageResponse,
)
async def semantic_send_message(
    conversation_id: str, request: SemanticSendMessageRequest
):
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
        # Step 1: Validate conversation exists
        conversation = await conversation_store.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        user_id = conversation.user_id
        if not user_id:
            raise HTTPException(status_code=400, detail="Conversation has no user_id")

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
                context_bundle = await _retrieval_singleton.get_context_bundle(
                    query=request.message,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    max_tokens=request.max_context_tokens,
                )
                context_used = (
                    len(context_bundle.get("summaries", [])) > 0
                    or len(context_bundle.get("messages", [])) > 0
                    or len(context_bundle.get("tasks", [])) > 0
                    or len(context_bundle.get("memory_facts", [])) > 0
                )
            except Exception as e:
                print(f"Error during semantic retrieval: {e}")
                context_used = False

        # Step 4: Prepare conversation context for provider
        # Convert stored messages to provider-expected format
        recent_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in conversation.messages[-10:]  # Last 10 messages for context
        ]

        # Build enhanced prompt with semantic context
        if context_used and context_bundle:
            # Use semantic context builder
            enhanced_messages = ContextBuilder.build_contextual_prompt(
                user_message=request.message,
                context_bundle=context_bundle,
                conversation_history=recent_messages,
                max_context_tokens=request.max_context_tokens,
            )
        else:
            # Fallback to standard conversation history
            enhanced_messages = recent_messages

        # Step 5: Invoke AI provider via dispatcher
        import time

        start_time = time.time()

        payload = {
            "messages": enhanced_messages,
            "model": request.model,
        }

        # Inject registered tools for native function calling
        sem_tools = export_openai_tools()
        if sem_tools:
            payload["tools"] = sem_tools

        try:
            provider_response = await invoke_provider(
                pid=None,  # Let dispatcher choose best provider
                model=request.model,
                payload=payload,
                timeout_ms=60000,  # Longer timeout for semantic processing
                stream=request.stream,
            )

            # Tool-calling loop for semantic chat
            if (isinstance(provider_response, dict)
                    and provider_response.get("ok")
                    and extract_tool_calls(provider_response)):
                provider_response = await run_tool_loop(
                    messages=list(enhanced_messages),
                    invoke_fn=invoke_provider,
                    provider=None,
                    model=request.model,
                    tools=sem_tools if sem_tools else None,
                    timeout_ms=60000,
                )

            duration = time.time() - start_time
            success = isinstance(provider_response, dict) and provider_response.get(
                "ok", True
            )
            error = None if success else str(provider_response.get("error", "unknown"))
        except Exception as e:
            duration = time.time() - start_time
            raise

        # Step 6: Normalize provider response format
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

        # Step 7: Store AI response with metadata
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
                "context_tokens": context_bundle.get("total_tokens", 0)
                if context_used
                else 0,
            },
        )

        # Step 8: Queue embeddings for async processing
        if context_used:
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
    except HTTPException:
        raise
    except Exception as e:
        # Error details are now handled by ErrorHandlingMiddleware
        raise HTTPException(status_code=500, detail="Failed to send semantic message")


@router.get("/conversations/{conversation_id}/context")
async def get_context_bundle(
    conversation_id: str, query: str, k: int = 5, max_age_hours: int = 168
):
    """Retrieve semantic context for a conversation and query"""
    try:
        # Validate conversation exists
        conversation = await conversation_store.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        user_id = conversation.user_id
        if not user_id:
            raise HTTPException(status_code=400, detail="Conversation has no user_id")

        # Retrieve context
        context_bundle = await _retrieval_singleton.get_context_bundle(
            query=query,
            user_id=user_id,
            conversation_id=conversation_id,
            max_tokens=2000,
        )

        return context_bundle

    except HTTPException:
        raise
    except HTTPException:
        raise
    except Exception as e:
        # Error details are now handled by ErrorHandlingMiddleware
        raise HTTPException(status_code=500, detail="Failed to retrieve context")


@router.post("/conversations/{conversation_id}/summarize")
async def summarize_conversation(
    conversation_id: str,
    summary_length: int = 300,  # Target length in words
):
    """Generate and store a summary of the conversation"""
    try:
        # Validate conversation exists
        conversation = await conversation_store.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        user_id = conversation.user_id
        if not user_id:
            raise HTTPException(status_code=400, detail="Conversation has no user_id")

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
            "model": "gpt-3.5-turbo",
            "max_tokens": 500,
            "temperature": 0.3,
        }

        provider_response = await invoke_provider(
            pid=None,
            model="gpt-3.5-turbo",
            payload=payload,
            timeout_ms=30000,
            stream=False,
        )

        if isinstance(provider_response, dict) and provider_response.get("ok"):
            summary_text = provider_response["result"]["text"]
        else:
            raise Exception("Failed to generate summary")

        # Store summary and its embedding
        success = await _retrieval_singleton.embedding_service.store_conversation_summary(
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
    except HTTPException:
        raise
    except Exception as e:
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
        if not fact_text or not fact_text.strip():
            raise HTTPException(status_code=400, detail="Fact text cannot be empty")

        # Store memory fact and its embedding
        success = await _retrieval_singleton.embedding_service.store_memory_fact(
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
    except HTTPException:
        raise
    except Exception as e:
        # Error details are now handled by ErrorHandlingMiddleware
        raise HTTPException(status_code=500, detail="Failed to add memory fact")


@router.get("/users/{user_id}/memory/search")
async def search_memory_facts(
    user_id: str, query: str, categories: Optional[List[str]] = None, k: int = 5
):
    """Search user's memory facts using semantic similarity"""
    try:
        if not query or not query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")

        facts = await _retrieval_singleton.retrieve_memory_facts(
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
    except HTTPException:
        raise
    except Exception as e:
        # Error details are now handled by ErrorHandlingMiddleware
        raise HTTPException(status_code=500, detail="Failed to search memory facts")


# Start the embedding worker on startup
@router.on_event("startup")
async def startup_event():
    """Start the async embedding worker"""
    await embedding_worker.start()


@router.on_event("shutdown")
async def shutdown_event():
    """Stop the async embedding worker"""
    await embedding_worker.stop()
