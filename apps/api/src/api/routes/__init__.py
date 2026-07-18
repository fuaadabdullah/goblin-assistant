"""Goblin Assistant API Routes Package.

Submodules are imported lazily (PEP 562) so that importing one router does not
eagerly pull in every other router's dependency graph.
"""

__all__ = ["agent_router", "privacy_router"]

_LAZY_EXPORTS = {
    "agent_router": ("agent", "router"),
    "privacy_router": ("privacy", "router"),
}


def __getattr__(name):
    if name in _LAZY_EXPORTS:
        import importlib

        module_name, attr = _LAZY_EXPORTS[name]
        module = importlib.import_module(f".{module_name}", __name__)
        return getattr(module, attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
