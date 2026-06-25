"""
Heuristic prompt-to-TaskType classifier.

Runs in microseconds with no ML dependencies. Used by BanditRouter and
SmartRouter to auto-detect task type when the caller doesn't specify one.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from api.services.smart_router import TaskType


# Keyword sets per task type, checked in priority order (first match wins).
# Tuples of (pattern_strings, ...) matched against lowercase prompt text.
_IMAGE_KEYWORDS = (
    "generate image",
    "generate an image",
    "create an image",
    "draw me",
    "draw a",
    "dalle",
    "midjourney",
    "stable diffusion",
    "flux model",
    "text to image",
)

_VISION_KEYWORDS = (
    "describe this image",
    "describe the image",
    "what's in this",
    "what is in this",
    "analyze the image",
    "analyze this image",
    "look at this screenshot",
    "look at this image",
    "what does this image show",
    "read this image",
)

_EMBEDDING_KEYWORDS = (
    "embedding",
    "embeddings",
    "embed this",
    "semantic search",
    "vector similarity",
    "cosine similarity",
)

_TRANSLATION_KEYWORDS = (
    "translate",
    "traducir",
    "übersetzen",
    "翻译",
    "traduire",
    "tradurre",
    "переводить",
)

_CODE_GENERATION_KEYWORDS = (
    "write a function",
    "write me a function",
    "implement a",
    "implement the",
    "create a class",
    "write code",
    "write a script",
    "write a program",
    "in python",
    "in typescript",
    "in javascript",
    "in golang",
    "in rust",
    "in java",
    "in c++",
)

# Code block indicator: at least 3 lines that look like code syntax
_CODE_SYNTAX_PATTERN = re.compile(
    r"(def |function |const |let |var |import |from |class |public |private |return |async )",
)

_CODE_REVIEW_KEYWORDS = (
    "review this",
    "review my",
    "code review",
    "what's wrong with",
    "whats wrong with",
    "find the bug",
    "find bugs",
    "refactor this",
    "refactor my",
    "pull request",
    "lgtm",
    "looks good to me",
    "improve this code",
    "fix this code",
)

_REASONING_KEYWORDS = (
    "think step by step",
    "reason about",
    "analyze this",
    "analyze the",
    "compare and contrast",
    "pros and cons",
    "pros/cons",
    "tradeoffs",
    "trade-offs",
    "explain why",
    "why does",
    "how does",
    "what are the implications",
    "evaluate",
    "assess",
)

_SUMMARIZATION_KEYWORDS = (
    "summarize",
    "summarise",
    "tl;dr",
    "tldr",
    "summary of",
    "give me a summary",
    "key points",
    "key takeaways",
    "main points",
    "in brief",
    "in short",
    "condense",
)


def _contains_any(text: str, keywords: tuple) -> bool:
    return any(kw in text for kw in keywords)


def _looks_like_code(prompt: str) -> bool:
    """Return True if the prompt contains ≥3 code-syntax lines."""
    matches = _CODE_SYNTAX_PATTERN.findall(prompt)
    return len(matches) >= 3


class PromptClassifier:
    """Classify a prompt string into a TaskType using keyword heuristics."""

    def classify(self, prompt: str) -> "TaskType":
        from api.services.smart_router import TaskType  # lazy to avoid circular

        text = prompt.lower()

        if _contains_any(text, _IMAGE_KEYWORDS):
            return TaskType.IMAGE_GENERATION
        if _contains_any(text, _VISION_KEYWORDS):
            return TaskType.VISION
        if _contains_any(text, _EMBEDDING_KEYWORDS):
            return TaskType.EMBEDDING
        if _contains_any(text, _TRANSLATION_KEYWORDS):
            return TaskType.TRANSLATION
        if _contains_any(text, _CODE_GENERATION_KEYWORDS) or _looks_like_code(prompt):
            return TaskType.CODE_GENERATION
        if _contains_any(text, _CODE_REVIEW_KEYWORDS):
            return TaskType.CODE_REVIEW
        if _contains_any(text, _REASONING_KEYWORDS):
            return TaskType.REASONING
        if _contains_any(text, _SUMMARIZATION_KEYWORDS):
            return TaskType.SUMMARIZATION
        return TaskType.CHAT

    def classify_messages(self, messages: List[Dict[str, Any]]) -> "TaskType":
        """Classify from a messages list, using the last user message."""
        from api.services.smart_router import TaskType  # lazy to avoid circular

        last_user_content = ""
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str):
                    last_user_content = content
                elif isinstance(content, list):
                    # OpenAI multi-part content: extract text parts
                    last_user_content = " ".join(
                        part.get("text", "") for part in content if isinstance(part, dict)
                    )
                break

        if not last_user_content:
            return TaskType.CHAT

        return self.classify(last_user_content)


prompt_classifier = PromptClassifier()
