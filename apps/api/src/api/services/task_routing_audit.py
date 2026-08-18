"""Best-effort persistence for task-aware routing decisions."""

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

import structlog

from ..providers.pricing import estimate_cost

logger = structlog.get_logger(__name__)


async def record_task_routing_decision(
    *,
    request_id: Optional[str],
    requested_model: Optional[str],
    task_class: str,
    classifier_source: str,
    classifier_confidence: float,
    classifier_reason: Optional[str],
    classifier_model: Optional[str],
    logical_model: str,
    backend_provider_id: Optional[str],
    backend_model: Optional[str],
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    classifier_prompt_tokens: int = 0,
    classifier_completion_tokens: int = 0,
    classifier_cost_usd: float = 0.0,
    latency_ms: float = 0.0,
    success: bool = True,
    error_message: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Insert a routing-decision row if database access is available."""

    decision_request_id = str(request_id or uuid.uuid4())
    final_prompt_tokens = max(0, int(prompt_tokens))
    final_completion_tokens = max(0, int(completion_tokens))
    final_total_tokens = final_prompt_tokens + final_completion_tokens
    final_cost_usd = 0.0
    if backend_provider_id:
        try:
            final_cost_usd = estimate_cost(
                backend_provider_id,
                final_prompt_tokens,
                final_completion_tokens,
                model=backend_model,
            )
        except Exception:
            final_cost_usd = 0.0

    classifier_prompt_tokens = max(0, int(classifier_prompt_tokens))
    classifier_completion_tokens = max(0, int(classifier_completion_tokens))
    classifier_total_tokens = classifier_prompt_tokens + classifier_completion_tokens
    combined_prompt_tokens = final_prompt_tokens + classifier_prompt_tokens
    combined_completion_tokens = final_completion_tokens + classifier_completion_tokens
    combined_total_tokens = final_total_tokens + classifier_total_tokens
    combined_cost_usd = round(
        max(0.0, float(final_cost_usd)) + max(0.0, float(classifier_cost_usd)), 8
    )

    row_metadata: Dict[str, Any] = dict(metadata or {})
    row_metadata.update(
        {
            "classifier_prompt_tokens": classifier_prompt_tokens,
            "classifier_completion_tokens": classifier_completion_tokens,
            "classifier_total_tokens": classifier_total_tokens,
            "classifier_cost_usd": round(max(0.0, float(classifier_cost_usd)), 8),
            "final_prompt_tokens": final_prompt_tokens,
            "final_completion_tokens": final_completion_tokens,
            "final_total_tokens": final_total_tokens,
            "final_cost_usd": round(max(0.0, float(final_cost_usd)), 8),
        }
    )

    try:
        from ..storage.database import get_db_context
        from ..storage.models import TaskRoutingDecisionModel

        async with get_db_context() as session:
            await session.run_sync(
                lambda sync_session: TaskRoutingDecisionModel.__table__.create(
                    sync_session.get_bind(),
                    checkfirst=True,
                )
            )
            session.add(
                TaskRoutingDecisionModel(
                    decision_id=str(uuid.uuid4()),
                    request_id=decision_request_id,
                    requested_model=requested_model,
                    task_class=task_class,
                    classifier_source=classifier_source,
                    classifier_confidence=max(0.0, min(1.0, float(classifier_confidence))),
                    classifier_reason=classifier_reason,
                    classifier_model=classifier_model,
                    logical_model=logical_model,
                    backend_provider_id=backend_provider_id,
                    backend_model=backend_model,
                    prompt_tokens=combined_prompt_tokens,
                    completion_tokens=combined_completion_tokens,
                    total_tokens=combined_total_tokens,
                    cost_usd=combined_cost_usd,
                    latency_ms=max(0.0, float(latency_ms)),
                    success=bool(success),
                    error_message=error_message,
                    metadata_=row_metadata,
                )
            )
    except Exception as exc:
        logger.debug(
            "task_routing_decision_persist_failed",
            request_id=decision_request_id,
            logical_model=logical_model,
            error=str(exc),
        )
