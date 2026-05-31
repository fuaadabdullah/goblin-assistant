from __future__ import annotations

import asyncio
from typing import Any, AsyncGenerator, Dict, List, Optional

from ..base import BaseProvider, ProviderErrorCategory, ProviderResult, classify_provider_error
from ..metrics import record_dispatch


def provider_error_category(
    value: Any,
    fallback_error: str,
) -> Optional[ProviderErrorCategory]:
    if value is None:
        return classify_provider_error(fallback_error) if fallback_error else None
    if isinstance(value, ProviderErrorCategory):
        return value
    try:
        return ProviderErrorCategory(str(value))
    except Exception:
        return classify_provider_error(fallback_error) if fallback_error else None


def build_invoke_kwargs(payload: Dict[str, Any]) -> Dict[str, Any]:
    kwargs = dict(payload)
    for key in ("messages", "prompt", "model"):
        kwargs.pop(key, None)
    return kwargs


async def stream_wrap(
    dispatcher: Any,
    provider_id: str,
    provider: BaseProvider,
    messages: List[Dict[str, str]],
    model: str,
    *,
    logger: Any,
    **kwargs: Any,
) -> ProviderResult:
    from ...routing.router import registry

    started_at = asyncio.get_running_loop().time()
    try:
        gen = provider.stream(messages, model, **kwargs)
        first = None
        async for chunk in gen:
            first = chunk
            break

        async def combined() -> AsyncGenerator[Dict[str, Any], None]:
            if first is not None:
                yield first
            async for item in gen:
                yield item

        latency = (asyncio.get_running_loop().time() - started_at) * 1000
        provider.record_success()
        registry.record_success(provider_id, latency_ms=latency, cost_usd=0.0)
        record_dispatch(
            provider_id=provider_id,
            model=model,
            latency_ms=latency,
            ok=True,
        )
        logger.bind(
            provider=provider_id,
            model=model,
            latency_ms=round(latency, 1),
        ).info("dispatch_stream_success")
        return ProviderResult(
            ok=True,
            provider=provider_id,
            model=model,
            latency_ms=latency,
            raw={"stream_gen": combined()},
        )
    except Exception as exc:
        safe_error = dispatcher._sanitize_error(exc)
        error_category = classify_provider_error(exc).value
        provider.record_failure(safe_error)
        registry.record_failure(provider_id)
        record_dispatch(
            provider_id=provider_id,
            model=model,
            latency_ms=0.0,
            ok=False,
            error_category=error_category,
        )
        logger.bind(
            provider=provider_id,
            model=model,
            error_category=error_category,
        ).warning("dispatch_stream_failure", error=safe_error)
        return ProviderResult(
            ok=False,
            provider=provider_id,
            model=model,
            error=safe_error,
            error_category=error_category,
        )


