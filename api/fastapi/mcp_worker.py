"""
MCP Worker - Redis queue processor for MCP requests.

This worker processes MCP requests from the Redis queue,
handles provider routing, streaming, and result storage.
"""

import os
import json
import asyncio
from typing import Dict, Any
from datetime import datetime

import redis
from ddtrace import tracer

from mcp_models import MCPRequest, MCPResult, create_engine_and_session
from mcp_providers import provider_manager
from metrics import metrics as goblin_metrics
from chroma_indexer import SecretScanner

# Initialize components
engine, SessionLocal = create_engine_and_session()
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"), port=6379, decode_responses=True
)


class MCPWorker:
    """MCP request processor."""

    def __init__(self):
        self.db = SessionLocal()
        self.queue = redis_client

    def log_event(self, request_id: str, event_type: str, payload: Dict[str, Any]):
        """Log an event (simplified - in real impl, use proper event logging)."""
        print(f"EVENT: {request_id} - {event_type} - {payload}")

    def publish_stream(self, request_id: str, data: Dict[str, Any]):
        """Publish data to WebSocket stream."""
        self.queue.publish(f"mcp:stream:{request_id}", json.dumps(data))

    async def process_request(self, request_id: str):
        """Process a single MCP request."""
        with tracer.trace("mcp.worker.process_request") as span:
            span.set_tag("request.id", request_id)

            # Track assistant latency start
            assistant_start_time = datetime.utcnow()

            try:
                # Get request from database
                request = (
                    self.db.query(MCPRequest)
                    .filter(MCPRequest.id == request_id)
                    .first()
                )
                if not request:
                    print(f"Request {request_id} not found")
                    return

                if request.status != "pending":
                    print(
                        f"Request {request_id} already processed (status: {request.status})"
                    )
                    return

                # Update status to running
                request.status = "running"
                request.attempts += 1
                request.updated_at = datetime.utcnow()
                self.db.commit()

                # Publish status update
                self.publish_stream(
                    request_id,
                    {
                        "type": "status_update",
                        "status": "running",
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )

                self.log_event(
                    request_id,
                    "processing_started",
                    {"attempt": request.attempts, "task_type": request.task_type},
                )

                # Simulate RAG retrieval if context requested
                context_docs = []
                context_used = False
                if hasattr(request, "context_ids") and request.context_ids:
                    # TODO: Implement actual RAG retrieval
                    context_docs = [
                        "Mock context document 1",
                        "Mock context document 2",
                    ]
                    context_used = True

                # Track RAG hit rate
                goblin_metrics.record_rag_hit_rate(request.task_type, context_used)

                # Simulate provider selection and processing
                provider = self.select_provider(request)
                result = await self.call_provider(provider, request, context_docs)

                # Check if fallback was used (error in result indicates fallback)
                fallback_used = "error" in result and result.get("provider") == "mock"
                goblin_metrics.record_fallback_rate(provider, fallback_used)

                # Store result
                db_result = MCPResult(
                    request_id=request_id,
                    result=result,
                    tokens=result.get("tokens", 0),
                    cost_usd=result.get("cost_usd", 0.0),
                )
                self.db.add(db_result)

                # Update request
                request.status = "finished"
                request.last_provider = provider
                request.updated_at = datetime.utcnow()
                self.db.commit()

                # Log completion
                self.log_event(
                    request_id,
                    "processing_completed",
                    {
                        "provider": provider,
                        "tokens": result.get("tokens", 0),
                        "cost_usd": result.get("cost_usd", 0.0),
                    },
                )

                # Publish completion
                self.publish_stream(
                    request_id,
                    {
                        "type": "completed",
                        "result": result,
                        "tokens": result.get("tokens", 0),
                        "cost_usd": result.get("cost_usd", 0.0),
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )

                # Calculate and record assistant latency (p95 tracking)
                assistant_latency_ms = (
                    datetime.utcnow() - assistant_start_time
                ).total_seconds() * 1000
                goblin_metrics.record_assistant_latency(
                    request.task_type, assistant_latency_ms
                )

                # Track token usage and cost
                tokens_used = result.get("tokens", 0)
                cost_usd = result.get("cost_usd", 0.0)
                if tokens_used > 0:
                    goblin_metrics.record_token_usage(
                        provider, result.get("model", "unknown"), tokens_used
                    )
                if cost_usd > 0:
                    goblin_metrics.record_cost_tracking(provider, cost_usd)

                # Emit legacy metrics for compatibility
                goblin_metrics.histogram(
                    "goblin.mcp.request.latency_ms",
                    (datetime.utcnow() - request.created_at).total_seconds() * 1000,
                )
                goblin_metrics.increment("goblin.mcp.tokens", result.get("tokens", 0))
                goblin_metrics.histogram(
                    "goblin.mcp.provider.latency_ms",
                    result.get("latency_ms", 1000),
                    tags={"provider": provider},
                )

            except Exception as e:
                # Handle errors
                print(f"Error processing request {request_id}: {e}")

                request.status = "failed"
                request.updated_at = datetime.utcnow()
                self.db.commit()

                self.log_event(request_id, "processing_failed", {"error": str(e)})

                self.publish_stream(
                    request_id,
                    {
                        "type": "error",
                        "message": str(e),
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )

                # Track error rate (we'll need to aggregate this externally for rate calculation)
                goblin_metrics.record_provider_error("worker", type(e).__name__)

                # Legacy error metric
                goblin_metrics.increment(
                    "goblin.mcp.request.errors", tags={"error_type": type(e).__name__}
                )

    def select_provider(self, request: MCPRequest) -> str:
        """Select appropriate provider using intelligent routing."""
        # Convert request to dict for provider manager
        request_data = {
            "task_type": request.task_type,
            "priority": request.priority,
            "provider_hint": getattr(request, "provider_hint", None),
            "prefer_local": getattr(request, "prefer_local", False),
            "prompt": getattr(request, "prompt", ""),
        }

        provider = provider_manager.route_request(request_data)
        return provider or "mock"  # Fallback to mock if no provider available

    async def call_provider(
        self, provider_name: str, request: MCPRequest, context_docs: list
    ) -> Dict[str, Any]:
        """Call the selected provider and return result."""
        provider = provider_manager.get_provider(provider_name)

        if not provider:
            # Fallback to mock response
            return {
                "text": f"Provider {provider_name} not available. Mock response: {getattr(request, 'prompt', 'No prompt')}",
                "provider": "mock",
                "model": "mock-model",
                "tokens": 50,
                "cost_usd": 0.0,
                "latency_ms": 500,
                "error": f"Provider {provider_name} not found",
            }

        # Prepare prompt with context
        prompt = getattr(request, "prompt", "")
        if context_docs:
            context_text = "\n".join(context_docs)
            prompt = f"Context:\n{context_text}\n\nQuestion: {prompt}"

        # Scan for secrets before sending to provider (additional safety layer)
        scanner = SecretScanner()
        secrets_found = scanner.scan_text(prompt)
        if secrets_found:
            # Log security event
            self.log_event(
                request.id,
                "secrets_detected_worker",
                {
                    "secret_count": len(secrets_found),
                    "secret_types": list(set(s["secret_type"] for s in secrets_found)),
                    "action": "request_failed",
                },
            )

            # Track security metrics
            goblin_metrics.increment(
                "goblin.security.secrets_detected",
                tags={"env": os.getenv("ENV", "dev"), "detection_point": "worker_processing"},
            )

            # Return error result
            return {
                "text": f"Request blocked: Contains sensitive information ({len(secrets_found)} potential secrets detected).",
                "provider": provider_name,
                "model": getattr(provider, "model_name", "unknown") if provider else "unknown",
                "tokens": 0,
                "cost_usd": 0.0,
                "latency_ms": 0,
                "error": "SECURITY_VIOLATION",
            }

        # Estimate cost before calling
        estimated_cost = provider.estimate_cost(
            prompt, request.priority * 100
        )  # Rough token estimate

        # Update request with cost estimate
        request.cost_estimate_usd = estimated_cost
        self.db.commit()

        # Publish cost estimate
        self.publish_stream(
            request.id,
            {
                "type": "cost_estimate",
                "estimated_cost_usd": estimated_cost,
                "provider": provider_name,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        # Call provider with circuit breaker protection
        start_time = datetime.utcnow()

        try:
            response = await provider.circuit_breaker.call(
                provider.generate,
                prompt,
                max_tokens=min(
                    request.priority * 100, 4000
                ),  # Scale tokens with priority
                temperature=0.7,
            )

            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            if response.success:
                return {
                    "text": response.content,
                    "provider": provider_name,
                    "model": response.metadata.get("model", "unknown"),
                    "tokens": response.tokens_used,
                    "cost_usd": response.cost_usd,
                    "latency_ms": latency_ms,
                    "metadata": response.metadata,
                }
            else:
                # Provider call failed
                raise Exception(response.error_message)

        except Exception as e:
            # Circuit breaker will handle retries, but we need to return error
            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            return {
                "text": f"Provider {provider_name} failed: {str(e)}",
                "provider": provider_name,
                "model": "error",
                "tokens": 0,
                "cost_usd": 0.0,
                "latency_ms": latency_ms,
                "error": str(e),
            }


async def worker_loop():
    """Main worker loop processing requests from Redis queue."""
    worker = MCPWorker()
    print("MCP Worker started - listening for requests...")

    while True:
        try:
            # Check queue depth and alert if needed
            queue_depth = redis_client.llen("mcp:queue")
            goblin_metrics.record_queue_alert("mcp:queue", queue_depth)

            # Check for queued requests (simple polling - in production use RQ/Celery)
            # For now, we'll use a simple Redis list as queue
            request_id = redis_client.blpop("mcp:queue", timeout=5)

            if request_id:
                request_id = request_id[1]  # blpop returns (queue_name, item)
                print(f"Processing request: {request_id}")
                await worker.process_request(request_id)

        except Exception as e:
            print(f"Worker error: {e}")
            await asyncio.sleep(5)


if __name__ == "__main__":
    # Run the worker
    asyncio.run(worker_loop())
