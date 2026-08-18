"""Pydantic request/response models for the chat router."""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, field_validator, model_validator

from ..config.mode_addendums import MODE_REGISTRY, Mode, ModeKey
from ..config.tone_addendums import ToneMode


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
    department: Optional[str] = None  # e.g. "reasoning", "coding", "creative", "research"
    stream: Optional[bool] = False
    metadata: Optional[Dict[str, Any]] = None
    enable_context_assembly: Optional[bool] = True  # Inject RAG context like contextual-chat
    attachment_ids: Optional[List[str]] = None  # IDs from /chat/upload-file
    mode: Mode = Mode.CHAT  # canonical v2 mode; active-gated at validation time
    legacy_mode: Optional[ModeKey] = (
        None  # overrides auto-detection; exported via OpenAPI → SDK codegen
    )
    tone: Optional[ToneMode] = None  # voice register; DEFAULT/None = no addendum
    glossary: Optional[Dict[str, str]] = None  # Session-scoped term overrides
    language: Optional[str] = (
        None  # e.g. "python", "javascript" — hints code language for glossary injection
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_mode_payload(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        raw_mode = data.get("mode")
        if not isinstance(raw_mode, str):
            return data

        legacy_map = {
            "GENERAL_ASSISTANT": ModeKey.GENERAL_ASSISTANT,
            "ARCHITECT": ModeKey.ARCHITECT,
            "TRADING_FORGE": ModeKey.TRADING_FORGE,
            "OPERATOR": ModeKey.OPERATOR,
            "RESEARCH": ModeKey.RESEARCH,
            "DEEP_RESEARCH": ModeKey.DEEP_RESEARCH,
            "DEBUG": ModeKey.DEBUG,
            "CODE_REVIEW": ModeKey.CODE_REVIEW,
            "EDUCATION": ModeKey.EDUCATION,
        }
        legacy_mode = legacy_map.get(raw_mode.strip().upper())
        if legacy_mode is None:
            return data

        updated = dict(data)
        updated["legacy_mode"] = updated.get("legacy_mode") or legacy_mode
        updated["mode"] = Mode.CHAT
        return updated

    @field_validator("mode")
    @classmethod
    def mode_must_be_active(cls, v: Mode) -> Mode:
        if not MODE_REGISTRY[v].active:
            raise ValueError(f"mode '{v.value}' is not yet active")
        return v


class SendMessageResponse(BaseModel):
    message_id: str
    response: str
    provider: Optional[str] = None
    model: Optional[str] = None
    department: Optional[str] = None
    department_reason: Optional[str] = None
    timestamp: str
    usage: Optional[Dict[str, Any]] = None
    cost_usd: Optional[float] = None
    correlation_id: Optional[str] = None
    visualizations: Optional[List[Dict[str, Any]]] = None


class LayerEstimate(BaseModel):
    """Token estimate for a single context-assembly layer."""

    name: str
    tokens: int


class EstimateTokensResponse(BaseModel):
    """Estimated token/cost breakdown for a chat request."""

    input_tokens: int
    estimated_output_tokens: int
    estimated_cost_usd: float
    department: str = "general"
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
    category: Optional[str] = None


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
    department: Optional[str] = None  # Which department handled this
    department_reason: Optional[str] = None
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
    provider: Optional[str] = None  # None = let dispatcher choose
    model: Optional[str] = None  # None = use provider default
    department: Optional[str] = None  # e.g. "reasoning", "coding", "creative", "research"
    stream: Optional[bool] = False
    metadata: Optional[Dict[str, Any]] = None
    enable_context_assembly: bool = True
    mode: Mode = Mode.CHAT  # canonical v2 mode; active-gated at validation time
    legacy_mode: Optional[ModeKey] = (
        None  # overrides auto-detection; exported via OpenAPI → SDK codegen
    )
    tone: Optional[ToneMode] = None  # Voice/register override. None → DEFAULT.
    glossary: Optional[Dict[str, str]] = None  # Session-scoped term overrides

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_mode_payload(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        raw_mode = data.get("mode")
        if not isinstance(raw_mode, str):
            return data

        legacy_map = {
            "GENERAL_ASSISTANT": ModeKey.GENERAL_ASSISTANT,
            "ARCHITECT": ModeKey.ARCHITECT,
            "TRADING_FORGE": ModeKey.TRADING_FORGE,
            "OPERATOR": ModeKey.OPERATOR,
            "RESEARCH": ModeKey.RESEARCH,
            "DEEP_RESEARCH": ModeKey.DEEP_RESEARCH,
            "DEBUG": ModeKey.DEBUG,
            "CODE_REVIEW": ModeKey.CODE_REVIEW,
            "EDUCATION": ModeKey.EDUCATION,
        }
        legacy_mode = legacy_map.get(raw_mode.strip().upper())
        if legacy_mode is None:
            return data

        updated = dict(data)
        updated["legacy_mode"] = updated.get("legacy_mode") or legacy_mode
        updated["mode"] = Mode.CHAT
        return updated

    @field_validator("mode")
    @classmethod
    def mode_must_be_active(cls, v: Mode) -> Mode:
        if not MODE_REGISTRY[v].active:
            raise ValueError(f"mode '{v.value}' is not yet active")
        return v


class ContextualChatResponse(BaseModel):
    """Response for contextual chat with context assembly details"""

    message_id: str
    response: str
    department: str  # Which brain department handled this
    department_reason: str = ""
    timestamp: str
    context_assembly: Optional[Dict[str, Any]] = None
    token_usage: Optional[Dict[str, Any]] = None
    visualizations: Optional[List[Dict[str, Any]]] = None


class StreamChatRequest(BaseModel):
    message: str
    conversation_id: str
    provider: Optional[str] = None  # None = let dispatcher choose
    model: Optional[str] = None  # None = use provider default
    department: Optional[str] = None  # e.g. "reasoning", "coding", "creative", "research"
    metadata: Optional[Dict[str, Any]] = None
    mode: Mode = Mode.CHAT
    tone: Optional[ToneMode] = None  # Voice/register override. None → DEFAULT.
    glossary: Optional[Dict[str, str]] = None  # Session-scoped term overrides
