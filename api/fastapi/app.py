"""
FastAPI app for Goblin Assistant runtime.

We import `debug_bootstrap` at the very top so that debugpy can be activated
before other heavy imports (like pydantic / uvicorn / compiling pydantic-core
wheels) are evaluated. This ensures the debugger can attach early and
catch import-time exceptions when the DEBUGPY env var is enabled.
"""

# Import debug bootstrap for local development (enables debugpy if DEBUGPY env var is set)
# import debug_bootstrap  # noqa: F401

# Import ddtrace configuration for APM and metrics
from ddtrace_config import goblin_tracer, statsd  # noqa: F401

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel
import asyncio
import json
import os
import time
import httpx
from dotenv import load_dotenv
import sys
from pathlib import Path

# Optional OpenAI import
try:
    from openai import OpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None
from metrics import MetricsCollector as GoblinMetrics, trace_provider_call

# Add src to path for imports
sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))

# Import the intelligent routing system
# from routing.router import (
#     route_task,
#     record_success,
# )
from rag import retrieve, add_document, embed_text, get_vector_db


# Simple routing function (fallback)
async def route_task(
    task_type: str, payload: dict, prefer_local: bool = True, stream: bool = False
):
    """Simple routing function for LLM providers."""
    try:
        if not OPENAI_AVAILABLE or not os.getenv("OPENAI_API_KEY"):
            return {
                "result": {
                    "text": "No LLM provider available. Please set OPENAI_API_KEY."
                },
                "provider": "none",
                "model": "unknown",
            }

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        messages = payload.get("messages", [])
        if not messages:
            # Convert simple prompt to messages
            prompt = payload.get("prompt", "")
            messages = [{"role": "user", "content": prompt}]

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=payload.get("max_tokens", 1000),
            temperature=payload.get("temperature", 0.7),
            stream=stream,
        )

        if stream:
            return response  # Return the stream object
        else:
            return {
                "result": {"text": response.choices[0].message.content},
                "provider": "openai",
                "model": "gpt-3.5-turbo",
            }
    except Exception as e:
        return {
            "result": {"text": f"Error: {str(e)}"},
            "provider": "error",
            "model": "unknown",
        }


def record_success(provider: str):
    """Record successful provider usage (stub)."""
    pass


# Import Redis polling store for production scalability
from redis_polling_store import RedisPollingStore

# Load environment variables
load_dotenv()

# Optional direct debugpy attach (useful for local troubleshooting)
# Set DEBUGPY_DIRECT=1 to enable listening and wait for debugger client to attach
if os.getenv("DEBUGPY_DIRECT"):
    try:
        import debugpy

        debugpy.listen(("127.0.0.1", 5678))
        print("Waiting for debugger to attach on 127.0.0.1:5678...")
        # Wait for client to attach to make debugging deterministic in dev
        debugpy.wait_for_client()
        print("Debugger attached.")
    except Exception as e:
        # Don't crash the app if debugpy isn't available in the current environment
        print(f"debugpy not available or failed to start: {e}")


app = FastAPI(title="Goblin Assistant Runtime (FastAPI)")

# Allow CORS for local dev (Vite / Tauri dev server)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:1420",
        "http://localhost:1420",
        "tauri://localhost",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ParseRequest(BaseModel):
    text: str
    default_goblin: Optional[str] = None


class ExecuteRequest(BaseModel):
    goblin: str
    task: str
    provider: Optional[str] = None
    model: Optional[str] = None
    code: Optional[str] = None


# OpenAI-compatible API models
class ChatMessage(BaseModel):
    role: str
    content: str
    name: Optional[str] = None

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        extra = "allow"


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 1.0
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False
    stop: Optional[List[str]] = None


class ChatCompletionChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: Optional[str] = None


class ChatCompletionUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: ChatCompletionUsage


class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    created: int
    owned_by: str = "goblin-assistant"


class ModelsResponse(BaseModel):
    object: str = "list"
    data: List[ModelInfo]


@app.get("/v1/models")
async def list_models():
    """OpenAI-compatible models endpoint."""
    return ModelsResponse(
        data=[
            ModelInfo(id="gpt-4", created=1677649963, owned_by="goblin-assistant"),
            ModelInfo(
                id="gpt-3.5-turbo", created=1677649963, owned_by="goblin-assistant"
            ),
        ]
    )


@app.get("/providers")
async def get_providers():
    from routing.router import PROVIDERS

    return JSONResponse(list(PROVIDERS.keys()))


@app.get("/api/health")
async def health_check():
    return JSONResponse({"status": "healthy", "service": "goblin-assistant-fastapi"})


@app.post("/continue/hook")
async def continue_hook(request: Request):
    """Endpoint used by the Continue VS Code extension to post events or tests."""
    data = await request.json()
    print(f"📥 Continue hook: {data}")

    # Echo back success and indicate which keys are configured
    return JSONResponse(
        {
            "success": True,
            "message": "Continue hook received",
            "data": data,
            "api_keys_configured": {
                "openai": bool(os.getenv("OPENAI_API_KEY")),
                "admin": bool(os.getenv("OPENAI_ADMIN_KEY")),
                "service": bool(os.getenv("OPENAI_SERVICE_KEY")),
            },
        }
    )


