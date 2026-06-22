"""Sentry SDK context helpers — side-effect boundary module."""

from typing import Optional


def set_sentry_chat_context(
    *,
    conversation_id: str,
    user_id: str,
    provider: Optional[str],
    model: Optional[str],
) -> None:
    """Set Sentry tags and context for the current chat operation.

    This is an explicit side-effect boundary: calling this function triggers
    Sentry SDK calls. Failures are silently caught — Sentry context must
    never affect chat delivery.
    """
    try:
        import sentry_sdk  # noqa: PLC0415

        sentry_sdk.set_tag("conversation_id", conversation_id)
        sentry_sdk.set_tag("operation", "chat.send_message")
        if provider:
            sentry_sdk.set_tag("provider_requested", provider)
        if model:
            sentry_sdk.set_tag("model_requested", model)
        sentry_sdk.set_context(
            "chat",
            {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "provider": provider,
                "model": model,
            },
        )
        sentry_sdk.set_transaction_name(
            "POST /api/v1/chat/conversations/{conversation_id}/messages"
        )
    except Exception:
        return
