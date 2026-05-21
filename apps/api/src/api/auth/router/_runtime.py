"""Late-bound accessor for symbols tests monkeypatch at `api.auth.router.X`.

Route + helper submodules read patchable runtime dependencies (UserService,
get_db, ...) through this module so that
`monkeypatch.setattr("api.auth.router.X", ...)` is honored even when the
call site lives in a submodule.

Each attribute access re-reads `sys.modules['api.auth.router']`, so patches
applied after import are picked up.
"""

import sys


def __getattr__(name):
    pkg = sys.modules.get("api.auth.router")
    if pkg is None:
        raise AttributeError(name)
    return getattr(pkg, name)
