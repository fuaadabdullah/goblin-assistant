"""Routing selection helpers for provider-aware task execution."""

from __future__ import annotations

import asyncio
import importlib
import os
from pathlib import Path
from typing import Any, Dict, List

from ..providers.dispatcher import invoke_provider


def _load_provider_configs() -> Dict[str, Dict[str, Any]]:
    config_path = Path(__file__).resolve().parents[2] / "config" / "providers.toml"
    if not config_path.exists():
        return {}

    try:
        try:
            import tomllib

            with open(config_path, "rb") as file_obj:
                parsed = tomllib.load(file_obj)
        except ImportError:
            toml = importlib.import_module("toml")
            with open(config_path, "r", encoding="utf-8") as file_obj:
                parsed = toml.load(file_obj)
    except (ImportError, OSError, ValueError, TypeError):
        return {}

    providers = parsed.get("providers", {})
    return providers if isinstance(providers, dict) else {}


def _api_key_present(provider_cfg: Dict[str, Any]) -> bool:
    api_key_env = provider_cfg.get("api_key_env")
    if not isinstance(api_key_env, str) or not api_key_env:
        return True
    return bool(os.getenv(api_key_env, "").strip())


def _provider_capabilities(provider_id: str) -> set[str]:
    default_caps = {
        "chat",
        "reasoning",
        "code",
    }
    mapping: Dict[str, set[str]] = {
        "deepseek": {"chat", "reasoning", "code"},
        "gemini": {"chat", "reasoning", "code"},
        "openai": {"chat", "reasoning", "code"},
        "anthropic": {"chat", "reasoning", "code"},
        "groq": {"chat", "reasoning", "code"},
        "siliconeflow": {"chat", "reasoning", "code"},
        "azure": {"chat", "reasoning", "code"},
        "vertex_ai": {"chat", "reasoning", "code"},
        "aliyun": {"chat", "reasoning", "code"},
        "ollama": {"chat", "code"},
    }
    return mapping.get(provider_id, default_caps)


def top_providers_for(
    capability: str,
    prefer_local: bool = False,
    prefer_cost: bool = False,
    limit: int = 6,
) -> List[str]:
    providers_cfg = _load_provider_configs()
    if not providers_cfg:
        fallback = ["groq", "siliconeflow", "openai", "anthropic", "gemini", "ollama"]
        return fallback[: max(1, limit)]

    candidates: List[str] = []
    for provider_id, cfg in providers_cfg.items():
        if not isinstance(cfg, dict):
            continue
        if not cfg.get("enabled", True):
            continue
        if capability not in _provider_capabilities(provider_id):
            continue
        if not _api_key_present(cfg):
            continue
        candidates.append(provider_id)

    if prefer_local:
        local_first = sorted(candidates, key=lambda p: 0 if p in {"ollama", "llamacpp"} else 1)
        candidates = local_first
    elif prefer_cost:
        # Cost-aware ordering: cheaper providers first
        cost_rank = {
            "groq": 0,
            "siliconeflow": 1,
            "deepseek": 2,
            "azure": 3,
            "openai": 4,
            "anthropic": 5,
            "gemini": 6,
            "ollama": 7,
        }
        candidates = sorted(candidates, key=lambda p: cost_rank.get(p, 100))

    if not candidates:
        candidates = ["auto"]

    return candidates[: max(1, limit)]


async def route_task(
    task_type: str,
    payload: Dict[str, Any],
    prefer_local: bool = False,
    prefer_cost: bool = False,
    max_retries: int = 2,
    stream: bool = False,
) -> Dict[str, Any]:
    provider_candidates = top_providers_for(
        capability=task_type,
        prefer_local=prefer_local,
        prefer_cost=prefer_cost,
        limit=max(1, max_retries + 1),
    )
    model = payload.get("model")
    resolved_model = model if isinstance(model, str) else ""

    last_error = "Routing failed"
    for provider_id in provider_candidates:
        response = await invoke_provider(
            pid=provider_id,
            model=resolved_model,
            payload=payload,
            timeout_ms=int(payload.get("timeout_ms", 30000)),
            stream=stream,
        )
        if isinstance(response, dict) and response.get("ok"):
            response.setdefault("selected_provider", provider_id)
            return response
        if isinstance(response, dict):
            last_error = response.get("error", last_error)

    return {
        "ok": False,
        "error": last_error,
        "providers_tried": provider_candidates,
    }


def route_task_sync(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    try:
        asyncio.get_running_loop()
        return {
            "ok": False,
            "error": "route_task_sync cannot run in an active event loop; use route_task instead",
        }
    except RuntimeError:
        return asyncio.run(route_task(*args, **kwargs))
