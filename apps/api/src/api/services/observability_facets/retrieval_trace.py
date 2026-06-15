from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

import structlog

from ...observability.retrieval_tracer import (
    RetrievalTrace as ObsRetrievalTrace,
)
from ...observability.retrieval_tracer import (
    RetrievedItem,
    retrieval_tracer,
)
from ..observability_models import RetrievalTrace
from .shared import compute_hash

logger = structlog.get_logger()


class RetrievalTraceFacet:
    def __init__(self, owner: Any):
        self._owner = owner

    def log_retrieval_trace(
        self,
        request_id: str,
        user_id: Optional[str],
        model_selected: str,
        token_budget: int,
        retrieval_result: Dict[str, Any],
    ) -> None:
        try:
            layers = retrieval_result.get("layers", [])
            items = []
            for idx, layer in enumerate(layers):
                items.append(
                    RetrievedItem(
                        source=layer["name"],
                        source_id=None,
                        content="",
                        relevance_score=layer.get("score", 0.0),
                        token_count=layer["tokens"],
                        rank=idx + 1,
                        truncated=layer["tokens"] < layer.get("original_tokens", layer["tokens"]),
                        metadata={},
                    )
                )

            context_text = retrieval_result.get("context", "")
            context_hash = compute_hash(context_text)

            import asyncio  # noqa: PLC0415

            try:
                loop = asyncio.get_running_loop()
                loop.create_task(
                    retrieval_tracer.trace_retrieval(
                        request_id=request_id,
                        user_id=user_id,
                        model_selected=model_selected,
                        token_budget=token_budget,
                        items_retrieved=items,
                        context_hash=context_hash,
                        context_snapshot=context_text[:200] if context_text else "",
                        retrieval_time_ms=0.0,
                        error=None,
                    )
                )
            except RuntimeError:
                pass

            trace = ObsRetrievalTrace(
                request_id=request_id,
                user_id=user_id,
                timestamp=datetime.utcnow(),
                model_selected=model_selected,
                token_budget=token_budget,
                total_tokens_used=sum(item.token_count for item in items),
                items_retrieved=items,
                tier_breakdown={},
                context_hash=context_hash,
                context_snapshot=context_text[:200] if context_text else "",
                retrieval_time_ms=0.0,
                truncation_events=[],
                error=None,
            )
            retrieval_tracer._trace_cache[request_id] = trace

            logger.info(
                "Retrieval trace logged",
                request_id=request_id,
                total_items=len(items),
            )

            self._owner.retrieval_traces.append(
                RetrievalTrace(
                    request_id=request_id,
                    user_id=user_id,
                    model_selected=model_selected,
                    token_budget=token_budget,
                    items_retrieved=[
                        {
                            "source": item.source,
                            "tier": item.metadata.get("tier", ""),
                            "relevance_score": item.relevance_score,
                            "token_count": item.token_count,
                            "rank": item.rank,
                            "truncated": item.truncated,
                        }
                        for item in items
                    ],
                    scoring_breakdown={},
                    token_allocation={},
                    timestamp=datetime.utcnow().isoformat(),
                )
            )
        except Exception as e:
            logger.error("Failed to log retrieval trace", error=str(e))
