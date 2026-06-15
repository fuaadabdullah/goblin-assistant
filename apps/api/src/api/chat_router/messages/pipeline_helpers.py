"""Small helpers for the chat message pipeline."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from ...providers.dispatcher import canonical_provider_id, dispatcher


def resolve_provider_id(requested: Optional[str]) -> Optional[str]:
    """Mirror dispatcher provider selection so estimates match the real send."""
    candidates = dispatcher._candidate_order(requested)
    return candidates[0] if candidates else None


def provider_supports_tools(provider_id: Optional[str]) -> bool:
    """Check whether the resolved provider advertises OpenAI-tool support."""
    if provider_id is None:
        return True
    resolved = canonical_provider_id(provider_id)
    if not resolved:
        return True
    config = dispatcher._configs.get(resolved, {})
    value = config.get("supports_openai_tools")
    return value is not False


def merge_attachment_metadata(
    *,
    current_user_id: str,
    attachment_ids: list[str] | None,
    pending_uploads: Dict[str, Dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Collect attachment metadata and the corresponding upload sources."""
    attachments_meta: list[dict[str, Any]] = []
    attachment_context_sources: list[dict[str, Any]] = []
    if not attachment_ids:
        return attachments_meta, attachment_context_sources

    for aid in attachment_ids:
        upload = pending_uploads.pop(aid, None)
        if upload and upload["user_id"] == current_user_id:
            attachment_context_sources.append(upload)
            attachments_meta.append(
                {
                    "id": upload["file_id"],
                    "filename": upload["filename"],
                    "mime_type": upload["mime_type"],
                    "size_bytes": upload["size_bytes"],
                    "pdf_extraction_status": upload.get("pdf_extraction_status"),
                    "pdf_warnings": upload.get("warnings", []),
                }
            )
    return attachments_meta, attachment_context_sources


def normalize_provider_response(
    provider_response: Any,
    request_provider: Optional[str],
    request_model: Optional[str],
) -> Tuple[str, str, str]:
    """Return (content, used_provider, used_model) from a dispatcher response."""
    provider = request_provider or "unknown"
    model = request_model or "unknown"

    # OpenAI-compatible format
    if isinstance(provider_response, dict) and "choices" in provider_response:
        return (
            provider_response["choices"][0]["message"]["content"],
            provider_response.get("provider", provider),
            provider_response.get("model", model),
        )

    # LiteLLM/other format with 'ok' flag
    if isinstance(provider_response, dict) and provider_response.get("ok"):
        return (
            provider_response.get("result", {}).get("text", ""),
            provider_response.get("provider", provider),
            provider_response.get("model", model),
        )

    # Fallback: JSON-serialize dicts, stringify primitives
    import json

    content = ""
    if isinstance(provider_response, dict):
        try:
            content = json.dumps(provider_response)
        except (TypeError, ValueError):
            content = str(provider_response) or ""
    elif provider_response:
        content = str(provider_response)

    return content, provider, model
