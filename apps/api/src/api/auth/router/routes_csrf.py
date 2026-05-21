"""CSRF token route — clients fetch this before /register or /login."""

from fastapi import APIRouter

from ...core.csrf_manager import generate_csrf_token

router = APIRouter()


@router.get("/csrf-token")
async def get_csrf_token():
    """Get a CSRF token for form submissions. Required for /register and /login."""
    token = await generate_csrf_token()
    return {"csrf_token": token}
