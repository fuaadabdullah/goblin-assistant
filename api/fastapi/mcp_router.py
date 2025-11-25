"""
MCP (Model Control Plane) FastAPI router.

This module implements the MCP endpoints for request orchestration,
streaming, and result management.
"""

import os
import uuid
import hashlib
import json
from typing import Optional, Dict, Any, List
from datetime import datetime

import redis
from fastapi import (
    APIRouter,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    Depends,
)
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from mcp_auth import (
    User,
    require_user_or_service,
    require_admin,
    hash_user_id,
    auth_service,
    UserRole,
    get_current_user,
)
from mcp_models import (
    MCPRequest,
    MCPResult,
    MCPEvent,
    get_database_url,
    create_engine_and_session,
)
from ddtrace_config import goblin_tracer as tracer
from mcp_providers import provider_manager
from metrics import metrics as goblin_metrics

# Import Chroma indexer
try:
    from chroma_indexer import ChromaIndexer, SecretScanner
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    ChromaIndexer = None
    SecretScanner = None

# Initialize components
engine, SessionLocal = create_engine_and_session()
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"), port=6379, decode_responses=True
)

# Constants
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))


# Helper functions
def estimate_cost(prompt: str, task_type: str) -> float:
    """Simple cost estimation based on token count."""
    # Rough estimation: ~4 chars per token
    token_estimate = len(prompt) / 4

    # Base rates (simplified)
    rates = {
        "chat": 0.002,  # per 1K tokens
        "code": 0.003,
        "transform": 0.001,
        "workflow": 0.005,
    }

    rate = rates.get(task_type, 0.002)
    return (token_estimate / 1000) * rate


def log_event(db: Session, request_id: str, event_type: str, payload: Dict[str, Any]):
    """Log an event to the database."""
    event = MCPEvent(request_id=request_id, event_type=event_type, payload=payload)
    db.add(event)
    db.commit()


# MCP Router
router = APIRouter(prefix="/mcp/v1", tags=["mcp"])


# Pydantic models for MCP endpoints
class MCPRequestCreate(BaseModel):
    user_id: str = Field(..., description="User identifier")
    prompt: str = Field(..., description="The prompt/text to process")
    task_type: str = Field(
        "chat", description="Task type: chat, code, transform, workflow"
    )
    context_ids: Optional[List[str]] = Field(
        None, description="Context document IDs for RAG"
    )
    prefer_local: bool = Field(True, description="Prefer local models over cloud")
    priority: int = Field(50, description="Priority (0-100, higher = more urgent)")
    provider_hint: Optional[str] = Field(
        None, description="Specific provider preference"
    )


class MCPRequestResponse(BaseModel):
    request_id: str
    status: str
    estimated_cost: float
    message: str


class MCPStatusResponse(BaseModel):
    request_id: str
    status: str
    priority: int
    created_at: datetime
    updated_at: datetime
    last_provider: Optional[str]
    attempts: int
    cost_estimate_usd: Optional[float]


class MCPResultResponse(BaseModel):
    request_id: str
    status: str
    result: Optional[Dict[str, Any]]
    tokens: Optional[int]
    cost_usd: Optional[float]
    finished_at: Optional[datetime]


# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Authentication models
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]


