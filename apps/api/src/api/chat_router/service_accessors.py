"""Lazy accessors for services with heavy or circular import graphs.

These wrap imports inside function bodies so they only fire when a request
handler runs, avoiding import-time cycles at app boot.
"""

from __future__ import annotations

_request_pipeline = None


def _get_context_assembly_service():
    from ..services.context_assembly_service import context_assembly_service

    return context_assembly_service


def _get_message_classifier():
    from ..services.message_classifier import MessageType, message_classifier

    return message_classifier, MessageType


def _get_write_time_intelligence():
    from ..services.write_time_matrix import write_time_intelligence

    return write_time_intelligence


def _get_request_pipeline():
    from ..pipeline import RequestPipeline, tool_selection_model
    from ..routing.intent_classifier import intent_classifier
    from ..services.context_assembly_service import context_assembly_service
    from ..services.smart_router import smart_router

    global _request_pipeline
    if _request_pipeline is None:
        _request_pipeline = RequestPipeline(
            intent_classifier=intent_classifier,
            context_assembly_service=context_assembly_service,
            smart_router=smart_router,
            tool_selection_model=tool_selection_model,
        )
    return _request_pipeline
