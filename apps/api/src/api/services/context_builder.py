"""
Context builder utilities for semantic retrieval prompts.

This module provides:
- Async instance API (`ContextBuilder`) for new call sites.
- Legacy synchronous API (`LegacyContextBuilder`) for compatibility.
"""

from typing import Any, Dict, List, Optional

from ..config.system_prompt import system_prompt_manager


def _build_financial_profile_block(context_bundle: Dict[str, Any]) -> Optional[str]:
    fin_profile = context_bundle.get("financial_profile")
    if not fin_profile:
        return None

    profile_lines: List[str] = []
    if fin_profile.get("watched_tickers"):
        watched = ", ".join(fin_profile["watched_tickers"])
        profile_lines.append(f"Watched tickers: {watched}")
    if fin_profile.get("last_dcf_assumptions"):
        assumptions = fin_profile["last_dcf_assumptions"]
        profile_lines.append(
            f"Last DCF assumptions: ticker={assumptions.get('ticker', '?')}, "
            f"WACC={assumptions.get('wacc', 0) * 100:.1f}%, "
            f"growth={assumptions.get('growth_rate', 0) * 100:.1f}%"
        )
    if fin_profile.get("portfolio_snapshot"):
        profile_lines.append(f"Portfolio: {fin_profile['portfolio_snapshot']}")
    if fin_profile.get("risk_snapshot"):
        profile_lines.append(f"Risk: {fin_profile['risk_snapshot']}")

    if not profile_lines:
        return None
    return "[FINANCIAL PROFILE] " + " | ".join(profile_lines)


def _build_context_text(
    context_bundle: Dict[str, Any],
    max_context_tokens: int,
) -> str:
    context_parts: List[str] = []

    # Priority order: summaries -> long-term memory -> vector messages -> ephemeral -> tasks.
    for summary in context_bundle.get("summaries", []):
        context_parts.append(f"[SUMMARY] {summary['content']}")

    for fact in context_bundle.get("memory_facts", []):
        memory_type = fact.get("memory_type") or fact.get("metadata", {}).get("memory_type")
        label = f"[MEMORY:{memory_type}]" if memory_type else "[MEMORY]"
        context_parts.append(f"{label} {fact['content']}")

    profile_block = _build_financial_profile_block(context_bundle)
    if profile_block:
        context_parts.append(profile_block)

    for message in context_bundle.get("messages", []):
        context_parts.append(f"[MESSAGE] {message['content']}")

    for message in context_bundle.get("ephemeral_messages", []):
        context_parts.append(f"[EPHEMERAL] {message['content']}")

    for task in context_bundle.get("tasks", []):
        context_parts.append(f"[TASK] {task['content']}")

    context_text = "\n\n".join(context_parts)

    max_chars = max_context_tokens * 4
    if len(context_text) > max_chars:
        context_text = context_text[:max_chars]

    return context_text


def _build_system_prompt(
    user_message: str,
    context_text: str,
    conversation_history: List[Dict[str, str]],
    system_prompt_override: Optional[str],
) -> str:
    if system_prompt_override is not None:
        if context_text:
            system_prompt = f"{system_prompt_override}\n\nContext:\n{context_text}"
        else:
            system_prompt = system_prompt_override
    else:
        system_prompt = system_prompt_manager.config.get_prompt_with_context(context_text)

    system_prompt += "\n\nConversation history:\n"
    for msg in conversation_history[-5:]:
        system_prompt += f"{msg['role']}: {msg['content']}\n"

    system_prompt += f"user: {user_message}"
    return system_prompt


def build_contextual_prompt_sync(
    user_message: str,
    context_bundle: Dict[str, Any],
    conversation_history: List[Dict[str, str]],
    max_context_tokens: int = 1500,
    system_prompt_override: Optional[str] = None,
) -> List[Dict[str, str]]:
    context_text = _build_context_text(context_bundle, max_context_tokens)
    system_prompt = _build_system_prompt(
        user_message=user_message,
        context_text=context_text,
        conversation_history=conversation_history,
        system_prompt_override=system_prompt_override,
    )
    return [{"role": "system", "content": system_prompt}]


class ContextBuilder:
    """Async contextual prompt builder for RAG callers."""

    async def build_contextual_prompt(
        self,
        user_id: str,
        context_bundle: Dict[str, Any],
        user_message: str,
        conversation_history: List[Dict[str, str]],
        max_context_tokens: int = 1500,
        system_prompt_override: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        del user_id  # Reserved for future user-specific prompt variants.
        return build_contextual_prompt_sync(
            user_message=user_message,
            context_bundle=context_bundle,
            conversation_history=conversation_history,
            max_context_tokens=max_context_tokens,
            system_prompt_override=system_prompt_override,
        )


class LegacyContextBuilder:
    """Compatibility layer preserving synchronous call sites."""

    @staticmethod
    def build_contextual_prompt(
        user_message: str,
        context_bundle: Dict[str, Any],
        conversation_history: List[Dict[str, str]],
        max_context_tokens: int = 1500,
        system_prompt_override: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        return build_contextual_prompt_sync(
            user_message=user_message,
            context_bundle=context_bundle,
            conversation_history=conversation_history,
            max_context_tokens=max_context_tokens,
            system_prompt_override=system_prompt_override,
        )