# Authentication endpoints
@router.post("/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Authenticate user and return JWT token."""
    user = auth_service.authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # Create access token
    access_token = auth_service.create_access_token(
        data={"sub": user.username, "role": user.role.value}
    )

    return TokenResponse(
        access_token=access_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user={
            "id": user.id,
            "username": user.username,
            "role": user.role.value,
            "is_active": user.is_active,
        },
    )


@router.get("/auth/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "role": current_user.role.value,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at,
    }


# Admin endpoints
@router.get("/admin/dashboard")
async def get_admin_dashboard(current_user: User = Depends(require_admin)):
    """Get comprehensive admin dashboard data."""
    # Get database stats
    db = SessionLocal()
    try:
        # Request statistics
        total_requests = db.query(MCPRequest).count()
        pending_requests = (
            db.query(MCPRequest).filter(MCPRequest.status == "pending").count()
        )
        running_requests = (
            db.query(MCPRequest).filter(MCPRequest.status == "running").count()
        )
        completed_requests = (
            db.query(MCPRequest).filter(MCPRequest.status == "finished").count()
        )
        failed_requests = (
            db.query(MCPRequest).filter(MCPRequest.status == "failed").count()
        )

        # Cost statistics (last 24 hours)
        from datetime import datetime, timedelta

        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_results = (
            db.query(MCPResult).filter(MCPResult.finished_at >= yesterday).all()
        )
        total_cost_24h = sum(
            result.cost_usd for result in recent_results if result.cost_usd
        )
        total_tokens_24h = sum(
            result.tokens for result in recent_results if result.tokens
        )

        # Provider status
        provider_status = provider_manager.get_all_provider_status()

        # Calculate KPI metrics from recent data
        recent_requests = (
            db.query(MCPRequest).filter(MCPRequest.created_at >= yesterday).all()
        )

        # Calculate p95 latency from recent completed requests
        completed_latencies = []
        for req in recent_requests:
            if req.status == "finished" and req.created_at and req.updated_at:
                latency_ms = (req.updated_at - req.created_at).total_seconds() * 1000
                completed_latencies.append(latency_ms)

        p95_latency = None
        if completed_latencies:
            completed_latencies.sort()
            p95_index = int(len(completed_latencies) * 0.95)
            p95_latency = completed_latencies[
                min(p95_index, len(completed_latencies) - 1)
            ]

        # Calculate error rate
        total_recent = len(recent_requests)
        error_recent = sum(1 for req in recent_requests if req.status == "failed")
        error_rate = (
            (error_recent / max(total_recent, 1)) * 100 if total_recent > 0 else 0
        )

        # Calculate RAG hit rate (requests with context used)
        # Note: This would need actual context tracking in the database
        rag_requests = sum(
            1 for req in recent_requests if getattr(req, "context_ids", None)
        )
        rag_hit_rate = (
            (rag_requests / max(total_recent, 1)) * 100 if total_recent > 0 else 0
        )

        # Calculate fallback rate (mock provider usage)
        fallback_recent = sum(
            1
            for req in recent_requests
            if getattr(req, "last_provider", None) == "mock"
        )
        fallback_rate = (
            (fallback_recent / max(total_recent, 1)) * 100 if total_recent > 0 else 0
        )

        return {
            "system_status": {
                "total_requests": total_requests,
                "pending_requests": pending_requests,
                "running_requests": running_requests,
                "completed_requests": completed_requests,
                "failed_requests": failed_requests,
            },
            "cost_metrics": {
                "total_cost_24h": total_cost_24h,
                "total_tokens_24h": total_tokens_24h,
                "avg_cost_per_request": total_cost_24h / max(completed_requests, 1),
            },
            "kpi_metrics": {
                "p95_latency_ms": p95_latency,
                "error_rate_percent": error_rate,
                "rag_hit_rate_percent": rag_hit_rate,
                "fallback_rate_percent": fallback_rate,
                "total_cost_24h": total_cost_24h,
                "queue_depth": redis_client.llen("mcp:queue"),
                "targets": {
                    "p95_latency_max": 1500,  # 1.5s
                    "error_rate_max": 3.0,  # 3%
                    "rag_hit_rate_min": 60.0,  # 60%
                    "fallback_rate_max": 5.0,  # 5%
                },
            },
            "providers": provider_status,
            "timestamp": datetime.utcnow().isoformat(),
        }
    finally:
        db.close()


@router.post("/admin/providers/{provider_name}/reset-circuit")
async def reset_provider_circuit(
    provider_name: str, current_user: User = Depends(require_admin)
):
    """Reset circuit breaker for a provider."""
    success = provider_manager.reset_circuit_breaker(provider_name)
    if not success:
        raise HTTPException(status_code=404, detail="Provider not found")

    return {"message": f"Circuit breaker reset for provider: {provider_name}"}


@router.get("/admin/requests")
async def get_admin_requests(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(require_admin),
):
    """Get paginated list of requests for admin."""
    db = SessionLocal()
    try:
        query = db.query(MCPRequest)
        if status:
            query = query.filter(MCPRequest.status == status)

        total = query.count()
        requests = (
            query.order_by(MCPRequest.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return {
            "total": total,
            "requests": [
                {
                    "id": req.id,
                    "user_hash": req.user_hash,
                    "status": req.status,
                    "task_type": req.task_type,
                    "priority": req.priority,
                    "last_provider": req.last_provider,
                    "attempts": req.attempts,
                    "cost_estimate_usd": req.cost_estimate_usd,
                    "created_at": req.created_at,
                    "updated_at": req.updated_at,
                }
                for req in requests
            ],
        }
    finally:
        db.close()


# MCP Endpoints
@router.post("/request", response_model=MCPRequestResponse)
async def create_request(
    req: MCPRequestCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user_or_service),
):
    """Submit a new MCP request."""
    with tracer.trace("mcp.create_request") as span:
        span.set_tags(
            {
                "user.hash": hash_user_id(req.user_id),
                "task.type": req.task_type,
                "priority": req.priority,
            }
        )

        # Generate request ID
        request_id = str(uuid.uuid4())

        # Hash user ID for privacy
        user_hash = hash_user_id(req.user_id)

        # Estimate cost
        cost_estimate = estimate_cost(req.prompt, req.task_type)

        # Scan for secrets in the prompt
        if SecretScanner:
            scanner = SecretScanner()
            secrets_found = scanner.scan_text(req.prompt)
            if secrets_found:
                # Log security event
                log_event(
                    db,
                    request_id,
                    "secrets_detected",
                    {
                        "secret_count": len(secrets_found),
                        "secret_types": list(set(s["secret_type"] for s in secrets_found)),
                        "action": "request_blocked",
                    },
                )

                # Emit security metrics
                goblin_metrics.increment(
                    "goblin.security.secrets_detected",
                    tags={"env": os.getenv("ENV", "dev"), "detection_point": "request_creation"},
                )

                # Return error response
                raise HTTPException(
                    status_code=400,
                    detail=f"Request contains sensitive information ({len(secrets_found)} potential secrets detected). Please remove API keys, passwords, or other sensitive data from your request."
                )

        # Create database record
        db_request = MCPRequest(
            id=request_id,
            user_hash=user_hash,
            status="pending",
            task_type=req.task_type,
            priority=req.priority,
            provider_hint=req.provider_hint,
            cost_estimate_usd=cost_estimate,
        )

        db.add(db_request)
        db.commit()

        # Log creation event
        log_event(
            db,
            request_id,
            "request_created",
            {
                "task_type": req.task_type,
                "priority": req.priority,
                "cost_estimate": cost_estimate,
                "context_count": len(req.context_ids) if req.context_ids else 0,
            },
        )

        # Emit metrics
        goblin_metrics.increment(
            "goblin.mcp.request.count",
            tags={"env": os.getenv("ENV", "dev"), "task_type": req.task_type},
        )
        goblin_metrics.gauge("goblin.mcp.cost_estimate_usd", cost_estimate)

        # Queue the request for processing
        redis_client.rpush("mcp:queue", request_id)

        return MCPRequestResponse(
            request_id=request_id,
            status="pending",
            estimated_cost=cost_estimate,
            message="Request queued for processing",
        )


@router.get("/request/{request_id}", response_model=MCPStatusResponse)
async def get_request_status(
    request_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_user_or_service),
):
    """Get request status and metadata."""
    request = db.query(MCPRequest).filter(MCPRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    return MCPStatusResponse(
        request_id=request.id,
        status=request.status,
        priority=request.priority,
        created_at=request.created_at,
        updated_at=request.updated_at,
        last_provider=request.last_provider,
        attempts=request.attempts,
        cost_estimate_usd=request.cost_estimate_usd,
    )


@router.get("/request/{request_id}/result", response_model=MCPResultResponse)
async def get_request_result(
    request_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_user_or_service),
):
    """Get final result for a completed request."""
    request = db.query(MCPRequest).filter(MCPRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    result = db.query(MCPResult).filter(MCPResult.request_id == request_id).first()

    return MCPResultResponse(
        request_id=request.id,
        status=request.status,
        result=result.result if result else None,
        tokens=result.tokens if result else None,
        cost_usd=result.cost_usd if result else None,
        finished_at=result.finished_at if result else None,
    )


@router.post("/cancel/{request_id}")
async def cancel_request(
    request_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_user_or_service),
):
    """Cancel a running request."""
    request = db.query(MCPRequest).filter(MCPRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    if request.status in ["finished", "failed", "cancelled"]:
        raise HTTPException(status_code=400, detail="Request already completed")

    # Update status
    request.status = "cancelled"
    request.updated_at = datetime.utcnow()
    db.commit()

    # Log cancellation
    log_event(db, request_id, "request_cancelled", {"reason": "user_cancelled"})

    # Emit metrics
    goblin_metrics.increment("goblin.mcp.request.cancelled")

    return {"message": "Request cancelled", "request_id": request_id}


@router.websocket("/stream/{request_id}")
async def websocket_stream(websocket: WebSocket, request_id: str):
    """WebSocket endpoint for real-time streaming of request progress."""
    await websocket.accept()

    try:
        # Subscribe to Redis pubsub for this request
        pubsub = redis_client.pubsub()
        pubsub.subscribe(f"mcp:stream:{request_id}")

        # Send initial status
        await websocket.send_json(
            {"type": "status", "request_id": request_id, "status": "connected"}
        )

        # Listen for messages
        while True:
            message = pubsub.get_message(timeout=1.0)
            if message and message["type"] == "message":
                data = json.loads(message["data"])
                await websocket.send_json(data)

                # Check if this is a completion message
                if data.get("type") in ["completed", "error", "cancelled"]:
                    break

    except WebSocketDisconnect:
        # Client disconnected
        pass
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})
    finally:
        pubsub.unsubscribe()
        pubsub.close()


