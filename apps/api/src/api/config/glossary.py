"""Glossary registry.

Resolves term → definition pairs into a prompt addendum that is injected
between the base prompt and the mode addendum (see `compose_system_prompt`
in this module for the canonical order).

Sources, in order of precedence (highest first):
    1. Per-request terms passed in via `glossary: dict[str, str]` on the
       chat request — lets the frontend ship a session-scoped glossary
       without round-tripping the database.
    2. Per-user stored terms (`user_glossary`) — defaults to an empty dict
       so the resolver is safe to call before the user record loads.
    3. Global, code-defined terms (`GLOBAL_GLOSSARY` below).

The resolved addendum is always returned as a single string the call site
can concatenate. Empty when no terms resolve, so the composition pipeline
never has to special-case the glossary layer.
"""

from __future__ import annotations

from typing import Dict, Iterable, Mapping, Optional

# Code-defined global glossary. Cheap, stable terms that should be available
# regardless of user state. Keep this short — every term is shipped in every
# response's system prompt and the budget is shared with retrieval layers.
GLOBAL_GLOSSARY: Dict[str, str] = {
    "GoblinOS": "The hybrid local/cloud, multi-provider AI orchestration platform this assistant is embedded in.",
    "Goblin": "The operational intelligence inside GoblinOS — the assistant identity you are speaking to.",
    "context assembly": "The fixed-order retrieval stack (system → profile → long-term → working memory → semantic → ephemeral) that produces the context payload for this response.",
    "phase gate": "A CI-enforced checkpoint (architecture boundaries, cycle detection, contract drift) that must pass before a rollout phase is considered shipped.",
    "provider": "An external LLM backend (OpenAI, Anthropic, Vertex, DashScope, etc.) the dispatcher can route requests to.",
    "department": "A routing target inside GoblinOS that groups providers by capability (reasoning, coding, creative, research).",
}


def _normalize_terms(
    terms: Optional[Mapping[str, str] | Iterable[tuple[str, str]]],
) -> Dict[str, str]:
    """Coerce a mapping or iterable of (term, def) tuples into a clean dict.

    Drops falsy terms/definitions and trims whitespace. Always returns a
    fresh dict so callers can mutate without affecting the input.
    """
    if not terms:
        return {}
    if isinstance(terms, Mapping):
        items = terms.items()
    else:
        items = list(terms)  # type: ignore[arg-type]
    out: Dict[str, str] = {}
    for term, definition in items:
        if term is None or definition is None:
            continue
        term_s = str(term).strip()
        def_s = str(definition).strip()
        if not term_s or not def_s:
            continue
        out[term_s] = def_s
    return out


def resolve_glossary(
    request_glossary: Optional[Mapping[str, str] | Iterable[tuple[str, str]]] = None,
    user_glossary: Optional[Mapping[str, str] | Iterable[tuple[str, str]]] = None,
    include_global: bool = True,
) -> Dict[str, str]:
    """Merge glossary sources into a single term → definition map.

    Precedence: request > user > global. Later sources only fill in
    missing keys; existing definitions are not overwritten.
    """
    merged: Dict[str, str] = {}
    if include_global:
        merged.update(GLOBAL_GLOSSARY)
    merged.update(_normalize_terms(user_glossary))
    merged.update(_normalize_terms(request_glossary))
    return merged


def format_glossary_addendum(
    request_glossary: Optional[Mapping[str, str] | Iterable[tuple[str, str]]] = None,
    user_glossary: Optional[Mapping[str, str] | Iterable[tuple[str, str]]] = None,
    include_global: bool = True,
    max_terms: int = 32,
) -> str:
    """Render the glossary as a prompt addendum.

    Returns an empty string if no terms resolve, so call sites can
    unconditionally concatenate the result. Caps the number of terms at
    `max_terms` to protect the system prompt budget — callers expecting
    more than that should narrow the user glossary upstream.
    """
    terms = resolve_glossary(
        request_glossary=request_glossary,
        user_glossary=user_glossary,
        include_global=include_global,
    )
    if not terms:
        return ""

    ordered = list(terms.items())[:max_terms]
    lines = ["\n[GLOSSARY]"]
    for term, definition in ordered:
        lines.append(f"- {term}: {definition}")
    return "\n".join(lines) + "\n"


def list_global_terms() -> list[str]:
    """Return global glossary term names (stable, sorted)."""
    return sorted(GLOBAL_GLOSSARY.keys())
