"""Backward-compatible auth package exports."""

from importlib import import_module

router = import_module(".router", __name__)

__all__ = ["router"]
