"""Goblin Assistant API Routes Package."""

from .agent import router as agent_router
from .privacy import router as privacy_router

__all__ = ["agent_router", "privacy_router"]
