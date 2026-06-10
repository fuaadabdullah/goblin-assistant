"""Messages package — routes and helpers for the send-message pipeline.

Originally a single 877-line module; split into topic submodules for
maintainability while preserving the `api.chat_router.messages.X` import
surface so existing tests and `chat_router/__init__.py` continue to work.
"""

from ...observability.events import event_emitter  # noqa: F401
from ...providers.dispatcher import dispatcher  # noqa: F401
from ...storage.tasks import get_task_store  # noqa: F401
from ...storage.usage_events import get_usage_event_store  # noqa: F401
from ..archiving import schedule_conversation_archive  # noqa: F401
from ..service_accessors import (  # noqa: F401
    _get_context_assembly_service,
    _get_message_classifier,
    _get_request_pipeline,
    _get_write_time_intelligence,
)
from .router import (  # noqa: F401
    estimate_tokens,
    router,
    send_message,
)
