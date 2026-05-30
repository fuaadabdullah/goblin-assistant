from __future__ import annotations

from typing import Any, Dict, Generic, Literal, Optional, TypeAlias, TypeVar

from pydantic import BaseModel, JsonValue

T = TypeVar("T")
EventPayloadT = TypeVar("EventPayloadT", bound=BaseModel | dict[str, JsonValue])

JsonObject: TypeAlias = dict[str, JsonValue]
EventType: TypeAlias = Literal[
    "chat.message.created",
    "provider.health.updated",
    "sandbox.execution.completed",
    "memory.item.promoted",
]


class ApiErrorPayload(BaseModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class SuccessEnvelope(BaseModel, Generic[T]):
    success: bool = True
    data: T


class ErrorEnvelope(BaseModel):
    success: bool = False
    error: ApiErrorPayload


class ChatMessageCreatedPayload(BaseModel):
    conversation_id: str
    message_id: str
    role: str
    provider: Optional[str] = None
    model: Optional[str] = None
    has_attachments: bool = False


class ProviderHealthUpdatedPayload(BaseModel):
    provider_id: str
    status: str
    configured: bool
    healthy: bool
    cache_stale: bool = False
    avg_latency_ms: float = 0.0
    success_rate: float = 1.0
    consecutive_failures: int = 0
    last_error: Optional[str] = None


class SandboxExecutionCompletedPayload(BaseModel):
    job_id: str
    status: str
    language: Optional[str] = None
    exit_code: Optional[int] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    error: Optional[str] = None


class MemoryItemPromotedPayload(BaseModel):
    memory_fact_id: str
    category: str
    source_conversation: str
    source_type: str
    confidence: float
    gates_passed: list[str]


class EventEnvelope(BaseModel, Generic[EventPayloadT]):
    event_id: str
    event_type: EventType
    occurred_at: str
    source: str
    payload: EventPayloadT
    actor_user_id: Optional[str] = None
    correlation_id: Optional[str] = None


class EventLogListResponse(BaseModel):
    events: list[EventEnvelope[JsonObject]]
    total: int
