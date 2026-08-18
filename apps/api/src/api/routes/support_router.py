"""
Support message endpoint
Handles user support/feedback submissions and beta confusion signals.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from fastapi import APIRouter, HTTPException, Request

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/support", tags=["support"])


class SupportMessage:
    def __init__(
        self,
        message: str,
        email: Optional[str] = None,
        category: Optional[str] = None,
        attachment_url: Optional[str] = None,
    ):
        self.message = message
        self.email = email
        self.category = category
        self.attachment_url = attachment_url


from pydantic import BaseModel  # noqa: E402


class SupportMessageBody(BaseModel):
    message: str
    email: Optional[str] = None
    category: Optional[str] = None
    attachment_url: Optional[str] = None


class SupportResponse(BaseModel):
    id: str
    status: str
    timestamp: str


class BetaSignalBody(BaseModel):
    page: str
    note: Optional[str] = None
    tag: Optional[str] = None  # e.g. "what-is-goblin", "too-slow", "model-unclear"


@router.post("/message", response_model=SupportResponse)
async def send_support_message(request: SupportMessageBody) -> SupportResponse:
    """Submit a support message."""
    if not request.message or len(request.message.strip()) < 1:
        raise HTTPException(status_code=400, detail="Message is required")

    support_id = str(uuid.uuid4())
    logger.info(
        "support_message_received",
        support_id=support_id,
        category=request.category,
        has_email=bool(request.email),
    )
    return SupportResponse(
        id=support_id,
        status="received",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/beta-signal", response_model=SupportResponse)
async def submit_beta_signal(body: BetaSignalBody, request: Request) -> SupportResponse:
    """
    Capture a confusion or friction moment from a beta user.

    Called by the floating '?' widget when a user taps it.
    Logged to structlog so the beta week's confusion map can be grepped
    from server logs:  grep 'beta_confusion_signal' <log-file>
    """
    signal_id = str(uuid.uuid4())
    user_agent = request.headers.get("user-agent", "")[:120]

    logger.info(
        "beta_confusion_signal",
        signal_id=signal_id,
        page=body.page,
        note=body.note or "",
        tag=body.tag or "",
        user_agent=user_agent,
    )

    return SupportResponse(
        id=signal_id,
        status="logged",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
