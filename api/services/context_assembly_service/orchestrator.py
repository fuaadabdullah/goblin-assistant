"""
Context Assembly Orchestrator.

Slim coordinator that wires together the five retrieval layers in fixed order,
tracks token budgets, and produces the final context payload. All heavy
logic lives in the individual layer modules.
"""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from ...observability.context_snapshotter import context_snapshotter
from ...utils.tokenizer import count_tokens as _count_tokens, trim_to_tokens as _trim_to_tokens_util
from . import budget_manager as bm
from .ephemeral_layer import assemble_ephemeral_memory
from .long_term_layer import assemble_long_term_memory
from .models import ContextBudget, ContextLayer
from .semantic_layer import assemble_semantic_retrieval, _get_retrieval_service
from .system_layer import assemble_system_layer
from .working_memory_layer import assemble_working_memory

logger = structlog.get_logger()


class ContextAssemblyService:
    """
    Core service for assembling context with strict token budgeting and retrieval ordering.

    Retrieval Stack (Fixed Order):
    1. System + Guardrails (Fixed Cost)
    2. Long-Term Memory (Always, but tiny)
    3. Working Memory (Summaries)
    4. Semantic Retrieval (Vector Results)
    5. Ephemeral Memory (Recent Messages)

    Hard Stops: If you run out of tokens, vector results get cut first, then
    working memory. Long-term memory is last to go. System instructions never go.
    """

    def __init__(self) -> None:
        self._retrieval_service = None
        self._embedding_service = None
        self.default_budget = bm.load_budget_config()
        self.model_context_windows = bm.load_model_context_windows()
        self.response_reserve_tokens = int(
            os.getenv("CONTEXT_RESPONSE_RESERVE_TOKENS", "1024")
        )

    @property
    def retrieval_service(self):
        if self._retrieval_service is None:
            self._retrieval_service = _get_retrieval_service()
        return self._retrieval_service

    @property
    def embedding_service(self):
        if self._embedding_service is None:
            from ..embedding_service import EmbeddingService
            self._embedding_service = EmbeddingService()
        return self._embedding_service

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def assemble_context(
        self,
        query: str,
        user_id: str,
        conversation_id: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        model: Optional[str] = None,
        max_context_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Assemble complete context using fixed retrieval stack order.

        Returns:
            Dict with assembled context and metadata.
        """
        budget = bm.derive_budget(
            default_budget=self.default_budget,
            model_context_windows=self.model_context_windows,
            response_reserve_tokens=self.response_reserve_tokens,
            model=model,
            max_context_tokens=max_context_tokens,
        )
        layers: List[ContextLayer] = []
        remaining_tokens = budget.total_tokens

        correlation_id = f"ctx_assembly_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        assembly_log: Dict[str, Any] = {
            "query": query,
            "user_id": user_id,
            "conversation_id": conversation_id,
            "model": model,
            "layers": [],
            "token_usage": {},
            "assembly_time": datetime.utcnow().isoformat(),
            "correlation_id": correlation_id,
        }
        truncation_events: List[str] = []

        try:
            # 1. System + Guardrails
            system_layer = await assemble_system_layer(remaining_tokens, budget)
            if system_layer:
                layers.append(system_layer)
                remaining_tokens -= system_layer.tokens
                assembly_log["layers"].append("system")
                assembly_log["token_usage"]["system"] = system_layer.tokens

            # 2. Long-Term Memory
            if remaining_tokens > 0:
                long_term_layer = await assemble_long_term_memory(
                    user_id, remaining_tokens, budget
                )
                if long_term_layer:
                    layers.append(long_term_layer)
                    remaining_tokens -= long_term_layer.tokens
                    assembly_log["layers"].append("long_term")
                    assembly_log["token_usage"]["long_term"] = long_term_layer.tokens

            # 3. Working Memory
            if remaining_tokens > 0 and conversation_id:
                working_memory_layer = await assemble_working_memory(
                    user_id, conversation_id, remaining_tokens, budget
                )
                if working_memory_layer:
                    layers.append(working_memory_layer)
                    remaining_tokens -= working_memory_layer.tokens
                    assembly_log["layers"].append("working_memory")
                    assembly_log["token_usage"]["working_memory"] = (
                        working_memory_layer.tokens
                    )

            # 4. Semantic Retrieval
            if remaining_tokens > 0:
                semantic_layer = await assemble_semantic_retrieval(
                    query,
                    user_id,
                    conversation_id,
                    remaining_tokens,
                    correlation_id,
                    budget,
                )
                if semantic_layer:
                    layers.append(semantic_layer)
                    remaining_tokens -= semantic_layer.tokens
                    assembly_log["layers"].append("semantic_retrieval")
                    assembly_log["token_usage"]["semantic_retrieval"] = (
                        semantic_layer.tokens
                    )
                    if semantic_layer.metadata and semantic_layer.metadata.get(
                        "hard_stop_applied"
                    ):
                        truncation_events.append("semantic_retrieval_truncated")

                if hasattr(self.retrieval_service, "get_degraded_status"):
                    degraded_status = self.retrieval_service.get_degraded_status()
                    if degraded_status.get("degraded_mode"):
                        assembly_log["degraded_mode"] = True
                        assembly_log["degraded_reason"] = degraded_status.get("reason")

            # 5. Ephemeral Memory
            if remaining_tokens > 0 and conversation_history:
                ephemeral_layer = await assemble_ephemeral_memory(
                    conversation_history, remaining_tokens, budget
                )
                if ephemeral_layer:
                    layers.append(ephemeral_layer)
                    remaining_tokens -= ephemeral_layer.tokens
                    assembly_log["layers"].append("ephemeral")
                    assembly_log["token_usage"]["ephemeral"] = ephemeral_layer.tokens
                    if ephemeral_layer.metadata and ephemeral_layer.metadata.get(
                        "truncated"
                    ):
                        truncation_events.append("ephemeral_memory_truncated")
                        if ephemeral_layer.metadata.get("summary_fallback_applied"):
                            truncation_events.append(
                                "ephemeral_summary_fallback_applied"
                            )

            if truncation_events:
                assembly_log["degraded_mode"] = True
                existing_reason = assembly_log.get("degraded_reason")
                truncation_reason = "context_truncated:" + ",".join(truncation_events)
                assembly_log["degraded_reason"] = (
                    f"{existing_reason}; {truncation_reason}"
                    if existing_reason
                    else truncation_reason
                )
                assembly_log["truncation_warnings"] = truncation_events

            # Build final context
            final_context = self._build_final_context(layers, remaining_tokens, budget)

            context_snapshot_id = await context_snapshotter.create_snapshot(
                query=query,
                user_id=user_id,
                conversation_id=conversation_id,
                context=final_context,
                layers=len(layers),
                correlation_id=correlation_id,
            )

            assembly_log["final_token_usage"] = budget.total_tokens - remaining_tokens
            assembly_log["remaining_tokens"] = remaining_tokens
            assembly_log["layers_assembled"] = len(layers)
            assembly_log["context_snapshot_id"] = context_snapshot_id

            logger.info(
                "Context assembly completed",
                user_id=user_id,
                conversation_id=conversation_id,
                layers=len(layers),
                final_tokens=assembly_log["final_token_usage"],
                remaining_tokens=remaining_tokens,
                correlation_id=correlation_id,
                context_snapshot_id=context_snapshot_id,
            )

            return {
                "context": final_context,
                "layers": layers,
                "assembly_log": assembly_log,
                "remaining_tokens": remaining_tokens,
                "total_tokens_used": budget.total_tokens - remaining_tokens,
                "context_snapshot_id": context_snapshot_id,
                "degraded_mode": assembly_log.get("degraded_mode", False),
                "degraded_reason": assembly_log.get("degraded_reason"),
                "truncation_warnings": truncation_events,
                "summary_fallback_applied": "ephemeral_summary_fallback_applied"
                in truncation_events,
            }

        except Exception as e:
            logger.error(
                "Context assembly failed",
                user_id=user_id,
                conversation_id=conversation_id,
                error=str(e),
                correlation_id=correlation_id,
            )
            return {
                "context": await self._get_minimal_context(query),
                "layers": [],
                "assembly_log": assembly_log,
                "remaining_tokens": budget.total_tokens,
                "total_tokens_used": 0,
                "error": str(e),
                "context_snapshot_id": None,
                "degraded_mode": True,
                "degraded_reason": str(e),
            }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_final_context(
        layers: List[ContextLayer],
        remaining_tokens: int,
        budget: ContextBudget,
    ) -> str:
        """Build final context string from assembled layers."""
        context_parts = []
        for layer in layers:
            context_parts.append(f"[{layer.name.upper()}]\n{layer.content}\n")

        final_context = "\n".join(context_parts)

        final_tokens = _count_tokens(final_context)
        if final_tokens > (budget.total_tokens - remaining_tokens):
            final_context = _trim_to_tokens_util(
                final_context, budget.total_tokens - remaining_tokens
            )
        return final_context

    @staticmethod
    async def _get_minimal_context(query: str) -> str:
        """Get minimal context when assembly fails."""
        return (
            "You are Goblin Assistant — a sharp, resourceful AI helper. "
            "Use the following query to inform your response:\n\n"
            f"Query: {query}\n\n"
            "Note: Operating with minimal context due to system constraints. "
            "Answer as best you can."
        )


# Module-level singleton
context_assembly_service = ContextAssemblyService()
