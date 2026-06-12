"""CSRF token route — clients fetch this before /register or /login."""

from fastapi import APIRouter

from ...core.csrf_manager import generate_csrf_token
from .schemas import CsrfTokenResponse

router = APIRouter()


@router.get("/csrf-token", response_model=CsrfTokenResponse)
async def get_csrf_token():
    """Get a CSRF token for form submissions. Required for /register and /login."""
    token = await generate_csrf_token()
    return CsrfTokenResponse(csrf_token=token)
