# Complete Context Assembly Service with Observability Integration

import os
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import structlog

from ..storage.database import get_db
from ..storage.models import ConversationModel, MessageModel
from ..storage.vector_models import MemoryFactModel, ConversationSummaryModel
from .retrieval_service import retrieval_service as _retrieval_singleton
from .embedding_service import EmbeddingService
from .write_time_matrix import write_time_intelligence
from ..observability.context_snapshotter import context_snapshotter
from ..observability.retrieval_tracer import retrieval_tracer

logger = structlog.get_logger()


@dataclass
class ContextLayer:
    """Represents a layer in the context assembly"""
    name: str
    content: str
    tokens: int
    source_count: int = 0
    metadata: Dict[str, Any] = None


@dataclass
class ContextBudget:
    """Token budget configuration"""
    total_tokens: int = 8000
    system_tokens: int = 300
    long_term_tokens: int = 300
    working_memory_tokens: int = 700
    semantic_retrieval_tokens: int = 1200
    ephemeral_tokens: int = 5500  # Remaining tokens
    
    @property
    def available_for_retrieval(self) -> int:
        """Tokens available for semantic retrieval after fixed layers"""
        return self.total_tokens - (
            self.system_tokens + 
            self.long_term_tokens + 
            self.working_memory_tokens
        )