@app.post("/assistant/query")
async def assistant_query(request: Request):
    """Simple assistant query endpoint used by external UIs or tests.

    Accepts JSON { "query": "...", "user_id": "..." }
    """
    data = await request.json()
    query = data.get("query", "")
    user_id = data.get("user_id", "anonymous")

    # Run a local retrieval to provide contexts
    contexts = retrieve(query, k=4)

    # Minimal answer generation via routing system / simulated response
    # For now, call the routing.task system with a simple payload
    try:
        routing_resp = await route_task(
            task_type="chat",
            payload={"prompt": query, "contexts": contexts},
            prefer_local=True,
            stream=False,
        )
        # routing_resp may vary depending on providers; normalize
        answer = routing_resp.get("result", {}).get("text") or routing_resp.get("text")
        provider = routing_resp.get("provider")
        model = routing_resp.get("model")
    except Exception as e:
        print(f"assistant_query routing error: {e}")
        answer = f"Mock response to: {query}"
        provider = "mock"
        model = "test-model"

    return JSONResponse(
        {
            "answer": answer,
            "contexts": contexts,
            "usage": {"tokens": 0},
            "hit_rate": 0.0,
            "provider": provider,
            "model": model,
            "user_id": user_id,
        }
    )


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """OpenAI-compatible chat completions endpoint with RAG support."""
    try:
        # Extract user message
        user_message = ""
        for msg in request.messages:
            if msg.role == "user":
                user_message = msg.content
                break

        # Use RAG if requested (via custom parameter or if we detect a coding question)
        use_rag = getattr(request, "use_rag", False) or any(
            keyword in user_message.lower()
            for keyword in ["code", "function", "class", "api", "implementation"]
        )

        enhanced_messages = request.messages.copy()

        if use_rag and user_message:
            # Retrieve relevant context
            contexts = retrieve(user_message, k=3)

            if contexts:
                # Build context string
                context_parts = []
                for ctx in contexts:
                    metadata = ctx.get("metadata", {})
                    source = f"From {metadata.get('file_path', 'unknown')}"
                    if "start_line" in metadata:
                        source += f" (lines {metadata['start_line']}-{metadata.get('end_line', '?')})"
                    context_parts.append(f"{source}:\n{ctx['content']}")

                context_str = "\n\n".join(context_parts)

                # Add context as a system message
                enhanced_messages.insert(
                    0,
                    ChatMessage(
                        role="system",
                        content=f"You have access to the following relevant code context:\n\n{context_str}\n\nUse this context to provide accurate, helpful responses. If the context doesn't contain the needed information, say so clearly.",
                    ),
                )

        # Route to LLM provider
        routing_resp = await route_task(
            task_type="chat",
            payload={
                "messages": [
                    {"role": msg.role, "content": msg.content}
                    for msg in enhanced_messages
                ],
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "stream": request.stream,
            },
            stream=request.stream,
        )

        if request.stream:
            # Handle streaming response
            async def generate_stream():
                try:
                    async for chunk in routing_resp:
                        if hasattr(chunk, "choices") and chunk.choices:
                            choice = chunk.choices[0]
                            if hasattr(choice, "delta") and choice.delta.content:
                                yield f"data: {json.dumps({'choices': [{'delta': {'content': choice.delta.content}}]})}\n\n"

                    yield "data: [DONE]\n\n"
                except Exception as e:
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"

            return StreamingResponse(
                generate_stream(),
                media_type="text/plain",
                headers={"Content-Type": "text/plain; charset=utf-8"},
            )
        else:
            # Handle regular response
            content = routing_resp.get("result", {}).get(
                "text", "No response generated"
            )

            response = ChatCompletionResponse(
                id=f"chatcmpl-{int(time.time())}",
                object="chat.completion",
                created=int(time.time()),
                model=request.model,
                choices=[
                    ChatCompletionChoice(
                        index=0,
                        message=ChatMessage(role="assistant", content=content),
                        finish_reason="stop",
                    )
                ],
                usage=ChatCompletionUsage(
                    prompt_tokens=len(user_message.split()),
                    completion_tokens=len(content.split()),
                    total_tokens=len(user_message.split()) + len(content.split()),
                ),
            )

            return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat completion failed: {str(e)}")


@app.post("/parse")
async def parse_orchestration(req: ParseRequest):
    print(f"🔍 [DEBUG] Parsing orchestration: {req.text[:100]}...")
    import pdb

    pdb.set_trace()  # Debug breakpoint

    # Minimal parser: split on THEN and map default goblin if missing
    parts = [p.strip() for p in req.text.split("THEN") if p.strip()]
    steps = []
    for i, part in enumerate(parts):
        # allow `goblin: task` or just `task`
        if ":" in part:
            goblin, task = [p.strip() for p in part.split(":", 1)]
        else:
            goblin = req.default_goblin or "docs-writer"
            task = part
        steps.append(
            {
                "id": f"step{i + 1}",
                "goblin": goblin,
                "task": task,
                "dependencies": [],
                "batch": 0,
            }
        )
    result = {"steps": steps, "total_batches": 1, "max_parallel": 1}
    print(f"✅ [DEBUG] Parsed {len(steps)} steps")
    return result


@app.post("/execute")
async def execute_task(req: ExecuteRequest):
    print(
        f"🚀 [DEBUG] Executing task: goblin={req.goblin}, task={req.task[:50]}..., provider={req.provider}"
    )

    # Route the task to determine the best provider
    routed_provider = route_task(req.goblin, req.task, req.provider)

    # Generate a task ID
    task_id = f"task_{int(time.time())}_{req.goblin}"

    # For now, return the task ID - streaming will come from /stream
    result = {"taskId": task_id, "provider": routed_provider, "status": "queued"}

    print(f"✅ [DEBUG] Task queued with ID: {task_id}")
    return result


@app.post("/api/route_task")
async def api_route_task(request: Request):
    """Route a task through the intelligent routing system"""
    data = await request.json()
    task_type = data.get("task_type")
    payload = data.get("payload", {})
    opts = data.get("opts", {})

    if not task_type:
        return JSONResponse({"error": "task_type required"}, status_code=400)

    try:
        resp = await route_task(
            task_type,
            payload,
            prefer_local=opts.get("preferLocal", False),
            prefer_cost=opts.get("preferCost", False),
        )
        return JSONResponse(resp)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/route_task_stream")
async def api_route_task_stream(request: Request):
    """Route a task through the intelligent routing system with streaming response"""
    data = await request.json()
    task_type = data.get("task_type")
    payload = data.get("payload", {})
    opts = data.get("opts", {})

    if not task_type:
        return JSONResponse({"error": "task_type required"}, status_code=400)

    try:
        # call router with stream=True
        resp = await route_task(
            task_type,
            payload,
            prefer_local=opts.get("preferLocal", False),
            prefer_cost=opts.get("preferCost", False),
            stream=True,
        )
        if not resp.get("ok"):
            return JSONResponse(resp, status_code=500)

        # resp should contain "stream" async generator
        async def sse_generator():
            # provider meta first
            meta = {"provider": resp.get("provider"), "model": resp.get("model")}
            yield f"event: meta\ndata: {json.dumps(meta)}\n\n"
            async for chunk in resp["stream"]:
                # chunk may be dict (JSON) or raw text
                try:
                    data_text = (
                        json.dumps(chunk) if not isinstance(chunk, str) else chunk
                    )
                except Exception:
                    data_text = str(chunk)
                yield f"data: {data_text}\n\n"
            # final event
            yield "event: done\ndata: {}\n\n"

        return StreamingResponse(
            sse_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control",
                "X-Accel-Buffering": "no",  # nginx directive to disable buffering
            },
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# Redis-based polling store for high concurrency (production-ready)
_polling_store = RedisPollingStore()


