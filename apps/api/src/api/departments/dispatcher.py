"""Department dispatcher — invokes providers through the department abstraction.

This wraps the existing ProviderDispatcher with department-level logic:
1. Accept a DepartmentSelection
2. Resolve to the first available provider in the department's chain
3. Handle fallback across the chain on failure
4. Return the result with department metadata (no provider names in public fields)
"""

from __future__ import annotations

from typing import Any, AsyncGenerator, Dict, List, Optional

import structlog

from ..providers.base import ProviderErrorCategory
from ..providers.dispatcher import dispatcher as _provider_dispatcher
from .dispatcher_pkg import build_chain, reorder_chain_by_bandit
from .models import DepartmentSelection
from .registry import DEPARTMENT_REGISTRY

logger = structlog.get_logger()


class DepartmentDispatchError(Exception):
    """All providers in a department's chain have failed."""


class DepartmentDispatcher:
    """Dispatches requests through a department's provider chain.

    Wraps the existing ProviderDispatcher with fallback logic
    across the department's configured provider chain.
    """

    async def dispatch(
        self,
        selection: DepartmentSelection,
        payload: Dict[str, Any],
        *,
        stream: bool = False,
        timeout_ms: int = 30000,
    ) -> Dict[str, Any]:
        """Invoke the department's provider chain.

        Tries the resolved provider first, then falls back through the chain.
        Returns a normalized dict with department info (no raw provider leaks).

        Args:
            selection: DepartmentSelection from the router.
            payload: Request payload (messages, model, etc.).
            stream: Whether to stream the response.
            timeout_ms: Timeout in milliseconds.

        Returns:
            Normalized response dict with department metadata.
            On total failure, returns an error dict (never raises).
        """
        # Build the ordered chain: resolved_provider + fallbacks
        chain = self._build_chain(selection)

        last_error: Optional[str] = None
        last_error_category: Optional[str] = None

        for provider_id, model_name in chain:
            try:
                # Check if provider is available
                provider = _provider_dispatcher.get_provider(provider_id)
                if provider and not provider.is_available():
                    logger.warning(
                        "department_provider_unavailable",
                        department=selection.department_id.value,
                        provider=provider_id,
                        circuit_state=provider.circuit_state,
                    )
                    continue

                # Prepare payload with the department's model
                call_payload = dict(payload)
                call_payload["model"] = model_name

                # Dispatch via the existing provider dispatcher
                result = await _provider_dispatcher.invoke(
                    pid=provider_id,
                    model=model_name,
                    payload=call_payload,
                    timeout_ms=timeout_ms,
                    stream=stream,
                )

                # Check if successful
                if isinstance(result, dict) and result.get("ok", False):
                    # Success — annotate with department metadata
                    result["_department"] = selection.department_id.value
                    result["_department_reason"] = selection.reason
                    return result

                # Record failure and try next in chain
                if isinstance(result, dict):
                    last_error = str(result.get("error", "unknown"))
                    last_error_category = str(
                        result.get("error_category") or ProviderErrorCategory.UNKNOWN.value
                    )
                    logger.warning(
                        "department_provider_failed",
                        department=selection.department_id.value,
                        provider=provider_id,
                        model=model_name,
                        error=last_error,
                        category=last_error_category,
                    )

            except Exception as exc:
                last_error = str(exc)
                last_error_category = ProviderErrorCategory.UNKNOWN.value
                logger.warning(
                    "department_provider_exception",
                    department=selection.department_id.value,
                    provider=provider_id,
                    error=last_error,
                )

        # All providers exhausted
        logger.error(
            "department_all_providers_exhausted",
            department=selection.department_id.value,
            chain=[p for p, _m in chain],
            last_error=last_error,
        )

        return {
            "ok": False,
            "error": last_error or "All providers in department chain failed",
            "error_category": last_error_category or ProviderErrorCategory.UNKNOWN.value,
            "_department": selection.department_id.value,
            "_department_reason": selection.reason,
        }

    async def dispatch_stream(
        self,
        selection: DepartmentSelection,
        payload: Dict[str, Any],
        *,
        timeout_ms: int = 30000,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream a response through the department's provider chain.

        Tries the primary provider first. If streaming fails, falls back
        to the next available provider and returns a non-streaming result.

        Yields:
            Dicts with stream events, annotated with department metadata.
        """
        chain = self._build_chain(selection)

        for provider_id, model_name in chain:
            try:
                provider = _provider_dispatcher.get_provider(provider_id)
                if provider and not provider.is_available():
                    continue

                call_payload = dict(payload)
                call_payload["model"] = model_name

                # Yield initial status
                yield {
                    "event": "STATUS",
                    "department": selection.department_id.value,
                    "content": f"processing via {selection.department_id.value}",
                }

                # Stream from the existing streaming infrastructure
                async for chunk in _provider_dispatcher.stream(
                    pid=provider_id,
                    model=model_name,
                    payload=call_payload,
                    timeout_ms=timeout_ms,
                ):
                    if isinstance(chunk, dict):
                        chunk["_department"] = selection.department_id.value
                        chunk["_department_reason"] = selection.reason
                    yield chunk

                # Successful stream completion
                return

            except Exception as exc:
                logger.warning(
                    "department_stream_fallback",
                    department=selection.department_id.value,
                    provider=provider_id,
                    error=str(exc),
                )
                # Yield a fallback notification
                yield {
                    "event": "STATUS",
                    "department": selection.department_id.value,
                    "content": "retrying with alternative processing",
                }

        # All providers exhausted — yield error
        yield {
            "event": "ERROR",
            "department": selection.department_id.value,
            "error": "All processing paths failed",
            "is_recoverable": False,
        }

    def list_departments(self) -> List[Dict[str, str]]:
        """Return public-facing department list (no provider details)."""
        return DEPARTMENT_REGISTRY.list_public()

    def resolve_provider_id(self, department_id_str: str) -> Optional[str]:
        """Resolve a department string to its primary provider ID (internal).

        Used by estimate-tokens and other internal call sites.
        """
        try:
            policy = DEPARTMENT_REGISTRY.get_by_id_str(department_id_str)
            pid, _model = policy.primary_provider
            return pid
        except (KeyError, IndexError, ValueError):
            return None

    def _build_chain(self, selection: DepartmentSelection) -> List[tuple[str, str]]:
        return build_chain(selection)

    def _reorder_chain_by_bandit(
        self,
        chain: List[tuple[str, str]],
        task_type: str,
    ) -> List[tuple[str, str]]:
        return reorder_chain_by_bandit(chain, task_type)


# Singleton
department_dispatcher: DepartmentDispatcher = DepartmentDispatcher()
