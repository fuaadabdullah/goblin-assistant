"""Generic provider wrapper for OpenAI-compatible endpoints."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import structlog

from .openai_compatible import OpenAICompatibleProvider

logger = structlog.get_logger(__name__)


class GenericProvider(OpenAICompatibleProvider):
    _selection_warned = False

    def __init__(
        self,
        provider_id: str | Dict[str, Any],
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._warn_or_block(provider_id, config)
        super().__init__(provider_id, config)

    @classmethod
    def _allowed_in_current_env(cls) -> bool:
        env = os.getenv("ENV", "").strip().lower()
        testing = os.getenv("TESTING", "").strip().lower() in {"1", "true", "yes", "on"}
        return env in {"development", "dev"} or testing

    @classmethod
    def _warn_or_block(
        cls,
        provider_id: str | Dict[str, Any],
        config: Optional[Dict[str, Any]],
    ) -> None:
        if cls._selection_warned:
            if not cls._allowed_in_current_env():
                raise RuntimeError(
                    "GenericProvider is disabled outside development or test environments",
                )
            return

        cls._selection_warned = True
        provider_name = "provider"
        if isinstance(provider_id, str):
            provider_name = provider_id
        elif isinstance(config, dict):
            provider_name = str(config.get("name") or provider_name)
        logger.warning(
            "generic_provider_selected",
            provider=provider_name,
            env=os.getenv("ENV", ""),
            testing=os.getenv("TESTING", ""),
            allowed=cls._allowed_in_current_env(),
            note="GenericProvider is a compatibility escape hatch, not a production route",
        )
        if not cls._allowed_in_current_env():
            raise RuntimeError(
                "GenericProvider is disabled outside development or test environments",
            )