@app.get("/api/health/stream")
async def health_stream():
    """Health check for streaming connections"""
    return JSONResponse({"status": "healthy", "streaming": "available"})


@app.post("/api/route_task_stream_start")
async def api_route_task_stream_start(request: Request):
    """Start a polling-based streaming task and return stream ID"""
    data = await request.json()
    task_type = data.get("task_type")
    payload = data.get("payload", {})
    opts = data.get("opts", {})

    if not task_type:
        return JSONResponse({"error": "task_type required"}, status_code=400)

    try:
        # call router with stream=True
        resp = await route_task(
            task_type,
            payload,
            prefer_local=opts.get("preferLocal", False),
            prefer_cost=opts.get("preferCost", False),
            stream=True,
        )

        if not resp.get("ok"):
            return JSONResponse(resp, status_code=500)

        # Create stream in Redis store
        stream_id = f"stream_{int(asyncio.get_event_loop().time() * 1000000)}"
        success = await _polling_store.create_stream(
            stream_id, {"provider": resp.get("provider"), "model": resp.get("model")}
        )
        if not success:
            return JSONResponse({"error": "Failed to create stream"}, status_code=500)

        # Start background task to collect chunks
        asyncio.create_task(_collect_stream_chunks(stream_id, resp["stream"]))

        return JSONResponse(
            {
                "stream_id": stream_id,
                "provider": resp.get("provider"),
                "model": resp.get("model"),
            }
        )

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def _collect_stream_chunks(stream_id: str, generator):
    """Background task to collect chunks from async generator"""
    try:
        async for chunk in generator:
            await _polling_store.add_chunk(stream_id, chunk)

        # Mark as done
        await _polling_store.complete_stream(stream_id)

    except Exception as e:
        print(f"Error collecting stream chunks for {stream_id}: {e}")
        await _polling_store.complete_stream(stream_id, error=str(e))


@app.get("/api/route_task_stream_poll/{stream_id}")
async def api_route_task_stream_poll(stream_id: str):
    """Poll for new chunks in a streaming task"""
    try:
        result = await _polling_store.poll_stream(stream_id)
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/route_task_stream_cancel/{stream_id}")
async def api_route_task_stream_cancel(stream_id: str):
    """Cancel a streaming task"""
    try:
        await _polling_store.complete_stream(stream_id, cancelled=True)
        return JSONResponse({"status": "cancelled"})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# Background cleanup is handled automatically by Redis TTL
# No manual cleanup task needed


# Start background cleanup task for Redis store
@app.on_event("startup")
async def startup_event():
    try:
        from redis_polling_store import start_cleanup_task

        start_cleanup_task()
        print("Cleanup task started successfully")
    except Exception as e:
        print(f"Error starting cleanup task: {e}")
        import traceback

        traceback.print_exc()


async def _stream_generator(task_id: str, req: ExecuteRequest):
    # Load API keys from environment - now supporting comprehensive provider list
    api_keys = {
        "openai": os.getenv("OPENAI_API_KEY"),
        "anthropic_claude": os.getenv("ANTHROPIC_API_KEY"),
        "grok": os.getenv("GROK_API_KEY"),
        "gemini": os.getenv("GEMINI_API_KEY"),
        "siliconflow": os.getenv("SILICONFLOW_API_KEY"),
        "deepseek": os.getenv("DEEPSEEK_API_KEY"),
        "moonshot": os.getenv("MOONSHOT_API_KEY"),
        "zhipuai": os.getenv("ZHIPUAI_API_KEY"),
        "baichuan": os.getenv("BAICHUAI_API_KEY"),
        "stepfun": os.getenv("STEPFUN_API_KEY"),
        "minimax": os.getenv("MINIMAX_API_KEY"),
        "alibaba_qwen": os.getenv("ALIBABA_QWEN_API_KEY"),
        "tencent_hunyuan": os.getenv("TENCENT_HUNYUAN_API_KEY"),
        "sense_time": os.getenv("SENSE_API_KEY"),
        "naga_ai": os.getenv("NAGA_API_KEY"),
        "h2o_ai": os.getenv("H2O_API_KEY"),
        "cloudflare_workers": os.getenv("CLOUDFLARE_GLOBAL_API_KEY"),
        "cloudflare_vectors": os.getenv("CLOUDFLARE_GLOBAL_API_KEY"),
        "huggingface": os.getenv("HF_API_KEY"),
        "together_ai": os.getenv("TOGETHER_API_KEY"),
        "replicate": os.getenv("REPLICATE_API_KEY"),
        "ollama_local": None,  # No API key needed
        "lm_studio_local": None,  # No API key needed
        "llamacpp": None,  # No API key needed
        "mistral": os.getenv("MISTRAL_API_KEY"),
        "groq": os.getenv("GROQ_API_KEY"),
        "perplexity": os.getenv("PERPLEXITY_API_KEY"),
        "fireworks": os.getenv("FIREWORKS_API_KEY"),
        "voyage_ai": os.getenv("VOYAGE_API_KEY"),
        "elevenlabs": os.getenv("ELEVENLABS_API_KEY"),
        "dashscope": os.getenv("DASHSCOPE_API_KEY"),
        # Legacy mappings for backward compatibility
        "anthropic": os.getenv("ANTHROPIC_API_KEY"),
        "cloudflare-global": os.getenv("CLOUDFLARE_GLOBAL_API_KEY"),
        "cloudflare-cakey": os.getenv("CLOUDFLARE_CAKEY_V10"),
        "vectorize": os.getenv("CLOUDFLARE_GLOBAL_API_KEY"),
    }

    # Local providers that don't require API keys
    local_providers = [
        "ollama_local",
        "lm_studio_local",
        "llamacpp",
        "ollama",
        "llamacpp",
        "lmstudio",
    ]

    # If no provider specified, or API key missing for cloud providers, use simulated streaming
    if not req.provider or (
        req.provider not in local_providers and not api_keys.get(req.provider)
    ):
        async for chunk in _simulated_stream_generator(task_id, req):
            yield chunk
        return

        # Use intelligent routing system instead of hardcoded provider selection
        try:
            # Determine capability based on request
            capability = "chat"  # Default capability
            if hasattr(req, "task") and req.task:
                if "reason" in req.task.lower():
                    capability = "reasoning"
                elif "code" in req.task.lower():
                    capability = "code"
                elif "summary" in req.task.lower():
                    capability = "summary"
                elif "search" in req.task.lower():
                    capability = "search"
                elif "embedding" in req.task.lower():
                    capability = "embedding"
                elif "image" in req.task.lower():
                    capability = "image"

            # Prepare payload for routing
            payload = {
                "prompt": req.code or "Please help me with this task.",
                "max_tokens": 1000,
                "temperature": 0.7,
            }

            # Route the task using intelligent routing
            routing_result = await route_task(
                task_type=capability,
                payload=payload,
                prefer_local=False,  # Can be made configurable later
                prefer_cost=False,  # Can be made configurable later
                max_retries=2,
                stream=True,
            )

            if routing_result.get("ok"):
                # Simulate streaming response based on routing result
                result_text = routing_result["result"].get(
                    "text", "Task completed successfully"
                )
                provider_used = routing_result["provider"]
                model_used = routing_result["model"]

                # Record success metrics
                record_success(provider_used)

                # Yield streaming chunks
                chunks = result_text.split()
                for i, chunk in enumerate(chunks):
                    chunk_data = {
                        "taskId": task_id,
                        "chunk": chunk + " ",
                        "token_count": len(chunk.split()),
                        "cost_delta": 0.0,
                        "provider": provider_used,
                        "model": model_used,
                        "is_code": False,
                    }
                    yield json.dumps(chunk_data) + "\n"
                    await asyncio.sleep(0.01)  # Simulate streaming delay

                # Final completion chunk
                final = {
                    "taskId": task_id,
                    "result": True,
                    "cost": 0.0,
                    "output": f"Completed via {provider_used} ({model_used})",
                    "total_tokens": len(result_text.split()),
                }
                yield json.dumps(final) + "\n"
            else:
                # Routing failed, fall back to simulation
                async for chunk in _simulated_stream_generator(task_id, req):
                    yield chunk
        except Exception as e:
            print(f"API call failed for {req.provider}: {e}")
            async for chunk in _simulated_stream_generator(task_id, req):
                yield chunk


