"""Deterministic test-mode failure injection for provider routing."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List, Optional

from ..base import ProviderResult

__test__ = False


def active_test_mode_state(
    test_mode_stack: List[Dict[str, Any]],
    provider_id: str,
) -> Optional[Dict[str, Any]]:
    for state in reversed(test_mode_stack):
        if provider_id in state["profiles"]:
            return state
    return None


async def apply_test_mode_delay(
    test_mode_stack: List[Dict[str, Any]],
    provider_id: str,
) -> None:
    state = active_test_mode_state(test_mode_stack, provider_id)
    if state is None:
        return
    latency_ms = float(state["profiles"][provider_id].get("latency_ms", 0.0) or 0.0)
    if latency_ms > 0:
        await asyncio.sleep(latency_ms / 1000)


async def maybe_inject_test_failure(
    test_mode_stack: List[Dict[str, Any]],
    provider_id: str,
    model: str,
    *,
    provider_error_category_fn,
) -> Optional[ProviderResult]:
    state = active_test_mode_state(test_mode_stack, provider_id)
    if state is None:
        return None
    profile = state["profiles"][provider_id]
    call_count = int(state["calls"].get(provider_id, 0)) + 1
    state["calls"][provider_id] = call_count
    fail_after_calls = profile.get("fail_after_calls")
    fail_probability = float(profile.get("fail_probability", 0.0) or 0.0)
    should_fail = False
    if (
        isinstance(fail_after_calls, int)
        and fail_after_calls >= 0
        and call_count > fail_after_calls
    ):
        should_fail = True
    elif fail_probability > 0:
        import random

        if random.random() < min(1.0, max(0.0, fail_probability)):
            should_fail = True
    if not should_fail:
        return None
    category = provider_error_category_fn(profile.get("error_category"), "test failure")
    error_message = str(profile.get("error", "") or f"test-mode {category.value} failure")
    return ProviderResult(
        ok=False,
        provider=provider_id,
        model=model,
        error=error_message,
        error_category=category.value,
        latency_ms=float(profile.get("latency_ms", 0.0) or 0.0),
    )


async def invoke_with_test_mode(
    test_mode_stack: List[Dict[str, Any]],
    provider_id: str,
    provider: Any,
    messages: List[Dict[str, str]],
    model: str,
    *,
    sanitize_error_fn,
    provider_error_category_fn,
    **kwargs: Any,
) -> ProviderResult:
    started_at = asyncio.get_running_loop().time()
    await apply_test_mode_delay(test_mode_stack, provider_id)
    injected = await maybe_inject_test_failure(
        test_mode_stack,
        provider_id,
        model,
        provider_error_category_fn=provider_error_category_fn,
    )
    if injected is not None:
        return injected
    result = await provider.invoke(
        messages,
        model,
        stream=False,
        **kwargs,
    )
    elapsed_ms = (asyncio.get_running_loop().time() - started_at) * 1000
    if result.latency_ms < elapsed_ms:
        return ProviderResult(
            ok=result.ok,
            text=result.text,
            raw=result.raw,
            provider=result.provider,
            model=result.model,
            usage=result.usage,
            cost_usd=result.cost_usd,
            latency_ms=elapsed_ms,
            error=result.error,
            error_category=result.error_category,
        )
    return result


@asynccontextmanager
async def test_mode_context(
    test_mode_stack: List[Dict[str, Any]],
    profiles: Dict[str, Dict[str, Any]],
    self_obj: Any,
    *,
    canonical_provider_id_fn,
) -> AsyncGenerator[Any, None]:
    """Context manager for deterministic failure profile injection during tests."""
    state = {
        "profiles": {
            canonical_provider_id_fn(pid) or pid: dict(profile) for pid, profile in profiles.items()
        },
        "calls": {},
    }
    test_mode_stack.append(state)
    try:
        yield self_obj
    finally:
        with_state = [item for item in test_mode_stack if item is not state]
        test_mode_stack.clear()
        test_mode_stack.extend(with_state)
