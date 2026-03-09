"""Groq provider wrapper built on the OpenAI-compatible base."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .openai_compatible import OpenAICompatibleProvider


class GroqProvider(OpenAICompatibleProvider):
    def __init__(
        self,
        provider_id: str | Dict[str, Any],
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(provider_id, config)
