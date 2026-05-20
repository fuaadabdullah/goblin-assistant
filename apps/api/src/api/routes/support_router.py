"""
Support message endpoint
Handles user support/feedback submissions
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid

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

@router.post("/message", response_model=SupportResponse)
async def send_support_message(
    request: SupportMessage,
):
    """Submit a support message"""
    try:
        if not request.message or len(request.message.strip()) < 1:
            raise HTTPException(status_code=400, detail="Message is required")
        
        support_id = str(uuid.uuid4())
        
        # In a real implementation, this would:
        # 1. Store in database
        # 2. Send email notification
        # 3. Create ticket in support system
        
        return SupportResponse(
            id=support_id,
            status="received",
            timestamp=datetime.utcnow().isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit support message: {str(e)}")