async def _simulated_stream_generator(task_id: str, req: ExecuteRequest):
    # Fallback simulated streaming (existing logic)
    responses = {
        "docs-writer": [
            "Analyzing code structure...",
            "\n## Function Documentation\n\n### `add(a, b)`\n",
            "- **Parameters**: `a` (number), `b` (number)\n",
            "- **Returns**: Sum of a and b\n",
            "- **Example**: `add(2, 3)` returns `5`\n\n",
            "## Usage Notes\n",
            "This function performs basic arithmetic addition.\n",
            "Ensure both parameters are numeric types.\n",
        ],
        "code-writer": [
            "Generating unit test...",
            "\n```javascript\n",
            "describe('add function', () => {\n",
            "  test('should add two positive numbers', () => {\n",
            "    expect(add(2, 3)).toBe(5);\n",
            "  });\n\n",
            "  test('should handle zero', () => {\n",
            "    expect(add(0, 5)).toBe(5);\n",
            "  });\n\n",
            "  test('should handle negative numbers', () => {\n",
            "    expect(add(-1, 1)).toBe(0);\n",
            "  });\n",
            "});\n",
            "```\n",
        ],
    }

    content_parts = responses.get(
        req.goblin,
        [
            f"Processing task: {req.task}\n",
            "Step 1: Analyzing requirements...\n",
            "Step 2: Generating response...\n",
            f"Completed: {req.task}\n",
        ],
    )

    total_tokens = 0
    total_cost = 0

    for part in content_parts:
        tokens = part.split() if part.strip() else [part]

        for token in tokens:
            if token:
                await asyncio.sleep(0.05)

                token_count = len(token.split())
                cost_delta = 0.000001 * token_count

                payload = {
                    "taskId": task_id,
                    "chunk": token + " ",
                    "token_count": token_count,
                    "cost_delta": round(cost_delta, 9),
                    "provider": req.provider or "ollama",
                    "model": req.model or "qwen2.5",
                    "is_code": "`" in part or "function" in part.lower(),
                }

                total_tokens += token_count
                total_cost += cost_delta

                yield json.dumps(payload) + "\n"

    final = {
        "taskId": task_id,
        "result": True,
        "cost": round(total_cost, 6),
        "output": "".join(content_parts),
        "total_tokens": total_tokens,
    }
    yield json.dumps(final) + "\n"


async def _stream_openai(
    client: httpx.AsyncClient, task_id: str, req: ExecuteRequest, api_key: str
):
    """Stream from OpenAI API"""
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

    payload = {
        "model": req.model or "gpt-4",
        "messages": [
            {
                "role": "system",
                "content": f"You are a {req.goblin} assistant. {req.task}",
            },
            {"role": "user", "content": req.code or "Please help me with this task."},
        ],
        "stream": True,
        "temperature": 0.7,
    }

    async with client.stream("POST", url, json=payload, headers=headers) as response:
        if response.status_code != 200:
            raise Exception(f"OpenAI API error: {response.status_code}")

        total_tokens = 0
        total_cost = 0

        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data = line[6:]
                if data == "[DONE]":
                    break

                try:
                    chunk = json.loads(data)
                    if chunk.get("choices") and chunk["choices"][0].get(
                        "delta", {}
                    ).get("content"):
                        content = chunk["choices"][0]["delta"]["content"]

                        token_count = len(content.split())
                        cost_delta = 0.000002 * token_count  # Rough estimate for GPT-4

                        payload = {
                            "taskId": task_id,
                            "chunk": content,
                            "token_count": token_count,
                            "cost_delta": round(cost_delta, 9),
                            "provider": "openai",
                            "model": req.model or "gpt-4",
                            "is_code": False,
                        }

                        total_tokens += token_count
                        total_cost += cost_delta

                        yield json.dumps(payload) + "\n"
                except json.JSONDecodeError:
                    continue

    final = {
        "taskId": task_id,
        "result": True,
        "cost": round(total_cost, 6),
        "output": "Completed via OpenAI API",
        "total_tokens": total_tokens,
    }
    yield json.dumps(final) + "\n"


