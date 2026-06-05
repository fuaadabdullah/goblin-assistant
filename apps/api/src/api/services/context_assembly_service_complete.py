"""
Compatibility wrapper for the modular context assembly package.

The old single-file implementation has been replaced by
``api.services.context_assembly_service``. Keep this module as a thin alias so
any stale imports continue to work without carrying the monolith forward.
"""

from .context_assembly_service import ContextAssemblyService, ContextBudget, ContextLayer
from .context_assembly_service import context_assembly_service

context_assembly_service_complete = context_assembly_service

__all__ = [
    "ContextAssemblyService",
    "ContextBudget",
    "ContextLayer",
    "context_assembly_service",
    "context_assembly_service_complete",
]
