"""
FastAPI app for Goblin Assistant runtime.

We import `debug_bootstrap` at the very top so that debugpy can be activated
before other heavy imports (like pydantic / uvicorn / compiling pydantic-core
wheels) are evaluated. This ensures the debugger can attach early and
catch import-time exceptions when the DEBUGPY env var is enabled.
"""

# Import debug bootstrap for local development (enables debugpy if DEBUGPY env var is set)
# import debug_bootstrap  # noqa: F401

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from typing import Optional, Dict, Any
from pydantic import BaseModel
import asyncio
import json
import os
import httpx
from dotenv import load_dotenv
import sys
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))

# Import the intelligent routing system
from routing.router import (
    route_task,
    record_success,
)

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


@app.get("/providers")
async def get_providers():
    return JSONResponse(
        [
            "ollama",
            "llamacpp",
            "lm_studio_local",
            "openai",
            "gemini",
            "anthropic",
            "deepseek",
            "replicate",
            "grok",
            "siliconflow",
            "moonshot",
            "cloudflare-global",
            "cloudflare-cakey",
            "vectorize",
            "huggingface",
            "together_ai",
            "fireworks",
            "groq",
            "mistral",
            "perplexity",
            "voyage_ai",
            "elevenlabs",
        ]
    )


@app.get("/api/health")
async def health_check():
    return JSONResponse({"status": "healthy", "service": "goblin-assistant-fastapi"})


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

    # Start the task and return a taskId; streaming will come from /stream
    task_id = f"task_{req.goblin}_{req.task.replace(' ', '_')}_{int(asyncio.get_event_loop().time())}"
    print(f"📋 [DEBUG] Generated task_id: {task_id}")
    return {"taskId": task_id}


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
    """Stream from Alibaba Cloud DashScope API (OpenAI-compatible)"""
    base_url = os.getenv(
        "DASHSCOPE_HTTP_BASE_URL", "https://dashscope.aliyuncs.com/api/v1"
    )
    url = f"{base_url}/chat/completions"
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


# In-memory storage for API keys (for testing/demo purposes)
api_keys_store = {}


@app.post("/api-keys/{provider}")
async def store_api_key(provider: str, key: str):
    """Store an API key for a provider"""
    api_keys_store[provider] = key
    return {"status": "stored"}


@app.get("/api-keys/{provider}")
async def get_api_key(provider: str):
    """Retrieve an API key for a provider"""
    return {"key": api_keys_store.get(provider)}


@app.delete("/api-keys/{provider}")
async def clear_api_key(provider: str):
    """Clear an API key for a provider"""
    if provider in api_keys_store:
        del api_keys_store[provider]
    return {"status": "cleared"}


@app.get("/models/{provider}")
async def get_provider_models(provider: str):
    """Get available models for a provider"""
    # Comprehensive model lists matching provider configuration
    models = {
        "openai": ["gpt-4o", "gpt-4"],
        "anthropic_claude": ["claude-3"],
        "grok": ["grok-1"],
        "gemini": ["gemini-pro"],
        "siliconflow": ["deepseek-ai/DeepSeek-V2.5", "Qwen/Qwen2-72B-Instruct"],
        "deepseek": ["deepseek-chat", "deepseek-coder"],
        "moonshot": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
        "cloudflare_workers": [
            "@cf/meta/llama-3.1-8b-instruct",
            "@cf/meta/llama-3.1-70b-instruct",
        ],
        "lm_studio_local": ["local-model"],
        "ollama_local": ["qwen2.5:3b", "qwen2.5:7b", "llama2", "mistral"],
        "cloudflare_vectors": ["semantic-search", "vector-query"],
        "huggingface": ["sentence-transformers/all-MiniLM-L6-v2"],
        "replicate": ["black-forest-labs/flux-kontext-pro", "stability-ai/sdxl"],
        "mistral": ["mistral-large-latest"],
        "baichuan": ["Baichuan4"],
        "zhipuai": ["glm-4"],
        "sense_time": ["SenseChat-5"],
        "perplexity": ["llama-3.1-sonar-large-128k-online"],
        "fireworks": ["accounts/fireworks/models/llama-v3-70b-instruct"],
        "elevenlabs": ["eleven_monolingual_v1"],
        "dashscope": ["qwen-turbo", "qwen-plus", "qwen-max"],
        # Legacy mappings for backward compatibility
        "anthropic": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"],
        "ollama": ["qwen2.5:3b", "qwen2.5:7b", "llama2", "mistral"],
        "llamacpp": ["local-model", "gguf-model"],
        "lmstudio": ["local-model"],
        "cloudflare": ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"],
        "cloudflare-global": [
            "@cf/meta/llama-3.1-8b-instruct",
            "@cf/meta/llama-3.1-70b-instruct",
        ],
        "cloudflare-cakey": [
            "gpt-3.5-turbo",
            "gpt-4",
            "gpt-4-turbo",
            "claude-3-haiku",
            "claude-3-sonnet",
        ],
        "vectorize": ["semantic-search", "vector-query", "embedding-lookup"],
    }
    return models.get(provider, [])
