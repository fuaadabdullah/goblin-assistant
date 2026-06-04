"""Chat router package for Goblin Assistant.

Provides conversation management, chat completion endpoints, file uploads,
and SSE streaming. Originally a single 1.6kLOC module; split into topic
submodules for readability while preserving the `api.chat_router.X` import
surface so existing tests and `main.py` continue to work unchanged.

Route submodules read patchable runtime dependencies (invoke_provider,
conversation_store, _require_owned_conversation, InputSanitizer, ...) via
the `_runtime` indirection so that
`monkeypatch.setattr("api.chat_router.X", ...)` in tests is honored even
when the call site lives in a submodule.
"""

import structlog
from fastapi import APIRouter

from ..auth.router import User as AuthenticatedUser

# --- Patchable runtime dependencies ---
# Module-level so tests can monkeypatch via `api.chat_router.<name>`.
from ..auth.router import get_current_user  # noqa: F401
from ..input_validation import InputSanitizer  # noqa: F401
from ..providers.dispatcher import invoke_provider  # noqa: F401
from ..storage import conversation_store  # noqa: F401
from . import contextual as _contextual

# --- Sub-router modules + key handler exports ---
from . import conversations as _conversations
from . import messages as _messages
from . import streaming as _streaming
from . import uploads as _uploads

# --- Constants ---
from .constants import (  # noqa: F401
    ALLOWED_MIME_TYPES,
    MAX_UPLOAD_SIZE_BYTES,
    UPLOAD_DIR,
)
from .contextual import chat_completion  # noqa: F401 — preserved import path

# --- Helpers (re-exported; some are monkeypatched by tests) ---
from .helpers import (  # noqa: F401
    _assert_conversation_owned,
    _extract_usage_and_cost,
    _format_sse_event,
    _latest_snippet,
    _raise_structured_provider_error,
    _require_owned_conversation,
)

# --- Public schemas (re-exported for backward compatibility) ---
from .schemas import (  # noqa: F401
    AttachmentInfo,
    ChatMessage,
    ContextualChatRequest,
    ContextualChatResponse,
    ConversationInfo,
    CreateConversationRequest,
    CreateConversationResponse,
    EstimateTokensResponse,
    FileUploadResponse,
    ImportConversationRequest,
    LayerEstimate,
    SendMessageRequest,
    SendMessageResponse,
    SSEDataEvent,
    SSEErrorEvent,
    StreamChatRequest,
    UpdateConversationTitleRequest,
)

# --- Service accessors (re-exported) ---
from .service_accessors import (  # noqa: F401
    _get_context_assembly_service,
    _get_message_classifier,
    _get_write_time_intelligence,
)
from .streaming import generate_chat_stream  # noqa: F401 — used by tests
from .uploads import _pending_uploads  # noqa: F401 — shared mutable state

logger = structlog.get_logger()

# Compose the top-level router. Each submodule contributes its own
# APIRouter; merging into a single prefixed router keeps the public URL
# space (e.g. /chat/conversations, /chat/stream) unchanged.
router = APIRouter(prefix="/chat", tags=["chat"])
router.include_router(_conversations.router)
router.include_router(_messages.router)
router.include_router(_contextual.router)
router.include_router(_streaming.router)
router.include_router(_uploads.router)
