from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .core.orchestration import OrchestrationPlan, parse_natural_language

router = APIRouter(prefix="/parse", tags=["parse"])


def _detail_message(prefix: str, error: Exception) -> str:
    message = str(error).strip()
    if message:
        return f"{prefix}: {message}"
    return f"{prefix}: Request failed"


class ParseRequest(BaseModel):
    text: str
    default_goblin: Optional[str] = None


@router.post("/", response_model=OrchestrationPlan)
async def parse_orchestration(request: ParseRequest):
    """Parse natural language text into an orchestration plan"""
    try:
        return parse_natural_language(request.text, request.default_goblin)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=_detail_message("Failed to parse orchestration", e),
        )