async def _stream_grok(
    client: httpx.AsyncClient, task_id: str, req: ExecuteRequest, api_key: str
):
    """Stream from Grok (xAI) API"""
    url = "https://api.x.ai/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

    payload = {
        "messages": [
            {
                "role": "system",
                "content": f"You are a {req.goblin} assistant. {req.task}",
            },
            {"role": "user", "content": req.code or "Please help me with this task."},
        ],
        "model": req.model or "grok-beta",
        "stream": True,
        "temperature": 0.7,
    }

    async with client.stream("POST", url, json=payload, headers=headers) as response:
        if response.status_code != 200:
            raise Exception(f"Grok API error: {response.status_code}")

        total_tokens = 0
        total_cost = 0

        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data = line[6:]  # Remove "data: " prefix
                if data == "[DONE]":
                    break

                try:
                    chunk_data = json.loads(data)
                    if chunk_data.get("choices"):
                        delta = chunk_data["choices"][0].get("delta", {})
                        content = delta.get("content", "")

                        if content:
                            token_count = len(content.split())
                            cost_delta = 0.000001 * token_count

                            payload = {
                                "taskId": task_id,
                                "chunk": content,
                                "token_count": token_count,
                                "cost_delta": round(cost_delta, 9),
                                "provider": "grok",
                                "model": req.model or "grok-4-latest",
                                "is_code": False,
                            }

                            total_tokens += token_count
                            total_cost += cost_delta

                            yield json.dumps(payload) + "\n"
                except json.JSONDecodeError:
                    continue

    final = {
        "taskId": task_id,
        "result": True,
        "cost": round(total_cost, 6),
        "output": "Completed via Grok API",
        "total_tokens": total_tokens,
    }
    yield json.dumps(final) + "\n"


async def _stream_anthropic(
    client: httpx.AsyncClient, task_id: str, req: ExecuteRequest, api_key: str
):
    """Stream from Anthropic Claude API"""
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }

    payload = {
        "model": req.model or "claude-3-sonnet-20240229",
        "max_tokens": 1000,
        "messages": [
            {
                "role": "user",
                "content": f"You are a {req.goblin} assistant. {req.task}\n\nCode: {req.code or 'No code provided'}",
            }
        ],
        "stream": True,
    }

    async with client.stream("POST", url, json=payload, headers=headers) as response:
        if response.status_code != 200:
            raise Exception(f"Anthropic API error: {response.status_code}")

        total_tokens = 0
        total_cost = 0

        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data = line[6:]
                if data == "[DONE]":
                    break

                try:
                    chunk = json.loads(data)
                    if chunk.get("type") == "content_block_delta":
                        content = chunk.get("delta", {}).get("text", "")

                        if content:
                            token_count = len(content.split())
                            cost_delta = 0.000001 * token_count

                            payload = {
                                "taskId": task_id,
                                "chunk": content,
                                "token_count": token_count,
                                "cost_delta": round(cost_delta, 9),
                                "provider": "anthropic",
                                "model": req.model or "claude-3-sonnet-20240229",
                                "is_code": False,
                            }

                            total_tokens += token_count
                            total_cost += cost_delta

                            yield json.dumps(payload) + "\n"
                except json.JSONDecodeError:
                    continue

    final = {
        "taskId": task_id,
        "result": True,
        "cost": round(total_cost, 6),
        "output": "Completed via Anthropic API",
        "total_tokens": total_tokens,
    }
    yield json.dumps(final) + "\n"


async def _stream_deepseek(
    client: httpx.AsyncClient, task_id: str, req: ExecuteRequest, api_key: str
):
    """Stream from DeepSeek API"""
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

    payload = {
        "model": req.model or "deepseek-chat",
        "messages": [
            {"role": "system", "content": f"You are a {req.goblin} assistant."},
            {
                "role": "user",
                "content": f"{req.task}\n\nCode: {req.code or 'No code provided'}",
            },
        ],
        "stream": True,
        "temperature": 0.7,
    }

    async with client.stream("POST", url, json=payload, headers=headers) as response:
        if response.status_code != 200:
            raise Exception(f"DeepSeek API error: {response.status_code}")

        total_tokens = 0
        total_cost = 0

        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data = line[6:]
                if data == "[DONE]":
                    break

                try:
                    chunk = json.loads(data)
                    if chunk.get("choices"):
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content", "")

                        if content:
                            token_count = len(content.split())
                            cost_delta = 0.000001 * token_count

                            payload = {
                                "taskId": task_id,
                                "chunk": content,
                                "token_count": token_count,
                                "cost_delta": round(cost_delta, 9),
                                "provider": "deepseek",
                                "model": req.model or "deepseek-chat",
                                "is_code": False,
                            }

                            total_tokens += token_count
                            total_cost += cost_delta

                            yield json.dumps(payload) + "\n"
                except json.JSONDecodeError:
                    continue

    final = {
        "taskId": task_id,
        "result": True,
        "cost": round(total_cost, 6),
        "output": "Completed via DeepSeek API",
        "total_tokens": total_tokens,
    }
    yield json.dumps(final) + "\n"


