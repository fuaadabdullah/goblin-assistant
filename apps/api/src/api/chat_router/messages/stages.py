"""Pre-dispatch pipeline stage helpers for the send-message route.

Each stage has a single responsibility and an explicit side-effect
contract; the route in `router.py` reads as a high-level orchestration
of these helpers.
"""

from importlib import import_module
from inspect import isawaitable
from typing import Any, Optional

import structlog
from fastapi import HTTPException

from ...config.archetypes import (
    DEEP_RESEARCH_CONTRACT,
    GENERAL_ASSISTANT_CONTRACT,
)
from ...config.archetypes import (
    is_deep_research_mode as _is_deep_research_mode,
)
from ...config.archetypes import (
    is_general_assistant_mode as _is_general_assistant_mode,
)
from ...config.archetypes import (
    missing_deep_research_tools as _missing_deep_research_tools,
)
from ...config.archetypes import (
    missing_general_assistant_tools as _missing_general_assistant_tools,
)
from ...config.mode_addendums import get_addendum as _get_mode_addendum
from ...config.system_prompt import EDUCATION_SYSTEM_ADDENDUM

logger = structlog.get_logger()

# Late-bound package handle so tests can patch package attributes
# (e.g. api.chat_router.messages._get_write_time_intelligence).
_messages_pkg = import_module(__package__)


async def resolve_provider_call(result: Any) -> Any:
    if isawaitable(result):
        return await result
    return result


async def classify_intent(message: str) -> tuple[Any, dict]:
    """Run intent classification; return (result, meta_dict) or (None, {}) on failure."""
    try:
        from api.routing.intent_classifier import intent_classifier as _ic  # noqa: PLC0415

        result = _ic.classify(message)
        return result, result.to_dict()
    except Exception as exc:
        logger.warning("intent_classification_failed", error=str(exc))
        return None, {}


async def run_wti_stage(
    message_id: str,
    content: str,
    conversation: Any,
    conversation_id: str,
    user_id: str,
    metadata: Optional[dict],
    intent_result: Any,
) -> dict:
    """Run Write-Time Intelligence; return populated metadata dict or partial dict on failure."""
    result: dict = {}
    try:
        wti = _messages_pkg._get_write_time_intelligence()
        wti_result = await wti.process_message(
            message_id=message_id,
            content=content,
            role="user",
            user_id=conversation.user_id,
            conversation_id=conversation_id,
            metadata=metadata,
            intent=intent_result,
        )
        classification = wti_result["classification"]
        decision = wti_result["decision"]
        execution = wti_result["execution"]
        result.update(
            {
                "classification": classification,
                "decision": decision,
                "write_time_execution": execution,
                "memory_type": classification["type"],
                "confidence": classification["confidence"],
                "actions_taken": execution["actions_executed"],
                "processed_at": wti_result["processed_at"],
            }
        )
    except Exception as exc:
        logger.error(
            "write_time_intelligence_failed",
            message_id=message_id,
            conversation_id=conversation_id,
            user_id=user_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        result["write_time_error"] = str(exc)
    return result


async def check_usage_quota(user_id: str, conversation_id: str) -> None:
    """Raise HTTP 429 if the user has exceeded daily limits; silently pass on store errors."""
    try:
        usage_store = await _messages_pkg.get_usage_event_store()
        quota = await usage_store.check_limits(user_id)
        if not quota.get("allowed", True):
            raise HTTPException(
                status_code=429,
                detail={
                    "message": "Daily usage limit exceeded",
                    "reason": quota.get("reason"),
                    "usage": quota.get("usage"),
                },
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning(
            "usage_quota_check_failed",
            conversation_id=conversation_id,
            user_id=user_id,
            error=str(exc),
        )


async def resolve_addendum(
    mode: Optional[str],
    new_category: Optional[str],
    intent_meta: dict,
    user_id: str,
    sanitized_message: str,
) -> str:
    """Return the system-prompt addendum for the request."""
    if mode:
        try:
            return _get_mode_addendum(mode)
        except KeyError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    message_classifier, MessageType = _messages_pkg._get_message_classifier()
    classification = message_classifier.classify_message(sanitized_message, "user")
    addendum = (
        EDUCATION_SYSTEM_ADDENDUM if classification.message_type == MessageType.LEARNING else ""
    )

    if new_category:
        try:
            from api.config.mode_addendums import CATEGORY_ADDENDUMS  # noqa: PLC0415

            cat_addendum = CATEGORY_ADDENDUMS.get(new_category, "")
            if cat_addendum:
                addendum = (addendum + "\n\n" + cat_addendum).strip()
        except Exception:
            pass

    try:
        from api.config.mode_addendums import response_length_addendum as _rla  # noqa: PLC0415
        from api.services.preference_learner import preference_learner as _pl  # noqa: PLC0415

        length_pref = await _pl.get_length_pref(str(user_id), intent_meta.get("label", "default"))
        len_addendum = _rla(length_pref)
        if len_addendum:
            addendum = (addendum + "\n\n" + len_addendum).strip()
    except Exception:
        pass

    return addendum


def ensure_mode_required_tools(
    provider: Optional[str],
    mode: Optional[str],
    registered_tools: list,
) -> list:
    """Append archetype-contract tools missing from the intent-based selection.

    The pipeline's tool selector picks a relevance-ranked subset by intent;
    the archetype contracts define the floor a mode must always ship with
    (mode=None ⇒ General Assistant, RESEARCH/DEEP_RESEARCH ⇒ Deep Research).
    Caller is responsible for only invoking this for tool-capable providers.
    """
    contracts = []
    if _is_general_assistant_mode(mode):
        contracts.append(GENERAL_ASSISTANT_CONTRACT)
    if _is_deep_research_mode(mode):
        contracts.append(DEEP_RESEARCH_CONTRACT)
    if not contracts:
        return registered_tools

    present = {
        item.get("function", {}).get("name") for item in registered_tools if isinstance(item, dict)
    }
    required: set = set()
    for contract in contracts:
        required |= contract.required_tool_names
    missing = required - present
    if not missing:
        return registered_tools

    from ...assistant_tools.registry import (  # noqa: PLC0415 — avoid boot-time cycle
        export_tool_specs,
        format_tool_specs_for_provider,
    )

    specs = [spec for spec in export_tool_specs() if spec.name in missing]
    unregistered = missing - {spec.name for spec in specs}
    if unregistered:
        logger.warning(
            "mode_required_tools_unregistered",
            provider=provider,
            mode=mode,
            unregistered_tools=sorted(unregistered),
        )

    return registered_tools + format_tool_specs_for_provider(specs, provider_id=provider)


def log_missing_mode_tools(
    provider: Optional[str],
    mode: Optional[str],
    registered_tools: list,
) -> None:
    """Warn when mode-required tools are absent from the registered tool list."""
    if not registered_tools:
        return
    if _is_general_assistant_mode(mode):
        missing = _missing_general_assistant_tools(registered_tools)
        if missing:
            logger.warning(
                "general_assistant_required_tools_missing",
                provider=provider,
                mode=mode,
                missing_tools=missing,
                registered_tool_count=len(registered_tools),
            )
    if _is_deep_research_mode(mode):
        missing = _missing_deep_research_tools(registered_tools)
        if missing:
            logger.warning(
                "deep_research_required_tools_missing",
                provider=provider,
                mode=mode,
                missing_tools=missing,
                registered_tool_count=len(registered_tools),
            )
