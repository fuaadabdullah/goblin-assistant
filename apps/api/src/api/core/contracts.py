from __future__ import annotations

from typing import Any, Dict, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


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