async def _stream_gemini(
    client: httpx.AsyncClient, task_id: str, req: ExecuteRequest, api_key: str
):
    """Stream from Google Gemini API"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{req.model or 'gemini-pro'}:streamGenerateContent?alt=sse"
    headers = {
        "Content-Type": "application/json",
    }

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": f"You are a {req.goblin} assistant. {req.task}\n\nCode: {req.code or 'No code provided'}"
                    }
                ]
            }
        ]
    }

    # Add API key as query parameter
    url_with_key = f"{url}&key={api_key}"

    async with client.stream(
        "POST", url_with_key, json=payload, headers=headers
    ) as response:
        if response.status_code != 200:
            raise Exception(f"Gemini API error: {response.status_code}")

        total_tokens = 0
        total_cost = 0

        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data = line[6:]

                try:
                    chunk = json.loads(data)
                    if chunk.get("candidates"):
                        content = (
                            chunk["candidates"][0]
                            .get("content", {})
                            .get("parts", [{}])[0]
                            .get("text", "")
                        )

                        if content:
                            token_count = len(content.split())
                            cost_delta = 0.000001 * token_count

                            payload = {
                                "taskId": task_id,
                                "chunk": content,
                                "token_count": token_count,
                                "cost_delta": round(cost_delta, 9),
                                "provider": "gemini",
                                "model": req.model or "gemini-pro",
                                "is_code": False,
                            }

                            total_tokens += token_count
                            total_cost += cost_delta

                            yield json.dumps(payload) + "\n"
                except json.JSONDecodeError:
                    continue

    final = {
        "taskId": task_id,
        "result": True,
        "cost": round(total_cost, 6),
        "output": "Completed via Gemini API",
        "total_tokens": total_tokens,
    }
    yield json.dumps(final) + "\n"


async def _stream_siliconflow(
    client: httpx.AsyncClient, task_id: str, req: ExecuteRequest, api_key: str
):
    """Stream from Siliconflow API"""
    url = "https://api.siliconflow.cn/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

    payload = {
        "model": req.model or "deepseek-ai/DeepSeek-V2.5",
        "messages": [
            {
                "role": "system",
                "content": f"You are a {req.goblin} assistant. {req.task}",
            },
            {"role": "user", "content": req.code or "Please help me with this task."},
        ],
        "stream": True,
        "temperature": 0.7,
    }

    async with client.stream("POST", url, json=payload, headers=headers) as response:
        if response.status_code != 200:
            raise Exception(f"Siliconflow API error: {response.status_code}")

        total_tokens = 0
        total_cost = 0

        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data = line[6:]
                if data == "[DONE]":
                    break

                try:
                    chunk = json.loads(data)
                    if chunk.get("choices") and chunk["choices"][0].get(
                        "delta", {}
                    ).get("content"):
                        content = chunk["choices"][0]["delta"]["content"]

                        token_count = len(content.split())
                        cost_delta = 0.000001 * token_count

                        payload = {
                            "taskId": task_id,
                            "chunk": content,
                            "token_count": token_count,
                            "cost_delta": round(cost_delta, 9),
                            "provider": "siliconflow",
                            "model": req.model or "deepseek-ai/DeepSeek-V2.5",
                            "is_code": False,
                        }

                        total_tokens += token_count
                        total_cost += cost_delta

                        yield json.dumps(payload) + "\n"
                except json.JSONDecodeError:
                    continue

    final = {
        "taskId": task_id,
        "result": True,
        "cost": round(total_cost, 6),
        "output": "Completed via Siliconflow API",
        "total_tokens": total_tokens,
    }
    yield json.dumps(final) + "\n"


async def _stream_moonshot(
    client: httpx.AsyncClient, task_id: str, req: ExecuteRequest, api_key: str
):
    """Stream from Moonshot AI API"""
    url = "https://api.moonshot.cn/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

    payload = {
        "model": req.model or "moonshot-v1-8k",
        "messages": [
            {
                "role": "system",
                "content": f"You are a {req.goblin} assistant. {req.task}",
            },
            {"role": "user", "content": req.code or "Please help me with this task."},
        ],
        "stream": True,
        "temperature": 0.7,
    }

    async with client.stream("POST", url, json=payload, headers=headers) as response:
        if response.status_code != 200:
            raise Exception(f"Moonshot AI API error: {response.status_code}")

        total_tokens = 0
        total_cost = 0

        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data = line[6:]
                if data == "[DONE]":
                    break

                try:
                    chunk = json.loads(data)
                    if chunk.get("choices") and chunk["choices"][0].get(
                        "delta", {}
                    ).get("content"):
                        content = chunk["choices"][0]["delta"]["content"]

                        token_count = len(content.split())
                        cost_delta = 0.000001 * token_count

                        payload = {
                            "taskId": task_id,
                            "chunk": content,
                            "token_count": token_count,
                            "cost_delta": round(cost_delta, 9),
                            "provider": "moonshot",
                            "model": req.model or "moonshot-v1-8k",
                            "is_code": False,
                        }

                        total_tokens += token_count
                        total_cost += cost_delta

                        yield json.dumps(payload) + "\n"
                except json.JSONDecodeError:
                    continue

    final = {
        "taskId": task_id,
        "result": True,
        "cost": round(total_cost, 6),
        "output": "Completed via Moonshot AI API",
        "total_tokens": total_tokens,
    }
    yield json.dumps(final) + "\n"


async def _stream_ollama(client: httpx.AsyncClient, task_id: str, req: ExecuteRequest):
    """Stream from local Ollama API"""
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    url = f"{ollama_url}/api/chat"

    payload = {
        "model": req.model or "qwen2.5:3b",
        "messages": [
            {
                "role": "system",
                "content": f"You are a {req.goblin} assistant. {req.task}",
            },
            {"role": "user", "content": req.code or "Please help me with this task."},
        ],
        "stream": True,
    }

    async with client.stream("POST", url, json=payload) as response:
        if response.status_code != 200:
            raise Exception(f"Ollama API error: {response.status_code}")

        total_tokens = 0

        async for line in response.aiter_lines():
            if line.strip():
                try:
                    chunk = json.loads(line)
                    if chunk.get("message", {}).get("content"):
                        content = chunk["message"]["content"]

                        token_count = len(content.split())
                        cost_delta = 0  # Free local model

                        payload = {
                            "taskId": task_id,
                            "chunk": content,
                            "token_count": token_count,
                            "cost_delta": cost_delta,
                            "provider": "ollama",
                            "model": req.model or "qwen2.5:3b",
                            "is_code": False,
                        }

                        total_tokens += token_count

                        yield json.dumps(payload) + "\n"

                    if chunk.get("done", False):
                        break
                except json.JSONDecodeError:
                    continue

    final = {
        "taskId": task_id,
        "result": True,
        "cost": 0,
        "output": "Completed via Ollama (local)",
        "total_tokens": total_tokens,
    }
    yield json.dumps(final) + "\n"


async def _stream_llamacpp(
    client: httpx.AsyncClient, task_id: str, req: ExecuteRequest
):
    """Stream from local llama.cpp server"""
    llamacpp_url = os.getenv("LLAMACPP_BASE_URL", "http://localhost:8080")
    url = f"{llamacpp_url}/completion"

    payload = {
        "prompt": f"You are a {req.goblin} assistant. {req.task}\n\nCode: {req.code or 'No code provided'}\n\nAssistant: ",
        "stream": True,
        "temperature": 0.7,
        "n_predict": 512,
    }

    async with client.stream("POST", url, json=payload) as response:
        if response.status_code != 200:
            raise Exception(f"llama.cpp API error: {response.status_code}")

        total_tokens = 0

        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data = line[6:]
                if data == "[DONE]":
                    break

                try:
                    chunk = json.loads(data)
                    if chunk.get("content"):
                        content = chunk["content"]

                        token_count = len(content.split())
                        cost_delta = 0  # Free local model

                        payload = {
                            "taskId": task_id,
                            "chunk": content,
                            "token_count": token_count,
                            "cost_delta": cost_delta,
                            "provider": "llamacpp",
                            "model": req.model or "local-model",
                            "is_code": False,
                        }

                        total_tokens += token_count

                        yield json.dumps(payload) + "\n"
                except json.JSONDecodeError:
                    continue

    final = {
        "taskId": task_id,
        "result": True,
        "cost": 0,
        "output": "Completed via llama.cpp (local)",
        "total_tokens": total_tokens,
    }
    yield json.dumps(final) + "\n"


async def _stream_lmstudio(
    client: httpx.AsyncClient, task_id: str, req: ExecuteRequest
):
    """Stream from local LM Studio API (OpenAI-compatible)"""
    lm_studio_url = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234")
    url = f"{lm_studio_url}/v1/chat/completions"

    payload = {
        "model": req.model or "local-model",
        "messages": [
            {
                "role": "system",
                "content": f"You are a {req.goblin} assistant. {req.task}",
            },
            {"role": "user", "content": req.code or "Please help me with this task."},
        ],
        "stream": True,
        "temperature": 0.7,
    }

    async with client.stream("POST", url, json=payload) as response:
        if response.status_code != 200:
            raise Exception(f"LM Studio API error: {response.status_code}")

        total_tokens = 0

        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data = line[6:]
                if data == "[DONE]":
                    break

                try:
                    chunk = json.loads(data)
                    if chunk.get("choices") and chunk["choices"][0].get(
                        "delta", {}
                    ).get("content"):
                        content = chunk["choices"][0]["delta"]["content"]

                        token_count = len(content.split())
                        cost_delta = 0  # Free local model

                        payload = {
                            "taskId": task_id,
                            "chunk": content,
                            "token_count": token_count,
                            "cost_delta": cost_delta,
                            "provider": "lmstudio",
                            "model": req.model or "local-model",
                            "is_code": False,
                        }

                        total_tokens += token_count

                        yield json.dumps(payload) + "\n"
                except json.JSONDecodeError:
                    continue

    final = {
        "taskId": task_id,
        "result": True,
        "cost": 0,
        "output": "Completed via LM Studio (local)",
        "total_tokens": total_tokens,
    }
    yield json.dumps(final) + "\n"


async def _stream_vectorize(
    client: httpx.AsyncClient, task_id: str, req: ExecuteRequest, api_key: str
):
    """Query Cloudflare Vectorize index"""
    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "your-account-id")
    index_name = os.getenv("VECTORIZE_INDEX_NAME", "your-vector-index")

    # For Vectorize, we need to generate an embedding first using Workers AI
    # Then query the vector database
    # This is a simplified implementation

    # First, generate embedding using Workers AI
    embed_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/baai/bge-large-en-v1.5"
    embed_headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    embed_payload = {"text": [req.task + (req.code or "")]}

    embed_response = await client.post(
        embed_url, json=embed_payload, headers=embed_headers
    )
    if embed_response.status_code != 200:
        raise Exception(f"Workers AI embedding error: {embed_response.status_code}")

    embed_data = embed_response.json()
    query_vector = (
        embed_data.get("result", {}).get("data", [[]])[0][0]
        if embed_data.get("result", {}).get("data")
        else []
    )

    if not query_vector:
        # Fallback: generate a simple vector for demo
        import random

        query_vector = [
            random.uniform(-1, 1) for _ in range(1024)
        ]  # BGE Large dimension

    # Now query Vectorize using v2 API
    query_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/vectorize/v2/indexes/{index_name}/query"
    query_headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    query_payload = {
        "vector": query_vector,
        "topK": 5,
        "returnValues": False,
        "returnMetadata": True,
    }

    query_response = await client.post(
        query_url, json=query_payload, headers=query_headers
    )
    if query_response.status_code != 200:
        raise Exception(f"Vectorize v2 query error: {query_response.status_code}")

    query_data = query_response.json()

    # Format results as text response
    matches = query_data.get("result", {}).get("matches", [])

    if matches:
        result_text = f"Found {len(matches)} similar vectors in Vectorize index '{index_name}':\n\n"
        for i, match in enumerate(matches, 1):
            result_text += f"{i}. ID: {match.get('id', 'N/A')}\n"
            result_text += f"   Score: {match.get('score', 0):.4f}\n"
            if match.get("metadata"):
                result_text += (
                    f"   Metadata: {json.dumps(match['metadata'], indent=2)}\n"
                )
            result_text += "\n"
    else:
        result_text = (
            f"No similar vectors found in Vectorize index '{index_name}' for the query."
        )

    # Stream the result as text
    total_tokens = len(result_text.split())

    # Send the result as a single chunk
    payload = {
        "taskId": task_id,
        "chunk": result_text,
        "token_count": total_tokens,
        "cost_delta": 0.000001 * total_tokens,  # Small cost for API calls
        "provider": "vectorize",
        "model": f"vectorize-{index_name}",
        "is_code": False,
    }

    yield json.dumps(payload) + "\n"

    final = {
        "taskId": task_id,
        "result": True,
        "cost": round(0.000001 * total_tokens, 6),
        "output": f"Completed via Cloudflare Vectorize (index: {index_name})",
        "total_tokens": total_tokens,
    }
    yield json.dumps(final) + "\n"


async def _stream_cloudflare_cakey(
    client: httpx.AsyncClient, task_id: str, req: ExecuteRequest, api_key: str
):
    """Stream from Cloudflare AI Gateway (CAKey v1.0)"""
    # Using Cloudflare AI Gateway with CAKey v1.0 - OpenAI-compatible endpoint
    url = "https://gateway.ai.cloudflare.com/v1/your-account-id/your-gateway/openai/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "cf-aig-authorization": f"Bearer {api_key}",
    }

    payload = {
        "model": req.model or "gpt-3.5-turbo",
        "messages": [
            {
                "role": "system",
                "content": f"You are a {req.goblin} assistant. {req.task}",
            },
            {"role": "user", "content": req.code or "Please help me with this task."},
        ],
        "stream": True,
        "temperature": 0.7,
    }

    async with client.stream("POST", url, json=payload, headers=headers) as response:
        if response.status_code != 200:
            raise Exception(f"Cloudflare AI Gateway API error: {response.status_code}")

        total_tokens = 0
        total_cost = 0

        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data = line[6:]
                if data == "[DONE]":
                    break

                try:
                    chunk = json.loads(data)
                    if chunk.get("choices") and chunk["choices"][0].get(
                        "delta", {}
                    ).get("content"):
                        content = chunk["choices"][0]["delta"]["content"]

                        token_count = len(content.split())
                        cost_delta = 0.000001 * token_count

                        payload = {
                            "taskId": task_id,
                            "chunk": content,
                            "token_count": token_count,
                            "cost_delta": round(cost_delta, 9),
                            "provider": "cloudflare-cakey",
                            "model": req.model or "gpt-3.5-turbo",
                            "is_code": False,
                        }

                        total_tokens += token_count
                        total_cost += cost_delta

                        yield json.dumps(payload) + "\n"
                except json.JSONDecodeError:
                    continue

    final = {
        "taskId": task_id,
        "result": True,
        "cost": round(total_cost, 6),
        "output": "Completed via Cloudflare AI Gateway",
        "total_tokens": total_tokens,
    }
    yield json.dumps(final) + "\n"


async def _stream_cloudflare_global(
    client: httpx.AsyncClient, task_id: str, req: ExecuteRequest, api_key: str
):
    """Stream from Cloudflare Workers AI (Global API Key)"""
    # Using Cloudflare Workers AI with global API key
    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "your-account-id")
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/meta/llama-3.1-8b-instruct"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    payload = {
        "messages": [
            {
                "role": "system",
                "content": f"You are a {req.goblin} assistant. {req.task}",
            },
            {"role": "user", "content": req.code or "Please help me with this task."},
        ],
        "stream": True,
    }

    async with client.stream("POST", url, json=payload, headers=headers) as response:
        if response.status_code != 200:
            raise Exception(f"Cloudflare Workers AI API error: {response.status_code}")

        total_tokens = 0
        total_cost = 0

        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data = line[6:]
                if data == "[DONE]":
                    break

                try:
                    chunk = json.loads(data)
                    # Cloudflare Workers AI response format may differ
                    content = (
                        chunk.get("response", "")
                        if isinstance(chunk, dict)
                        else str(chunk)
                    )

                    if content:
                        token_count = len(content.split())
                        cost_delta = 0.000001 * token_count

                        payload = {
                            "taskId": task_id,
                            "chunk": content,
                            "token_count": token_count,
                            "cost_delta": round(cost_delta, 9),
                            "provider": "cloudflare-global",
                            "model": req.model or "@cf/meta/llama-3.1-8b-instruct",
                            "is_code": False,
                        }

                        total_tokens += token_count
                        total_cost += cost_delta

                        yield json.dumps(payload) + "\n"
                except json.JSONDecodeError:
                    continue

    final = {
        "taskId": task_id,
        "result": True,
        "cost": round(total_cost, 6),
        "output": "Completed via Cloudflare Workers AI",
        "total_tokens": total_tokens,
    }
    yield json.dumps(final) + "\n"


async def _stream_dashscope(
    client: httpx.AsyncClient, task_id: str, req: ExecuteRequest, api_key: str
):
    """Stream from DashScope API"""
    url = "https://dashscope.aliyuncs.com/api/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

    payload = {
        "model": req.model or "qwen-turbo",
        "messages": [
            {
                "role": "system",
                "content": f"You are a {req.goblin} assistant. {req.task}",
            },
            {"role": "user", "content": req.code or "Please help me with this task."},
        ],
        "stream": True,
        "temperature": 0.7,
    }

    async with client.stream("POST", url, json=payload, headers=headers) as response:
        if response.status_code != 200:
            raise Exception(f"DashScope API error: {response.status_code}")

        total_tokens = 0
        total_cost = 0

        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data = line[6:]
                if data == "[DONE]":
                    break

                try:
                    chunk = json.loads(data)
                    if chunk.get("choices") and chunk["choices"][0].get(
                        "delta", {}
                    ).get("content"):
                        content = chunk["choices"][0]["delta"]["content"]

                        token_count = len(content.split())
                        cost_delta = (
                            0.000001 * token_count
                        )  # Rough estimate for DashScope

                        payload = {
                            "taskId": task_id,
                            "chunk": content,
                            "token_count": token_count,
                            "cost_delta": round(cost_delta, 9),
                            "provider": "dashscope",
                            "model": req.model or "qwen-turbo",
                            "is_code": False,
                        }

                        total_tokens += token_count
                        total_cost += cost_delta

                        yield json.dumps(payload) + "\n"
                except json.JSONDecodeError:
                    continue

    final = {
        "taskId": task_id,
        "result": True,
        "cost": round(total_cost, 6),
        "output": "Completed via DashScope API",
        "total_tokens": total_tokens,
    }
    yield json.dumps(final) + "\n"


@app.get("/stream")
async def stream(task_id: str, goblin: str, task: str):
    print(
        f"📡 [DEBUG] Starting stream: task_id={task_id}, goblin={goblin}, task={task[:50]}..."
    )
    import pdb

    pdb.set_trace()  # Debug breakpoint for streaming

    # We'll reconstruct a minimal ExecuteRequest to simulate streaming content
    req = ExecuteRequest(goblin=goblin, task=task)

    async def event_generator():
        try:
            chunk_count = 0
            async for chunk in _stream_generator(task_id, req):
                chunk_count += 1
                print(f"📦 [DEBUG] Streaming chunk #{chunk_count}: {chunk[:100]}...")
                # Each `chunk` is a JSON line; EventSourceResponse will send it as a default
                # 'message' event if we yield as `{'data': ...}` or a string. We use the
                # JSON line as the `data` so the client can parse it in `onmessage`.
                payload = json.loads(chunk)
                yield {"data": json.dumps(payload), "event": "chunk"}
        except Exception as e:
            print(f"❌ [DEBUG] Stream error: {e}")
            # Send error event
            yield {
                "data": json.dumps({"error": str(e), "taskId": task_id}),
                "event": "error",
            }

    return EventSourceResponse(
        event_generator(),
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
        },
    )


@app.get("/debug/env")
async def debug_env():
    """Debug endpoint to check environment variables"""
    return {
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", "NOT_SET")[:10] + "..."
        if os.getenv("OPENAI_API_KEY")
        else "NOT_SET",
        "OPENAI_ADMIN_KEY": os.getenv("OPENAI_ADMIN_KEY", "NOT_SET")[:10] + "..."
        if os.getenv("OPENAI_ADMIN_KEY")
        else "NOT_SET",
        "OPENAI_SERVICE_KEY": os.getenv("OPENAI_SERVICE_KEY", "NOT_SET")[:10] + "..."
        if os.getenv("OPENAI_SERVICE_KEY")
        else "NOT_SET",
        "PWD": os.getcwd(),
        "DOTENV_LOADED": "CHECKED",
    }
