"""Lazy accessors for services with heavy or circular import graphs.

These wrap imports inside function bodies so they only fire when a request
handler runs, avoiding import-time cycles at app boot.
"""


def _get_context_assembly_service():
    from ..services.context_assembly_service import context_assembly_service

    return context_assembly_service


def _get_message_classifier():
    from ..services.message_classifier import MessageType, message_classifier

    return message_classifier, MessageType


def _get_write_time_intelligence():
    from ..services.write_time_matrix import write_time_intelligence

    return write_time_intelligence
