"""
Token‑budget loading and scaling.

Reads defaults from env vars and providers.toml, then derives a per‑request
budget scaled to the model's actual context window.
"""

import importlib
import os
from pathlib import Path
from typing import Any, Dict, Optional

import structlog

from ...config.providers import get_model_config
from .models import ContextBudget

logger = structlog.get_logger()


def load_budget_config() -> ContextBudget:
    """Load token budget configuration from environment or defaults."""
    try:
        total_tokens = int(os.getenv("CONTEXT_WINDOW_SIZE", "8000"))
        system_tokens = int(os.getenv("SYSTEM_TOKENS", "300"))
        long_term_tokens = int(os.getenv("LONG_TERM_TOKENS", "300"))
        working_memory_tokens = int(os.getenv("WORKING_MEMORY_TOKENS", "700"))
        semantic_retrieval_tokens = int(
            os.getenv("SEMANTIC_RETRIEVAL_TOKENS", "1200")
        )

        return ContextBudget(
            total_tokens=total_tokens,
            system_tokens=system_tokens,
            long_term_tokens=long_term_tokens,
            working_memory_tokens=working_memory_tokens,
            semantic_retrieval_tokens=semantic_retrieval_tokens,
        )
    except Exception as e:
        logger.warning("Failed to load budget config, using defaults", error=str(e))
        return ContextBudget()


def load_model_context_windows() -> Dict[str, int]:
    """Read per‑model context windows from config/providers.toml."""
    config_path = Path(__file__).resolve().parents[3] / "config" / "providers.toml"
    if not config_path.exists():
        return {}

    parsed: Dict[str, Any] = {}
    try:
        try:
            import tomllib

            with open(config_path, "rb") as file_obj:
                parsed = tomllib.load(file_obj)
        except ImportError:
            toml_module = importlib.import_module("toml")
            with open(config_path, "r", encoding="utf-8") as file_obj:
                parsed = toml_module.load(file_obj)
    except (ImportError, OSError, ValueError, TypeError) as e:
        logger.warning("Failed to load provider context windows", error=str(e))
        return {}

    raw_windows = parsed.get("model_context_windows", {})
    if not isinstance(raw_windows, dict):
        return {}

    windows: Dict[str, int] = {}
    for model_name, value in raw_windows.items():
        try:
            windows[str(model_name)] = int(value)
        except (TypeError, ValueError):
            continue
    return windows


def get_model_context_window(
    model: Optional[str],
    model_context_windows: Dict[str, int],
    default_total: int,
) -> int:
    """Resolve the context‑window size for *model*."""
    if not model:
        return default_total

    if model in model_context_windows:
        return model_context_windows[model]

    fallback_config = get_model_config(model)
    fallback_max_tokens = (
        fallback_config.get("max_tokens") if isinstance(fallback_config, dict) else None
    )
    try:
        return int(fallback_max_tokens) if fallback_max_tokens else default_total
    except (TypeError, ValueError):
        return default_total


def derive_budget(
    default_budget: ContextBudget,
    model_context_windows: Dict[str, int],
    response_reserve_tokens: int,
    model: Optional[str] = None,
    max_context_tokens: Optional[int] = None,
) -> ContextBudget:
    """Scale the default budget to the model's usable token window."""
    model_window = max_context_tokens or get_model_context_window(
        model, model_context_windows, default_budget.total_tokens
    )
    usable_tokens = max(512, model_window - response_reserve_tokens)

    base_total = max(1, default_budget.total_tokens)
    scale = usable_tokens / base_total

    system_tokens = max(80, int(default_budget.system_tokens * scale))
    long_term_tokens = max(80, int(default_budget.long_term_tokens * scale))
    working_memory_tokens = max(
        120, int(default_budget.working_memory_tokens * scale)
    )
    semantic_retrieval_tokens = max(
        240, int(default_budget.semantic_retrieval_tokens * scale)
    )

    fixed = (
        system_tokens
        + long_term_tokens
        + working_memory_tokens
        + semantic_retrieval_tokens
    )
    if fixed >= usable_tokens:
        shrink = max(0.3, usable_tokens / max(1, fixed))
        system_tokens = max(64, int(system_tokens * shrink))
        long_term_tokens = max(64, int(long_term_tokens * shrink))
        working_memory_tokens = max(96, int(working_memory_tokens * shrink))
        semantic_retrieval_tokens = max(128, int(semantic_retrieval_tokens * shrink))

    ephemeral_tokens = max(
        0,
        usable_tokens
        - (
            system_tokens
            + long_term_tokens
            + working_memory_tokens
            + semantic_retrieval_tokens
        ),
    )

    return ContextBudget(
        total_tokens=usable_tokens,
        system_tokens=system_tokens,
        long_term_tokens=long_term_tokens,
        working_memory_tokens=working_memory_tokens,
        semantic_retrieval_tokens=semantic_retrieval_tokens,
        ephemeral_tokens=ephemeral_tokens,
    )
