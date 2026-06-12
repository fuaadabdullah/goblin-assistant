"""Department decision layer — hides provider plumbing behind functional departments.

Each department represents a functional specialization of the "brain":
REASONING, CODING, CREATIVE, RECALL, TOOL_USE, RESEARCH, GENERAL.

Users interact with departments, never with raw provider names.
"""

from .dispatcher import DepartmentDispatcher, department_dispatcher
from .models import (
    DepartmentId,
    DepartmentPolicy,
    DepartmentSelection,
    DepartmentSpecialization,
)
from .registry import DEPARTMENT_REGISTRY
from .router import DepartmentRouter, classify_department

__all__ = [
    "DepartmentDispatcher",
    "department_dispatcher",
    "DepartmentId",
    "DepartmentPolicy",
    "DepartmentRouter",
    "DepartmentSelection",
    "DepartmentSpecialization",
    "DEPARTMENT_REGISTRY",
    "classify_department",
]
