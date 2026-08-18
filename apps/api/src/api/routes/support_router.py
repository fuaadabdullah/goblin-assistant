"""
Support message endpoint
Handles user support/feedback submissions and beta confusion signals.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.contracts import SuccessEnvelope
from api.core.errors import DomainError
from api.storage.database import get_db
from api.storage.saas_service import SaaSSettingsService
from api.storage.user_service import UserService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/support", tags=["support"])

_CATEGORY_SUBJECTS = {
    "bug": "Bug",
    "feature": "Feature Request",
    "account": "Account",
    "billing": "Billing",
    "other": "Other",
}


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
    name: Optional[str] = None
    email: Optional[str] = None
    note: Optional[str] = None
    tag: Optional[str] = None


@router.post("/message")
async def send_support_message(
    request: SupportMessageBody,
    db: AsyncSession = Depends(get_db),
) -> SuccessEnvelope:
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

    svc = SaaSSettingsService(db)
    user_svc = UserService(db)

    # Try to link the ticket to an existing user
    user_id = None
    if request.email:
        existing_user = await user_svc.get_user_by_email(request.email)
        if existing_user:
            user_id = existing_user.id

    subject = _CATEGORY_SUBJECTS.get(request.category or "", request.category or "Support")
    if request.category and request.category not in _CATEGORY_SUBJECTS:
        subject = request.category.capitalize()

    try:
        ticket = await svc.create_support_ticket({
            "user_id": user_id,
            "email": request.email,
            "category": request.category,
            "status": "received",
            "subject": subject,
            "message": request.message,
            "attachment_url": request.attachment_url,
            "metadata": {"source": "support_form"},
        })

        if user_id:
            await svc.create_notification({
                "user_id": user_id,
                "title": "Support request received",
                "body": f"Your {request.category or 'support'} request has been received.",
                "category": "support",
                "metadata": {
                    "source": "support_form",
                    "support_ticket_id": ticket.ticket_id,
                    "support_category": request.category,
                },
            })

        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise DomainError(
            code="SUPPORT_SUBMIT_FAILED",
            message="Failed to submit support request",
            status_code=500,
            details={"reason": str(exc)},
        ) from exc

    return SuccessEnvelope(data=SupportResponse(
        id=ticket.ticket_id,
        status="received",
        timestamp=datetime.now(timezone.utc).isoformat(),
    ))


@router.post("/beta-signal", response_model=SupportResponse)
async def submit_beta_signal(
    body: BetaSignalBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> SupportResponse:
    """Capture a confusion or friction moment from a beta user."""
    signal_id = str(uuid.uuid4())
    user_agent = request.headers.get("user-agent", "")[:120]
    subject = f"Pilot signal: {body.tag or body.page}"
    message = body.note.strip() if body.note and body.note.strip() else f"Confusion on {body.page}"

    try:
        svc = SaaSSettingsService(db)
        await svc.create_support_ticket({
            "category": "beta_signal",
            "status": "received",
            "subject": subject,
            "message": message,
            "email": body.email,
            "metadata": {
                "source": "beta_signal",
                "page": body.page,
                "tag": body.tag,
                "name": body.name,
                "email": body.email,
                "user_agent": user_agent,
            },
        })
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise DomainError(
            code="BETA_SIGNAL_SUBMIT_FAILED",
            message="Failed to submit beta signal",
            status_code=500,
            details={"reason": str(exc)},
        ) from exc

    logger.info(
        "beta_confusion_signal",
        signal_id=signal_id,
        page=body.page,
        note=body.note or "",
        tag=body.tag or "",
        name=body.name or "",
        email=body.email or "",
        user_agent=user_agent,
    )

    return SupportResponse(
        id=signal_id,
        status="logged",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
