"""
Support message endpoint
Handles user support/feedback submissions
"""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from api.core.contracts import SuccessEnvelope
from api.core.errors import DomainError

router = APIRouter(prefix="/support", tags=["support"])


class SupportMessage(BaseModel):
    message: str
    email: Optional[str] = None
    category: Optional[str] = None
    attachment_url: Optional[str] = None


class SupportResponse(BaseModel):
    id: str
    status: str
    timestamp: str


@router.post("/message", response_model=SuccessEnvelope[SupportResponse])
async def send_support_message(
    request: SupportMessage,
) -> SuccessEnvelope[SupportResponse]:
    """Submit a support message"""
    try:
        if not request.message or len(request.message.strip()) < 1:
            raise DomainError(
                code="SUPPORT_MESSAGE_REQUIRED",
                message="Message is required",
                status_code=400,
            )

        support_id = str(uuid.uuid4())

        # In a real implementation, this would:
        # 1. Store in database
        # 2. Send email notification
        # 3. Create ticket in support system

        return SuccessEnvelope(
            data=SupportResponse(
                id=support_id,
                status="received",
                timestamp=datetime.utcnow().isoformat(),
            )
        )
    except DomainError:
        raise
    except Exception as e:
        raise DomainError(
            code="SUPPORT_SUBMIT_FAILED",
            message="Failed to submit support message",
            status_code=500,
            details={"reason": str(e)},
        ) from e
