"""
Compatibility shim for debugger router — DEPRECATED

This module re-exports the debug suggestion router from api.routes.debug
for backward compatibility. The router has been relocated to reflect
that model routing is core logic, not debugger-specific functionality.

Endpoint has been renamed from /debugger/suggest to /debug/suggest.

Direct imports from this module will be removed in a future release.

New code should import from:
    from api.routes.debug import router as debug_router

This shim will be removed after one release cycle of compatibility window.
See api/routes/debug.py and api/core/router.py for canonical locations.
"""

# Re-export from canonical location
from ..routes.debug import router

__all__ = ["router"]
