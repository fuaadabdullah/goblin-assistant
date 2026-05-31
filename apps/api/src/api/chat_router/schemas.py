"""Pydantic request/response models for the chat router."""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class StreamEventType(str, Enum):
    TOKEN = "TOKEN"
    TOOL_CALL = "TOOL_CALL"
    TOOL_RESULT = "TOOL_RESULT"
    STATUS = "STATUS"
    ERROR = "ERROR"
    COMPLETE = "COMPLETE"


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
    mode: Optional[str] = None  # e.g. "GENERAL_ASSISTANT", "DEEP_RESEARCH", "DEBUG"


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


class LayerEstimate(BaseModel):
    name: str
    tokens: int


class EstimateTokensResponse(BaseModel):
    input_tokens: int
    estimated_output_tokens: int
    estimated_cost_usd: float
    provider: str
    model: Optional[str] = None
    layers: List[LayerEstimate]
    degraded_mode: bool = False
    degraded_reason: Optional[str] = None


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
    event_type: Optional[StreamEventType] = None
    code: str  # Machine-readable error code
    message: str  # User-friendly error message
    is_recoverable: bool = False  # Whether client can retry
    details: Optional[Dict[str, Any]] = None  # Additional context


class SSEDataEvent(BaseModel):
    """Generic Server-Sent Event data payload"""

    event_type: Optional[StreamEventType] = None
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


class ContextualChatRequest(BaseModel):
    """Request for contextual chat with advanced context assembly"""

    message: str
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    stream: Optional[bool] = False
    metadata: Optional[Dict[str, Any]] = None
    enable_context_assembly: bool = True
    mode: Optional[str] = None  # e.g. "GENERAL_ASSISTANT", "DEEP_RESEARCH", "DEBUG"


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


class StreamChatRequest(BaseModel):
    message: str
    conversation_id: str
    provider: Optional[str] = None
    model: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
