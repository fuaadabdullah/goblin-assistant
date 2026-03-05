"""
Compatibility shim for model_router — DEPRECATED

This module re-exports from api.core.router for backward compatibility.
Direct imports from this module will be removed in a future release.

New code should import directly from api.core.router:
    from api.core.router import ModelRouter, ModelRoute, RAPTOR_TASKS

This shim will be removed after one release cycle of compatibility window.
See api/core/router.py and api/routes/debug.py for canonical locations.
"""

# Re-export from canonical location
from ..core.router import RAPTOR_TASKS, ModelRoute, ModelRouter

__all__ = ["RAPTOR_TASKS", "ModelRoute", "ModelRouter"]