# Admin endpoints (basic)
@router.get("/providers/status")
async def get_provider_status(user: User = Depends(require_user_or_service)):
    """Get status of all MCP providers."""
    return provider_manager.get_all_provider_status()


@router.get("/admin/metrics")
async def get_metrics(user: User = Depends(require_admin)):
    """Get basic MCP metrics."""
    return {
        "requests_pending": 0,  # TODO: Implement actual metrics
        "requests_running": 0,
        "requests_completed": 0,
        "queue_depth": 0,
    }


# Chroma Indexer endpoints
if CHROMA_AVAILABLE:
    # Initialize Chroma indexer (lazy initialization)
    _chroma_indexer = None

    def get_chroma_indexer():
        global _chroma_indexer
        if _chroma_indexer is None:
            _chroma_indexer = ChromaIndexer()
        return _chroma_indexer

    @router.post("/chroma/index")
    async def index_document(
        request: dict,
        user: User = Depends(require_user_or_service)
    ):
        """Index a document with secret scrubbing and embedding."""
        if not CHROMA_AVAILABLE:
            raise HTTPException(status_code=503, detail="ChromaDB not available")

        try:
            content = request.get("content", "")
            metadata = request.get("metadata", {})
            doc_id = request.get("id")

            if not content:
                raise HTTPException(status_code=400, detail="Content is required")

            indexer = get_chroma_indexer()

            # Index the document
            result = indexer.add_documents([content], [metadata], [doc_id])

            return {
                "message": "Document indexed successfully",
                "document_id": result.get("ids", [None])[0] if result.get("ids") else None
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")

    @router.post("/chroma/search")
    async def search_documents(
        request: dict,
        user: User = Depends(require_user_or_service)
    ):
        """Search indexed documents using semantic similarity."""
        if not CHROMA_AVAILABLE:
            raise HTTPException(status_code=503, detail="ChromaDB not available")

        try:
            query = request.get("query", "")
            n_results = request.get("n_results", 5)
            where = request.get("where")  # Optional metadata filter

            if not query:
                raise HTTPException(status_code=400, detail="Query is required")

            indexer = get_chroma_indexer()

            # Search documents
            results = indexer.search(query, n_results=n_results, where=where)

            return {
                "results": results.get("documents", []),
                "metadatas": results.get("metadatas", []),
                "distances": results.get("distances", [])
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

    @router.delete("/chroma/document/{doc_id}")
    async def delete_document(
        doc_id: str,
        user: User = Depends(require_user_or_service)
    ):
        """Delete a document from the index."""
        if not CHROMA_AVAILABLE:
            raise HTTPException(status_code=503, detail="ChromaDB not available")

        try:
            indexer = get_chroma_indexer()
            indexer.delete([doc_id])

            return {"message": f"Document {doc_id} deleted successfully"}

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Deletion failed: {str(e)}")

    @router.get("/chroma/stats")
    async def get_index_stats(user: User = Depends(require_user_or_service)):
        """Get statistics about the Chroma index."""
        if not CHROMA_AVAILABLE:
            raise HTTPException(status_code=503, detail="ChromaDB not available")

        try:
            indexer = get_chroma_indexer()
            count = indexer.count()

            return {
                "total_documents": count,
                "available": True
            }

        except Exception as e:
            return {
                "total_documents": 0,
                "available": False,
                "error": str(e)
            }

    @router.post("/chroma/scan-secrets")
    async def scan_secrets(
        request: dict,
        user: User = Depends(require_user_or_service)
    ):
        """Scan text for secrets without indexing."""
        if not CHROMA_AVAILABLE:
            raise HTTPException(status_code=503, detail="ChromaDB not available")

        try:
            text = request.get("text", "")

            if not text:
                raise HTTPException(status_code=400, detail="Text is required")

            scanner = SecretScanner()
            secrets_found = scanner.scan_text(text)

            return {
                "secrets_found": len(secrets_found) > 0,
                "secret_types": list(set(s["type"] for s in secrets_found)),
                "redacted_text": scanner.redact_text(text)
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Secret scanning failed: {str(e)}")
else:
    # Fallback endpoints when ChromaDB is not available
    @router.get("/chroma/status")
    async def chroma_status():
        """Check ChromaDB availability."""
        return {
            "available": False,
            "message": "ChromaDB dependencies not installed"
        }
