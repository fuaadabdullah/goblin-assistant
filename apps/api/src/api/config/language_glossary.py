"""Language-aware glossary injection for code help contexts.

Detects the programming language from message content and injects
language-specific term definitions into the system prompt addendum
to improve code review and debugging quality.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

# ── Language-specific glossaries ────────────────────────────────────────────
# Each entry maps a term → brief definition. Entries are kept intentionally
# short (one line) to preserve system prompt budget — at most 8 terms are
# injected per request.

_PYTHON_GLOSSARY: Dict[str, str] = {
    "PEP 8": "Python's official style guide; 4-space indentation, 79-char lines.",
    "dunder": "Double-underscore methods like __init__, __str__, __repr__.",
    "type hints": "Optional static type annotations (def foo(x: int) -> str).",
    "context manager": "with-statement protocol (__enter__ / __exit__).",
    "list comprehension": "Concise list-creation syntax: [x for x in iterable if ...].",
    "decorator": "Function wrapper syntax: @decorator above a def.",
    "asyncio": "Python's async/await event-loop library for concurrent I/O.",
    "f-string": "Inline string formatting: f'Hello {name}'.",
    "iterator": "Object implementing __next__ and __iter__; consumed once.",
    "generator": "Function using yield; produces an iterator lazily.",
}

_JAVASCRIPT_GLOSSARY: Dict[str, str] = {
    "Promise": "Object representing eventual completion/failure of an async operation.",
    "async/await": "Syntactic sugar over Promises for writing async code synchronously.",
    "closure": "Function that retains access to its lexical scope even when invoked outside it.",
    "hoisting": "Variable and function declarations moved to top of scope at parse time.",
    "event loop": "Runtime model where the engine processes a queue of callbacks/microtasks.",
    "destructuring": "Unpacking syntax: const { a, b } = obj or const [x, y] = arr.",
    "arrow function": "Concise function syntax: (x) => x + 1; lexical this binding.",
    "strict mode": "'use strict' — enables stricter parsing and error handling.",
    "prototype": "Object from which another object inherits properties.",
    "module": "ES module (import/export) or CommonJS (require/module.exports).",
}

_TYPESCRIPT_GLOSSARY: Dict[str, str] = {
    "interface": "Structural contract for object shapes (interface Foo { ... }).",
    "type alias": "Named reusable type: type Foo = string | number.",
    "generic": "Parameterized type: function foo<T>(x: T): T.",
    "type guard": "Runtime check that narrows a union type (typeof, instanceof, is).",
    "strict mode": "Compiler flag enabling noImplicitAny, strictNullChecks, etc.",
    "enum": "Named constant set: enum Color { Red, Green, Blue }.",
    "union type": "Value can be one of several types: string | number.",
    "assertion": "as Type or <Type> cast; bypasses compiler checks.",
}

_GENERAL_CODE_GLOSSARY: Dict[str, str] = {
    "refactor": "Restructure code without changing external behavior.",
    "lint": "Static analysis tool that flags style and potential bugs.",
    "unit test": "Test that verifies a single function/class in isolation.",
    "integration test": "Test that verifies multiple components work together.",
    "regression": "Bug where previously working functionality breaks.",
    "DRY": "Don't Repeat Yourself — extract duplicated logic.",
    "SOLID": "Five OOP design principles (Single Responsibility, Open/Closed, etc.).",
    "CI/CD": "Continuous Integration / Continuous Deployment pipeline.",
}

# ── Language detection ──────────────────────────────────────────────────────


def _extract_fenced_languages(message: str) -> List[str]:
    """Return language identifiers from fenced code blocks (```lang ... ```)."""
    pattern = r"```(\w+)"
    matches = re.findall(pattern, message)
    # Normalize common aliases
    alias_map = {
        "py": "python",
        "python3": "python",
        "js": "javascript",
        "node": "javascript",
        "ts": "typescript",
        "typescript": "typescript",
        "bash": "bash",
        "sh": "bash",
        "shell": "bash",
        "zsh": "bash",
    }
    return [alias_map.get(m.lower(), m.lower()) for m in matches]


def _keyword_score(message: str) -> Dict[str, int]:
    """Score languages by keyword presence. Returns {lang: score}."""
    scores: Dict[str, int] = {}

    # Python indicators
    py_patterns = [
        r"\bdef\s+\w+\s*\(",
        r"\bimport\s+\w+",
        r"\bfrom\s+\w+\s+import\b",
        r"\bprint\s*\(",
        r"\bself\b",
        r"\b__init__\b",
        r"\bclass\s+\w+.*:\s*$",
        r"\blambda\s+\w+:",
        r"\bNone\b",
        r"\bTrue\b|\bFalse\b",
        r"\bexcept\s+\w+",
        r"\braise\s+\w+",
        r"\basync\s+def\b",
        r"\bawait\s+\w+",
    ]
    scores["python"] = sum(
        1 for p in py_patterns if re.search(p, message, re.MULTILINE)
    )

    # TypeScript indicators (check before JS — TS has a superset of JS keywords)
    ts_patterns = [
        r"\binterface\s+\w+\s*\{",
        r"\btype\s+\w+\s*=",
        r"\b:\s*string\b|\b:\s*number\b|\b:\s*boolean\b",
        r"\b:\s*void\b",
        r"\b:\s*string\[\]|\:\s*number\[\]",
        r"\bimplements\s+\w+",
        r"\benum\s+\w+",
        r"\bas\s+\w+",
        r"\bReadonlyArray<",
        r"\bPartial<|\bRequired<|\bPick<",
    ]
    scores["typescript"] = sum(
        1 for p in ts_patterns if re.search(p, message, re.MULTILINE)
    )

    # JavaScript indicators (generic, also match in TS files)
    js_patterns = [
        r"\bconst\s+\w+\s*=",
        r"\blet\s+\w+\s*=",
        r"\bvar\s+\w+\s*=",
        r"\bfunction\s+\w+\s*\(",
        r"\bconsole\.log\b",
        r"\bdocument\.\w+",
        r"\bwindow\.\w+",
        r"\brequire\s*\(",
        r"\bmodule\.exports\b",
        r"\bnew\s+Promise\b",
        r"=>\s*\{",
        r"=>\s*\w+",
    ]
    scores["javascript"] = sum(
        1 for p in js_patterns if re.search(p, message, re.MULTILINE)
    )

    # Rust indicators
    rust_patterns = [
        r"\bfn\s+\w+\s*\(",
        r"\blet\s+mut\b",
        r"\bimpl\s+\w+",
        r"\buse\s+\w+::\w+",
        r"\bstruct\s+\w+",
        r"\bpub\s+(fn|struct|enum)\b",
        r"\bResult<|\bOption<|\bVec<",
        r"\bunwrap\(|\bunwrap_or\(|\bexpect\(",
    ]
    scores["rust"] = sum(
        1 for p in rust_patterns if re.search(p, message, re.MULTILINE)
    )

    return scores


def detect_language(message: str) -> Tuple[Optional[str], float]:
    """Detect the primary programming language in a message.

    Returns (language_id, confidence) where confidence is 0.0–1.0.
    Returns (None, 0.0) when no language is detected.
    """
    # Priority 1: explicit fenced code block language tags
    fenced = _extract_fenced_languages(message)
    if fenced:
        # If all blocks share the same language, high confidence
        unique = set(fenced)
        if len(unique) == 1:
            return (unique.pop(), 0.95)
        # Multiple languages — pick the most frequent
        from collections import Counter

        most_common = Counter(fenced).most_common(1)[0]
        return (most_common[0], 0.75)

    # Priority 2: keyword frequency heuristics
    scores = _keyword_score(message)
    if not scores:
        return (None, 0.0)

    best_lang, best_score = max(scores.items(), key=lambda x: x[1])
    if best_score == 0:
        return (None, 0.0)

    # Map score to approximate confidence (capped at 0.7 since no explicit tag)
    confidence = min(best_score / 6.0, 0.7)
    return (best_lang, confidence)


# ── Language glossary formatting ────────────────────────────────────────────


def _get_glossary_for_language(language: str) -> Dict[str, str]:
    """Return the term glossary for a given language id."""
    lang_map: Dict[str, Dict[str, str]] = {
        "python": _PYTHON_GLOSSARY,
        "javascript": _JAVASCRIPT_GLOSSARY,
        "typescript": _TYPESCRIPT_GLOSSARY,
    }
    return lang_map.get(language.lower(), {})


def format_language_glossary(
    message: str,
    max_terms: int = 8,
    language_override: Optional[str] = None,
) -> str:
    """Detect language from message and format a glossary addendum for the system prompt.

    When `language_override` is supplied (e.g. from request.language), detection is
    skipped and the glossary for that language is returned unconditionally.
    Returns an empty string when no language is detected or confidence is too low
    (< 0.3). Caps at `max_terms` to protect the system prompt token budget.
    """
    if language_override:
        language = language_override.strip().lower()
    else:
        language, confidence = detect_language(message)
        if language is None or confidence < 0.3:
            return ""

    lang_terms = _get_glossary_for_language(language)
    general_terms = _GENERAL_CODE_GLOSSARY.copy()

    # Build ordered term list: language-specific first, then general
    items: List[Tuple[str, str]] = []
    seen: set = set()

    for term, definition in lang_terms.items():
        if term not in seen:
            items.append((term, definition))
            seen.add(term)

    for term, definition in general_terms.items():
        if term not in seen:
            items.append((term, definition))
            seen.add(term)

    if not items:
        return ""

    items = items[:max_terms]

    lines = [f"\n[CODE GLOSSARY — {language.upper()}]"]
    for term, definition in items:
        lines.append(f"- {term}: {definition}")

    return "\n".join(lines) + "\n"


def list_language_terms(language: str) -> List[str]:
    """Return sorted term names for a given language (for debugging/UI)."""
    glossary = _get_glossary_for_language(language)
    return sorted(glossary.keys())


def list_supported_languages() -> List[str]:
    """Return languages with dedicated glossaries."""
    return ["python", "javascript", "typescript"]