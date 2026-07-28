"""
Pydantic request/response models for the main API router.

Extracted from api_router.py to keep the route module focused on
handler logic. Import from here for new code; api_router.py re-exports
all symbols for backward compatibility.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


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
