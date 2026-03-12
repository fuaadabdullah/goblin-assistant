"""
Context Assembly Service — public package interface.

Re‑exports every symbol that callers previously imported from the
single‑file ``context_assembly_service.py``.  No call‑site changes needed.
"""

from .models import ContextBudget, ContextLayer
from .orchestrator import ContextAssemblyService, context_assembly_service

__all__ = [
    "ContextAssemblyService",
    "ContextBudget",
    "ContextLayer",
    "context_assembly_service",
]
