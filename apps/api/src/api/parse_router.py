from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .core.orchestration import OrchestrationPlan, parse_natural_language

router = APIRouter(prefix="/parse", tags=["parse"])


class ParseRequest(BaseModel):
    text: str
    default_goblin: Optional[str] = None


@router.post("/", response_model=OrchestrationPlan)
async def parse_orchestration(request: ParseRequest):
    """Parse natural language text into an orchestration plan"""
    try:
        return parse_natural_language(request.text, request.default_goblin)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse orchestration: {str(e)}")
