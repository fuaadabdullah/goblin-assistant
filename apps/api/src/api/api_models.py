"""
Pydantic request/response models for the main API router.

Extracted from api_router.py to keep the route module focused on
handler logic. Import from here for new code; api_router.py re-exports
all symbols for backward compatibility.
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from .core.contracts import SuccessEnvelope


class SimpleChatMessage(BaseModel):
    role: str
    content: str


class SimpleChatRequest(BaseModel):
    messages: List[SimpleChatMessage]
    model: Optional[str] = None
    provider: Optional[str] = None
    stream: Optional[bool] = False


class SimpleChatResponse(BaseModel):
    ok: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None


class GenerateRequest(BaseModel):
    messages: Optional[List[SimpleChatMessage]] = None
    prompt: Optional[str] = None
    model: Optional[str] = None
    provider: Optional[str] = None


class GenerateResponse(BaseModel):
    content: Optional[str] = None
    choices: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None


class RouteTaskRequest(BaseModel):
    task_type: str
    payload: Dict[str, Any]
    prefer_local: Optional[bool] = False
    prefer_cost: Optional[bool] = False
    max_retries: Optional[int] = 2
    stream: Optional[bool] = False


class StreamTaskRequest(BaseModel):
    goblin: str
    task: str
    code: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None


class StreamResponse(BaseModel):
    stream_id: str
    status: str = "started"


class ParseOrchestrationRequest(BaseModel):
    text: str
    default_goblin: Optional[str] = None


class GoblinStatus(BaseModel):
    id: str
    name: str
    title: str
    status: Literal["active", "inactive"] = "active"
    active: bool = True
    guild: Optional[str] = None
    description: Optional[str] = None


class GoblinListResponse(BaseModel):
    items: List[GoblinStatus]
    total: int
    limit: int
    order: Literal["catalog_order"] = "catalog_order"


class GoblinHistoryEntry(BaseModel):
    id: str
    goblin_id: str
    task: str
    response: str
    timestamp: datetime
    status: Optional[Literal["completed", "failed"]] = None
    kpis: Optional[str] = None


class GoblinHistoryResponse(BaseModel):
    items: List[GoblinHistoryEntry]
    total: int
    limit: int = Field(ge=1, le=100)
    next_cursor: Optional[str] = None
    order: Literal["newest_first"] = "newest_first"


class GoblinStatsWindow(BaseModel):
    hours: int = Field(ge=1, le=8760)
    started_at: datetime
    ended_at: datetime


class GoblinStatsCounters(BaseModel):
    total_tasks: int
    completed_tasks: Optional[int] = None
    failed_tasks: Optional[int] = None


class GoblinStatsLatency(BaseModel):
    average_duration_ms: Optional[float] = None
    p95_duration_ms: Optional[float] = None


class GoblinStatsResponse(BaseModel):
    goblin_id: str
    window: GoblinStatsWindow
    counters: GoblinStatsCounters
    latency: GoblinStatsLatency
    success_rate: Optional[float] = None
    total_cost: Optional[float] = None


# Named success envelopes — keep schema names stable in OpenAPI docs.
class GoblinListSuccessResponse(SuccessEnvelope[GoblinListResponse]):
    pass


class GoblinHistorySuccessResponse(SuccessEnvelope[GoblinHistoryResponse]):
    pass


class GoblinStatsSuccessResponse(SuccessEnvelope[GoblinStatsResponse]):
    pass
