"""Generic provider wrapper for OpenAI-compatible endpoints."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .openai_compatible import OpenAICompatibleProvider


class GenericProvider(OpenAICompatibleProvider):
    def __init__(
        self,
        provider_id: str | Dict[str, Any],
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(provider_id, config)
