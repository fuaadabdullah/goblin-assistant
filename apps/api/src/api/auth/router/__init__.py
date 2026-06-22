"""Auth router package.

Provides email/password, Google OAuth, passkey, refresh, logout, CSRF, and
`/me` endpoints, plus the shared `get_current_user` FastAPI dependency.

Originally a single 1.1kLOC module; split into topic submodules while
preserving the `api.auth.router.X` import surface so existing imports and
tests continue to work unchanged.

Route submodules read patchable runtime dependencies (UserService, get_db)
via the `_runtime` indirection so test monkeypatches at
`api.auth.router.X` are honored even from submodule call sites.

Legacy session compatibility helpers were removed at the v0.x -> v1.0 cutoff;
use the async DB-backed helpers from `api.auth.router.sessions` instead.
"""

from __future__ import annotations

import sys
from importlib import import_module
from types import ModuleType

from fastapi import APIRouter

# --- Public re-exports for callers + tests ---
from ...core.csrf_manager import (  # noqa: F401
    generate_csrf_token,
    validate_csrf_token,
)
from ...core.rate_limiter_auth import check_rate_limit  # noqa: F401

# --- Patchable runtime dependencies ---
# Tests monkeypatch these via `api.auth.router.<name>`.
from ...storage.database import get_db, get_readonly_db  # noqa: F401
from ...storage.user_service import UserCreateData, UserService  # noqa: F401

# --- Compose the auth router from sub-routers ---
from . import routes_csrf as _csrf
from . import routes_email as _email
from . import routes_google as _google
from . import routes_passkey as _passkey

_dependencies_module = import_module(".dependencies", __name__)
from .config import (  # noqa: F401
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    REFRESH_TOKEN_EXPIRE_DAYS,
    SECRET_KEY,
)
from .cookies import _clear_auth_cookies, _set_auth_cookies  # noqa: F401
from .dependencies import (  # noqa: F401
    _get_authenticated_user_model,
    _is_user_active,
    get_current_user,
    security,
)
from .passwords import hash_password, verify_password  # noqa: F401
from .schemas import (  # noqa: F401
    GoogleAuthCallback,
    GoogleAuthRequest,
    PasskeyAuthRequest,
    PasskeyRegistrationRequest,
    RefreshTokenRequest,
    Token,
    TokenValidationRequest,
    TokenWithRefresh,
    User,
    UserCreate,
    UserLogin,
)
from .sessions import (  # noqa: F401
    _db_create_session,
    _db_is_session_valid,
    _db_revoke_session,
    _session_cache_key,
    _session_ttl_seconds,
    create_session_id,
)
from .tokens import (  # noqa: F401
    create_access_token,
    create_refresh_token,
    verify_supabase_token,
    verify_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])
router.include_router(_email.router)
router.include_router(_google.router)
router.include_router(_passkey.router)
router.include_router(_csrf.router)


class _DependencyList(list):
    def __getattr__(self, name: str):
        return getattr(_dependencies_module, name)

    def __setattr__(self, name: str, value):
        setattr(_dependencies_module, name, value)


dependencies = _DependencyList(router.dependencies)


class _RouterPackage(ModuleType):
    _SUBMODULE_NAMES = {
        "config",
        "cookies",
        "passwords",
        "routes_csrf",
        "routes_email",
        "routes_google",
        "routes_passkey",
        "schemas",
        "sessions",
        "tokens",
    }

    def __getattribute__(self, name: str):
        if name in _RouterPackage._SUBMODULE_NAMES:
            caller = sys._getframe(1).f_globals.get("__name__", "")
            if caller.startswith("importlib.") or caller.startswith("_frozen_importlib"):
                return import_module(f".{name}", __name__)
        if name == "dependencies":
            return super().__getattribute__(name)
        if name != "router":
            try:
                return getattr(router, name)
            except AttributeError:
                pass
        return super().__getattribute__(name)

    def __setattr__(self, name: str, value):
        if name != "router":
            try:
                setattr(router, name, value)
                return
            except AttributeError:
                pass
        super().__setattr__(name, value)


sys.modules[__name__].__class__ = _RouterPackage
