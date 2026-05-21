"""Late-bound accessor for symbols the tests monkeypatch at `api.chat_router.X`.

Route submodules read patchable runtime dependencies (invoke_provider,
_require_owned_conversation, etc.) through this module so that
`monkeypatch.setattr("api.chat_router.invoke_provider", ...)` is honored
even when the call site lives in a submodule.

Each attribute lookup re-reads `sys.modules['api.chat_router']`, so patches
applied after import are picked up.
"""

import sys


def __getattr__(name):
    pkg = sys.modules.get("api.chat_router")
    if pkg is None:
        raise AttributeError(name)
    return getattr(pkg, name)