async def dispatch_request(
    dispatcher: Any,
    *,
    pid: Optional[str],
    model: Optional[str],
    payload: Dict[str, Any],
    timeout_ms: int = 30_000,
    stream: bool = False,
    dry_run: bool = False,
    logger: Any,
) -> Dict[str, Any]:
    from ...routing.router import registry

    resolved_pid, resolved_model = dispatcher._resolve_model_alias(pid, model)
    messages = payload.get("messages", [])
    prompt = payload.get("prompt", "")
    candidates = dispatcher._candidate_order(resolved_pid)
    if not candidates:
        return {
            "ok": False,
            "error": f"unknown-provider:{pid}",
            "latency_ms": 0.0,
        }

    explicit_mode = resolved_pid not in (None, "auto", "cheapest", "local")
    if explicit_mode:
        first_config = dispatcher._configs.get(candidates[0], {}) if candidates else {}
        if first_config.get("force_fallback"):
            fallback_order = [p for p in dispatcher._hybrid_order() if p not in candidates]
            ordered = [*candidates, *fallback_order]
        else:
            ordered = candidates
    else:
        configured_candidates = dispatcher._auto_configured_candidates(candidates)
        if not configured_candidates:
            configured_candidates = [p for p in candidates if dispatcher.is_configured(p)]

        available: List[str] = []
        for provider_id in configured_candidates:
            current_provider = dispatcher._ensure_provider(provider_id)
            if current_provider is None:
                continue
            if (
                current_provider.is_available()
                and registry.get(provider_id).success_rate >= dispatcher._routing_min_success_rate
            ):
                available.append(provider_id)
        ordered = available or configured_candidates

    if explicit_mode and not ordered:
        ordered = candidates
    if not ordered:
        return {
            "ok": False,
            "error": "no-configured-providers",
            "latency_ms": 0.0,
        }

    if dry_run:
        candidate_detail = []
        for provider_id in ordered:
            current_provider = dispatcher._ensure_provider(provider_id)
            candidate_detail.append(
                {
                    "provider": provider_id,
                    "model": resolved_model
                    or (current_provider.default_model if current_provider else ""),
                    "configured": dispatcher.is_configured(provider_id),
                }
            )
        first = candidate_detail[0]
        return {
            "ok": True,
            "dry_run": True,
            "resolved_provider": first["provider"],
            "resolved_model": first["model"],
            "routing_mode": "explicit" if explicit_mode else "auto",
            "candidate_order": candidate_detail,
        }

    last_error = "all providers failed"
    last_category: Optional[ProviderErrorCategory] = None

    for provider_id in ordered:
        current_provider = dispatcher._ensure_provider(provider_id)
        if current_provider is None:
            continue

        model_name = resolved_model or current_provider.default_model
        log = logger.bind(provider=provider_id, model=model_name)
        log.info("dispatch_attempt")
        kwargs = dispatcher._build_invoke_kwargs(payload)

        try:
            if stream:
                result = await asyncio.wait_for(
                    dispatcher._stream_wrap(
                        provider_id,
                        current_provider,
                        messages,
                        model_name,
                        prompt=prompt,
                        **kwargs,
                    ),
                    timeout=timeout_ms / 1000,
                )
                if result.ok:
                    return {
                        "ok": True,
                        "stream": result.raw.get("stream_gen"),
                        "provider": provider_id,
                        "model": model_name,
                    }
                last_error = dispatcher._sanitize_error(result.error or last_error)
                last_category = dispatcher._provider_error_category(
                    result.error_category,
                    last_error,
                )
                continue

            result = await asyncio.wait_for(
                current_provider.invoke(
                    messages,
                    model_name,
                    stream=False,
                    prompt=prompt,
                    **kwargs,
                ),
                timeout=timeout_ms / 1000,
            )
            if result.ok:
                current_provider.record_success()
                registry.record_success(
                    provider_id,
                    latency_ms=float(result.latency_ms),
                    cost_usd=float(result.cost_usd or 0.0),
                )
                record_dispatch(
                    provider_id=provider_id,
                    model=model_name,
                    latency_ms=float(result.latency_ms),
                    ok=True,
                )
                log.info(
                    "dispatch_success",
                    latency_ms=round(float(result.latency_ms), 1),
                )
                return result.to_dict()

            last_error = dispatcher._sanitize_error(result.error or last_error)
            last_category = dispatcher._provider_error_category(
                result.error_category,
                last_error,
            )
            current_provider.record_failure(last_error)
            registry.record_failure(provider_id)
            record_dispatch(
                provider_id=provider_id,
                model=model_name,
                latency_ms=float(result.latency_ms),
                ok=False,
                error_category=result.error_category,
            )
            log.warning(
                "dispatch_failure",
                error=last_error,
                error_category=result.error_category,
            )
        except asyncio.TimeoutError:
            last_error = f"timeout after {timeout_ms}ms"
            last_category = ProviderErrorCategory.TIMEOUT
            current_provider.record_failure(last_error)
            registry.record_failure(provider_id)
            record_dispatch(
                provider_id=provider_id,
                model=model_name,
                latency_ms=float(timeout_ms),
                ok=False,
                error_category=ProviderErrorCategory.TIMEOUT.value,
            )
            log.warning(
                "dispatch_timeout",
                error=last_error,
                error_category=ProviderErrorCategory.TIMEOUT.value,
                latency_ms=timeout_ms,
            )
        except Exception as exc:
            last_error = dispatcher._sanitize_error(exc)
            last_category = classify_provider_error(exc)
            current_provider.record_failure(last_error)
            registry.record_failure(provider_id)
            record_dispatch(
                provider_id=provider_id,
                model=model_name,
                latency_ms=0.0,
                ok=False,
                error_category=last_category.value,
            )
            log.warning(
                "dispatch_exception",
                error=last_error,
                error_category=last_category.value,
            )

    return {
        "ok": False,
        "error": last_error,
        "error_category": last_category.value if last_category else None,
        "provider": "none",
        "latency_ms": 0.0,
    }