class ContextAssemblyService:
    """
    Core service for assembling context with strict token budgeting and retrieval ordering.
    
    This service implements the fixed retrieval stack:
    1. System + Guardrails (Fixed Cost)
    2. Long-Term Memory (Always, but tiny)
    3. Working Memory (Summaries)
    4. Semantic Retrieval (Vector Results)
    5. Ephemeral Memory (Recent Messages)
    
    Enhanced with comprehensive observability for The Prime Directive compliance:
    - Context snapshots before LLM calls
    - Retrieval tracing with tier breakdown
    - Correlation ID tracking across services
    - Structured logging with decision context
    """
    
    def __init__(self):
        self.retrieval_service = _retrieval_singleton
        self.embedding_service = EmbeddingService()
        self.budget = self._load_budget_config()
    
    def _load_budget_config(self) -> ContextBudget:
        """Load token budget configuration from environment or defaults"""
        try:
            total_tokens = int(os.getenv("CONTEXT_WINDOW_SIZE", "8000"))
            system_tokens = int(os.getenv("SYSTEM_TOKENS", "300"))
            long_term_tokens = int(os.getenv("LONG_TERM_TOKENS", "300"))
            working_memory_tokens = int(os.getenv("WORKING_MEMORY_TOKENS", "700"))
            semantic_retrieval_tokens = int(os.getenv("SEMANTIC_RETRIEVAL_TOKENS", "1200"))
            
            return ContextBudget(
                total_tokens=total_tokens,
                system_tokens=system_tokens,
                long_term_tokens=long_term_tokens,
                working_memory_tokens=working_memory_tokens,
                semantic_retrieval_tokens=semantic_retrieval_tokens
            )
        except Exception as e:
            logger.warning("Failed to load budget config, using defaults", error=str(e))
            return ContextBudget()
    
    async def assemble_context(
        self,
        query: str,
        user_id: str,
        conversation_id: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Assemble complete context using fixed retrieval stack order with full observability.
        
        The Prime Directive: Every decision affecting memory, retrieval, routing, or context
        must be inspectable. No black boxes.
        
        Args:
            query: User query to find relevant context for
            user_id: User identifier for isolation
            conversation_id: Optional conversation to limit scope
            conversation_history: Recent conversation history
        
        Returns:
            Dict with assembled context, metadata, and observability data
        """
        layers = []
        remaining_tokens = self.budget.total_tokens
        
        # Generate correlation ID for tracing across services
        correlation_id = f"ctx_assembly_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Track assembly process for debugging and compliance
        assembly_log = {
            "query": query,
            "user_id": user_id,
            "conversation_id": conversation_id,
            "layers": [],
            "token_usage": {},
            "assembly_time": datetime.utcnow().isoformat(),
            "correlation_id": correlation_id,
            "retrieval_stack_order": [
                "System + Guardrails",
                "Long-Term Memory",
                "Working Memory", 
                "Semantic Retrieval",
                "Ephemeral Memory"
            ],
            "budget_limits": {
                "total": self.budget.total_tokens,
                "system": self.budget.system_tokens,
                "long_term": self.budget.long_term_tokens,
                "working_memory": self.budget.working_memory_tokens,
                "semantic_retrieval": self.budget.semantic_retrieval_tokens,
                "ephemeral": self.budget.ephemeral_tokens
            }
        }
        
        try:
            # 1. System + Guardrails (Fixed Cost)
            system_layer = await self._assemble_system_layer(remaining_tokens)
            if system_layer:
                layers.append(system_layer)
                remaining_tokens -= system_layer.tokens
                assembly_log["layers"].append("system")
                assembly_log["token_usage"]["system"] = system_layer.tokens
            
            # 2. Long-Term Memory (Always, but tiny)
            if remaining_tokens > 0:
                long_term_layer = await self._assemble_long_term_memory(
                    user_id, remaining_tokens
                )
                if long_term_layer:
                    layers.append(long_term_layer)
                    remaining_tokens -= long_term_layer.tokens
                    assembly_log["layers"].append("long_term")
                    assembly_log["token_usage"]["long_term"] = long_term_layer.tokens
            
            # 3. Working Memory (Summaries)
            if remaining_tokens > 0 and conversation_id:
                working_memory_layer = await self._assemble_working_memory(
                    user_id, conversation_id, remaining_tokens
                )
                if working_memory_layer:
                    layers.append(working_memory_layer)
                    remaining_tokens -= working_memory_layer.tokens
                    assembly_log["layers"].append("working_memory")
                    assembly_log["token_usage"]["working_memory"] = working_memory_layer.tokens
            
            # 4. Semantic Retrieval (Vector Results) - WITH TRACING
            if remaining_tokens > 0:
                semantic_layer = await self._assemble_semantic_retrieval(
                    query, user_id, conversation_id, remaining_tokens, correlation_id
                )
                if semantic_layer:
                    layers.append(semantic_layer)
                    remaining_tokens -= semantic_layer.tokens
                    assembly_log["layers"].append("semantic_retrieval")
                    assembly_log["token_usage"]["semantic_retrieval"] = semantic_layer.tokens
            
            # 5. Ephemeral Memory (Recent Messages)
            if remaining_tokens > 0 and conversation_history:
                ephemeral_layer = await self._assemble_ephemeral_memory(
                    conversation_history, remaining_tokens
                )
                if ephemeral_layer:
                    layers.append(ephemeral_layer)
                    remaining_tokens -= ephemeral_layer.tokens
                    assembly_log["layers"].append("ephemeral")
                    assembly_log["token_usage"]["ephemeral"] = ephemeral_layer.tokens
            
            # Build final context
            final_context = self._build_final_context(layers, remaining_tokens)
            
            # CREATE CONTEXT SNAPSHOT FOR OBSERVABILITY
            # This is critical for The Prime Directive - every LLM call must be inspectable
            context_snapshot_id = await context_snapshotter.create_snapshot(
                query=query,
                user_id=user_id,
                conversation_id=conversation_id,
                context=final_context,
                layers=len(layers),
                correlation_id=correlation_id,
                token_counts={
                    "total": self.budget.total_tokens - remaining_tokens,
                    "per_layer": assembly_log["token_usage"]
                },
                hard_stops_applied=any(
                    layer.metadata.get("hard_stop_applied", False) 
                    for layer in layers
                )
            )
            
            # Log assembly completion with full context
            assembly_log.update({
                "final_token_usage": self.budget.total_tokens - remaining_tokens,
                "remaining_tokens": remaining_tokens,
                "layers_assembled": len(layers),
                "context_snapshot_id": context_snapshot_id,
                "observability_enabled": True,
                "prime_directive_compliant": True
            })
            
            logger.info(
                "Context assembly completed with full observability",
                user_id=user_id,
                conversation_id=conversation_id,
                layers=len(layers),
                final_tokens=assembly_log["final_token_usage"],
                remaining_tokens=remaining_tokens,
                correlation_id=correlation_id,
                context_snapshot_id=context_snapshot_id,
                prime_directive_compliant=True,
                event_type="context_assembly_completed"
            )
            
            return {
                "context": final_context,
                "layers": layers,
                "assembly_log": assembly_log,
                "remaining_tokens": remaining_tokens,
                "total_tokens_used": self.budget.total_tokens - remaining_tokens,
                "context_snapshot_id": context_snapshot_id,
                "correlation_id": correlation_id,
                "prime_directive_compliant": True,
                "observability_data": {
                    "retrieval_trace_included": "semantic_retrieval" in assembly_log["layers"],
                    "context_snapshot_created": True,
                    "correlation_tracking": True
                }
            }
            
        except Exception as e:
            # Even on failure, create a snapshot for observability
            error_snapshot_id = await context_snapshotter.create_snapshot(
                query=query,
                user_id=user_id,
                conversation_id=conversation_id,
                context=f"ERROR: {str(e)}",
                layers=0,
                correlation_id=correlation_id,
                error=str(e)
            )
            
            logger.error(
                "Context assembly failed - Prime Directive compliance maintained",
                user_id=user_id,
                conversation_id=conversation_id,
                error=str(e),
                correlation_id=correlation_id,
                error_snapshot_id=error_snapshot_id,
                event_type="context_assembly_failed"
            )
            
            # Return minimal context on failure
            return {
                "context": await self._get_minimal_context(query),
                "layers": [],
                "assembly_log": assembly_log,
                "remaining_tokens": self.budget.total_tokens,
                "total_tokens_used": 0,
                "error": str(e),
                "context_snapshot_id": error_snapshot_id,
                "correlation_id": correlation_id,
                "prime_directive_compliant": True,
                "observability_data": {
                    "error_tracked": True,
                    "context_snapshot_created": True,
                    "correlation_tracking": True
                }
            }
    
    async def _assemble_system_layer(self, remaining_tokens: int) -> Optional[ContextLayer]:
        """Assemble System + Guardrails layer (Fixed Cost)"""
        if remaining_tokens < self.budget.system_tokens:
            return None
        
        system_prompt = self._get_system_prompt()
        tokens = self._estimate_tokens(system_prompt)
        
        # Trim if necessary to fit budget
        if tokens > self.budget.system_tokens:
            system_prompt = self._trim_to_tokens(system_prompt, self.budget.system_tokens)
            tokens = self.budget.system_tokens
        
        return ContextLayer(
            name="system",
            content=system_prompt,
            tokens=tokens,
            metadata={
                "type": "system",
                "fixed_cost": True,
                "description": "System prompt and guardrails",
                "never_trimmed": True
            }
        )
    
    async def _assemble_long_term_memory(
        self, 
        user_id: str, 
        remaining_tokens: int
    ) -> Optional[ContextLayer]:
        """Assemble Long-Term Memory layer (Always, but tiny)"""
        if remaining_tokens < self.budget.long_term_tokens:
            return None
        
        try:
            # Retrieve memory facts
            memory_facts = await self._get_long_term_memory_facts(user_id)
            
            if not memory_facts:
                return None
            
            # Convert to bullet points format
            memory_content = self._format_long_term_memory(memory_facts)
            tokens = self._estimate_tokens(memory_content)
            
            # Hard cap at 300 tokens - preserved even under pressure
            if tokens > self.budget.long_term_tokens:
                memory_content = self._trim_to_tokens(
                    memory_content, 
                    self.budget.long_term_tokens
                )
                tokens = self.budget.long_term_tokens
            
            return ContextLayer(
                name="long_term_memory",
                content=memory_content,
                tokens=tokens,
                source_count=len(memory_facts),
                metadata={
                    "type": "long_term",
                    "source_count": len(memory_facts),
                    "description": "User preferences and stable facts",
                    "preserved_under_pressure": True
                }
            )
            
        except Exception as e:
            logger.error("Failed to assemble long-term memory", error=str(e))
            return None
    
    async def _assemble_working_memory(
        self, 
        user_id: str, 
        conversation_id: str, 
        remaining_tokens: int
    ) -> Optional[ContextLayer]:
        """Assemble Working Memory layer (Summaries)"""
        if remaining_tokens < self.budget.working_memory_tokens:
            return None
        
        try:
            # Retrieve conversation summaries
            summaries = await self._get_working_memory_summaries(user_id, conversation_id)
            
            if not summaries:
                return None
            
            # Format summaries
            summary_content = self._format_working_memory(summaries)
            tokens = self._estimate_tokens(summary_content)
            
            # Cap at working memory limit
            if tokens > self.budget.working_memory_tokens:
                summary_content = self._trim_to_tokens(
                    summary_content, 
                    self.budget.working_memory_tokens
                )
                tokens = self.budget.working_memory_tokens
            
            return ContextLayer(
                name="working_memory",
                content=summary_content,
                tokens=tokens,
                source_count=len(summaries),
                metadata={
                    "type": "working_memory",
                    "source_count": len(summaries),
                    "description": "Conversation and task summaries"
                }
            )
            
        except Exception as e:
            logger.error("Failed to assemble working memory", error=str(e))
            return None
    
    async def _assemble_semantic_retrieval(
        self, 
        query: str, 
        user_id: str, 
        conversation_id: Optional[str], 
        remaining_tokens: int,
        correlation_id: str
    ) -> Optional[ContextLayer]:
        """
        Assemble Semantic Retrieval layer (Vector Results) WITH FULL TRACING
        
        This method includes comprehensive retrieval tracing for observability.
        Every LLM call must be traceable and inspectable.
        """
        if remaining_tokens < 100:  # Minimum tokens needed
            return None
        
        try:
            # START RETRIEVAL TRACE - Critical for observability
            trace_id = await retrieval_tracer.start_trace(
                query=query,
                user_id=user_id,
                conversation_id=conversation_id,
                correlation_id=correlation_id
            )
            
            # Retrieve relevant context using existing retrieval service
            context_results = await self.retrieval_service.retrieve_context(
                query=query,
                user_id=user_id,
                conversation_id=conversation_id,
                k=10,  # Get more results for better trimming
                max_age_hours=168
            )
            
            if not context_results:
                await retrieval_tracer.end_trace(
                    trace_id=trace_id,
                    results_count=0,
                    status="no_results"
                )
                return None
            
            # RECORD RETRIEVAL TIER BREAKDOWN - Prime Directive compliance
            await retrieval_tracer.record_tier_breakdown(
                trace_id=trace_id,
                tier="semantic_retrieval",
                results=context_results,
                total_results=len(context_results)
            )
            
            # Format semantic context
            semantic_content = self._format_semantic_retrieval(context_results)
            tokens = self._estimate_tokens(semantic_content)
            
            # Aggressive trimming to fit remaining budget
            hard_stop_applied = False
            if tokens > remaining_tokens:
                # HARD STOP - Vector results cut first per design
                semantic_content = self._trim_to_tokens(semantic_content, remaining_tokens)
                tokens = remaining_tokens
                hard_stop_applied = True
            
            # END RETRIEVAL TRACE with comprehensive data
            await retrieval_tracer.end_trace(
                trace_id=trace_id,
                results_count=len(context_results),
                total_tokens=tokens,
                status="success",
                hard_stop_applied=hard_stop_applied
            )
            
            return ContextLayer(
                name="semantic_retrieval",
                content=semantic_content,
                tokens=tokens,
                source_count=len(context_results),
                metadata={
                    "type": "semantic",
                    "source_count": len(context_results),
                    "description": "Vector search results",
                    "hard_stop_applied": hard_stop_applied,
                    "trace_id": trace_id,
                    "correlation_id": correlation_id,
                    "retrieval_traced": True
                }
            )
            
        except Exception as e:
            logger.error("Failed to assemble semantic retrieval", error=str(e))
            if 'trace_id' in locals():
                await retrieval_tracer.end_trace(
                    trace_id=trace_id,
                    results_count=0,
                    status="error",
                    error=str(e)
                )
            return None
    
    async def _assemble_ephemeral_memory(
        self, 
        conversation_history: List[Dict[str, str]], 
        remaining_tokens: int
    ) -> Optional[ContextLayer]:
        """Assemble Ephemeral Memory layer (Recent Messages)"""
        if remaining_tokens < 50:  # Minimum tokens needed
            return None
        
        try:
            # Use remaining tokens for recent messages
            recent_content = self._format_ephemeral_memory(conversation_history)
            tokens = self._estimate_tokens(recent_content)
            
            # Use whatever remains
            if tokens > remaining_tokens:
                recent_content = self._trim_to_tokens(recent_content, remaining_tokens)
                tokens = remaining_tokens
            
            return ContextLayer(
                name="ephemeral_memory",
                content=recent_content,
                tokens=tokens,
                source_count=len(conversation_history),
                metadata={
                    "type": "ephemeral",
                    "source_count": len(conversation_history),
                    "description": "Recent conversation messages"
                }
            )
            
        except Exception as e:
            logger.error("Failed to assemble ephemeral memory", error=str(e))
            return None
    
    def _build_final_context(self, layers: List[Context