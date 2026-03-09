"""
Semantic retrieval service using pgvector with hybrid scoring
"""

import os
from typing import List, Dict, Optional, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, func
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
import math
import structlog

from ..storage.database import get_db
from ..storage.vector_models import EmbeddingModel, ConversationSummaryModel, MemoryFactModel
from ..storage.models import UserModel, ConversationModel
from .embedding_service import EmbeddingService, EmbeddingProviderUnavailableError


logger = structlog.get_logger()


class RetrievalService:
    """Service for semantic retrieval with hybrid scoring"""
    
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.semantic_weight = 0.7
        self.recency_weight = 0.2
        self.source_priority_weight = 0.1
        self._degraded_mode = False
        self._degraded_reason: Optional[str] = None

    def get_degraded_status(self) -> Dict[str, Any]:
        return {
            "degraded_mode": self._degraded_mode,
            "reason": self._degraded_reason,
        }

    def _set_degraded(self, reason: str) -> None:
        self._degraded_mode = True
        self._degraded_reason = reason

    def _clear_degraded(self) -> None:
        self._degraded_mode = False
        self._degraded_reason = None
        
    async def retrieve_context(
        self, 
        query: str, 
        user_id: str, 
        conversation_id: Optional[str] = None,
        k: int = 5,
        max_age_hours: int = 168  # 7 days default
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant context using memory stratification priority
        
        Args:
            query: User query to find relevant context for
            user_id: User identifier for isolation
            conversation_id: Optional conversation to limit scope
            k: Number of results to return
            max_age_hours: Maximum age of embeddings to consider
        """
        if not query or not user_id:
            return []
        self._clear_degraded()
            
        try:
            # Generate query embedding
            try:
                query_embedding = await self.embedding_service.embed_text(query)
            except EmbeddingProviderUnavailableError as embed_err:
                self._set_degraded(str(embed_err))
                return []
            except Exception as embed_err:
                self._set_degraded(str(embed_err))
                return []

            if not query_embedding:
                return []
                
            # Retrieve context using stratified priority
            results = await self._stratified_retrieval(
                query_embedding=query_embedding,
                query=query,
                user_id=user_id,
                conversation_id=conversation_id,
                k=k,
                max_age_hours=max_age_hours
            )
            
            # Log retrieval trace to observability system
            try:
                # Import here to avoid circular imports
                from .observability_service import observability_service

                # Build retrieval trace data
                total_tokens_used = sum(len(r.get("content", "")) // 4 for r in results)
                retrieval_trace_data = {
                    "request_id": f"retrieval_{datetime.utcnow().isoformat()}",
                    "user_id": user_id,
                    "model_selected": "retrieval_service",
                    "token_budget": total_tokens_used,
                    "retrieval_result": {
                        "layers": [
                            {
                                "name": result.get("source_type", "unknown"),
                                "tokens": len(result.get("content", "")) // 4,  # Rough token estimation
                                "score": result.get("score", 0.0),
                                "original_tokens": len(result.get("content", "")) // 4
                            }
                            for result in results
                        ]
                    }
                }

                observability_service.log_retrieval_trace(**retrieval_trace_data)
            except Exception as e:
                logger.warning(
                    "failed to log retrieval trace to observability",
                    error=str(e),
                    user_id=user_id,
                    conversation_id=conversation_id,
                )
            
            return results
            
        except Exception as e:
            logger.error(
                "error in retrieve_context",
                error=str(e),
                user_id=user_id,
                conversation_id=conversation_id,
            )
            return []
    
    async def _stratified_retrieval(
        self,
        query_embedding: List[float],
        query: str,
        user_id: str,
        conversation_id: Optional[str] = None,
        k: int = 5,
        max_age_hours: int = 168
    ) -> List[Dict[str, Any]]:
        """
        Retrieve context using memory stratification priority:
        1. Long-term memory facts (highest priority)
        2. Working memory summaries
        3. Relevant vector-retrieved messages
        4. Ephemeral recent messages
        """
        
        all_results = []
        
        # 1. Long-term memory facts (highest priority)
        memory_facts = await self._retrieve_memory_facts_stratified(
            query_embedding=query_embedding,
            query=query,
            user_id=user_id,
            k=min(k, 3)  # Limit to 3 memory facts
        )
        all_results.extend(memory_facts)
        
        # 2. Working memory summaries
        summaries = await self._retrieve_summaries_stratified(
            query_embedding=query_embedding,
            query=query,
            user_id=user_id,
            conversation_id=conversation_id,
            k=min(k, 2)  # Limit to 2 summaries
        )
        all_results.extend(summaries)
        
        # 3. Relevant vector-retrieved messages
        messages = await self._retrieve_messages_stratified(
            query_embedding=query_embedding,
            query=query,
            user_id=user_id,
            conversation_id=conversation_id,
            k=min(k, 3)  # Limit to 3 messages
        )
        all_results.extend(messages)
        
        # 4. Ephemeral recent messages (if we still need more)
        remaining_k = k - len(all_results)
        if remaining_k > 0:
            recent_messages = await self._retrieve_recent_messages(
                user_id=user_id,
                conversation_id=conversation_id,
                k=remaining_k
            )
            all_results.extend(recent_messages)
        
        # Sort by score and return top k
        all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return all_results[:k]
    
    async def _retrieve_memory_facts_stratified(
        self,
        query_embedding: List[float],
        query: str,
        user_id: str,
        k: int = 3
    ) -> List[Dict[str, Any]]:
        """Retrieve long-term memory facts with high priority scoring"""
        
        try:
            async with get_db() as session:
                query_sql = text("""
                    SELECT 
                        mf.id,
                        mf.fact_text as content,
                        mf.category,
                        mf.metadata,
                        mf.created_at,
                        (1 - (mf.fact_embedding <=> :query_embedding)) * 1.5 as score  -- Boost memory facts
                    FROM memory_facts mf
                    WHERE mf.user_id = :user_id
                    ORDER BY score DESC
                    LIMIT :k
                """)
                
                result = await session.execute(query_sql, {
                    "query_embedding": query_embedding,
                    "user_id": user_id,
                    "k": k
                })
                
                rows = result.fetchall()
                
                return [{
                    "id": row.id,
                    "content": row.content,
                    "source_type": "memory",
                    "source_id": row.id,
                    "metadata": {
                        "category": row.category,
                        "source": "long_term_memory"
                    },
                    "created_at": row.created_at,
                    "score": float(row.score) if row.score else 0.0
                } for row in rows]
                
        except Exception as e:
            logger.error(
                "error retrieving memory facts (stratified)",
                error=str(e),
                user_id=user_id,
            )
            return []
    
    async def _retrieve_summaries_stratified(
        self,
        query_embedding: List[float],
        query: str,
        user_id: str,
        conversation_id: Optional[str] = None,
        k: int = 2
    ) -> List[Dict[str, Any]]:
        """Retrieve working memory summaries"""
        
        try:
            async with get_db() as session:
                # Build WHERE clause
                where_clauses = ["cs.user_id = :user_id"]
                params = {
                    "user_id": user_id,
                    "query_embedding": query_embedding,
                    "k": k
                }
                
                if conversation_id:
                    where_clauses.append("cs.conversation_id = :conversation_id")
                    params["conversation_id"] = conversation_id
                
                where_clause = " AND ".join(where_clauses)
                
                query_sql = text(f"""
                    SELECT 
                        cs.id,
                        cs.conversation_id,
                        cs.summary_text as content,
                        cs.created_at,
                        (1 - (cs.summary_embedding <=> :query_embedding)) * 1.2 as score  -- Boost summaries
                    FROM conversation_summaries cs
                    WHERE {where_clause}
                    ORDER BY score DESC
                    LIMIT :k
                """)
                
                result = await session.execute(query_sql, params)
                rows = result.fetchall()
                
                return [{
                    "id": row.id,
                    "content": row.content,
                    "source_type": "summary",
                    "source_id": row.conversation_id,
                    "metadata": {
                        "conversation_id": row.conversation_id,
                        "source": "working_memory"
                    },
                    "created_at": row.created_at,
                    "score": float(row.score) if row.score else 0.0
                } for row in rows]
                
        except Exception as e:
            logger.error(
                "error retrieving summaries (stratified)",
                error=str(e),
                user_id=user_id,
                conversation_id=conversation_id,
            )
            return []
    
    async def _retrieve_messages_stratified(
        self,
        query_embedding: List[float],
        query: str,
        user_id: str,
        conversation_id: Optional[str] = None,
        k: int = 3
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant messages with semantic search"""
        
        try:
            async with get_db() as session:
                # Build WHERE clause
                where_clauses = ["e.user_id = :user_id", "e.source_type = 'message'"]
                params = {
                    "user_id": user_id,
                    "query_embedding": query_embedding,
                    "k": k
                }
                
                if conversation_id:
                    where_clauses.append("e.conversation_id = :conversation_id")
                    params["conversation_id"] = conversation_id
                
                where_clause = " AND ".join(where_clauses)
                
                query_sql = text(f"""
                    SELECT 
                        e.id,
                        e.content,
                        e.conversation_id,
                        e.metadata,
                        e.created_at,
                        (
                            0.8 * (1 - (e.embedding <=> :query_embedding)) +  -- Semantic similarity
                            0.2 * EXP(-0.001 * EXTRACT(EPOCH FROM (NOW() - e.created_at)))  -- Recency
                        ) as score
                    FROM embeddings e
                    WHERE {where_clause}
                    ORDER BY score DESC
                    LIMIT :k
                """)
                
                result = await session.execute(query_sql, params)
                rows = result.fetchall()
                
                return [{
                    "id": row.id,
                    "content": row.content,
                    "source_type": "message",
                    "source_id": row.conversation_id,
                    "metadata": row.metadata,
                    "created_at": row.created_at,
                    "score": float(row.score) if row.score else 0.0
                } for row in rows]
                
        except Exception as e:
            logger.error(
                "error retrieving messages (stratified)",
                error=str(e),
                user_id=user_id,
                conversation_id=conversation_id,
            )
            return []
    
    async def _retrieve_recent_messages(
        self,
        user_id: str,
        conversation_id: Optional[str] = None,
        k: int = 2
    ) -> List[Dict[str, Any]]:
        """Retrieve recent ephemeral messages"""
        
        try:
            async with get_db() as session:
                # Build WHERE clause
                where_clauses = ["m.user_id = :user_id"]
                params = {
                    "user_id": user_id,
                    "k": k
                }
                
                if conversation_id:
                    where_clauses.append("m.conversation_id = :conversation_id")
                    params["conversation_id"] = conversation_id
                
                where_clause = " AND ".join(where_clauses)
                
                query_sql = text(f"""
                    SELECT 
                        m.id,
                        m.content,
                        m.conversation_id,
                        m.role,
                        m.created_at
                    FROM messages m
                    WHERE {where_clause}
                    ORDER BY m.created_at DESC
                    LIMIT :k
                """)
                
                result = await session.execute(query_sql, params)
                rows = result.fetchall()
                
                return [{
                    "id": row.id,
                    "content": row.content,
                    "source_type": "ephemeral",
                    "source_id": row.conversation_id,
                    "metadata": {
                        "role": row.role,
                        "source": "ephemeral_memory"
                    },
                    "created_at": row.created_at,
                    "score": 0.1  # Low priority for ephemeral messages
                } for row in rows]
                
        except Exception as e:
            logger.error(
                "error retrieving recent messages",
                error=str(e),
                user_id=user_id,
                conversation_id=conversation_id,
            )
            return []
    
    async def _hybrid_search(
        self, 
        query_embedding: List[float], 
        user_id: str, 
        conversation_id: Optional[str],
        k: int,
        max_age_hours: int
    ) -> List[Dict[str, Any]]:
        """Execute pgvector query with hybrid scoring"""
        
        async with get_db() as session:
            # Build dynamic WHERE clause
            where_clauses = ["e.user_id = :user_id"]
            params = {
                "user_id": user_id,
                "query_embedding": query_embedding,
                "k": k,
                "max_age": datetime.utcnow() - timedelta(hours=max_age_hours)
            }
            
            if conversation_id:
                where_clauses.append("e.conversation_id = :conversation_id")
                params["conversation_id"] = conversation_id
            
            where_clause = " AND ".join(where_clauses)
            
            # pgvector query with custom scoring function
            query = text(f"""
                SELECT 
                    e.id,
                    e.user_id,
                    e.conversation_id,
                    e.source_type,
                    e.source_id,
                    e.content,
                    e.metadata,
                    e.created_at,
                    (
                        :semantic_weight * (1 - (e.embedding <=> :query_embedding)) +  -- semantic similarity
                        :recency_weight * EXP(-0.001 * EXTRACT(EPOCH FROM (NOW() - e.created_at))) +  -- recency decay
                        :source_priority_weight * CASE 
                            WHEN e.source_type = 'summary' THEN 1.0
                            WHEN e.source_type = 'task' THEN 0.8
                            WHEN e.source_type = 'message' THEN 0.5
                            ELSE 0.3
                        END  -- source priority
                    ) as final_score
                FROM embeddings e
                WHERE {where_clause}
                AND e.created_at >= :max_age
                ORDER BY final_score DESC
                LIMIT :k
            """)
            
            params.update({
                "semantic_weight": self.semantic_weight,
                "recency_weight": self.recency_weight,
                "source_priority_weight": self.source_priority_weight
            })
            
            result = await session.execute(query, params)
            rows = result.fetchall()
            
            # Convert to list of dicts
            results = []
            for row in rows:
                results.append({
                    "id": row.id,
                    "user_id": row.user_id,
                    "conversation_id": row.conversation_id,
                    "source_type": row.source_type,
                    "source_id": row.source_id,
                    "content": row.content,
                    "metadata": row.metadata,
                    "created_at": row.created_at,
                    "score": float(row.final_score) if row.final_score else 0.0
                })
            
            return results
    
    def _group_and_rank_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Group results by source type and apply final ranking"""
        
        # Group by source type
        grouped = {
            "summary": [],
            "task": [],
            "message": [],
            "memory": []
        }
        
        for result in results:
            source_type = result["source_type"]
            if source_type in grouped:
                grouped[source_type].append(result)
        
        # Apply source-specific limits and ranking
        final_results = []
        
        # Summaries get highest priority - take top 2
        final_results.extend(sorted(grouped["summary"], key=lambda x: x["score"], reverse=True)[:2])
        
        # Tasks - take top 2
        final_results.extend(sorted(grouped["task"], key=lambda x: x["score"], reverse=True)[:2])
        
        # Messages - take top 3
        final_results.extend(sorted(grouped["message"], key=lambda x: x["score"], reverse=True)[:3])
        
        # Memory facts - take top 2
        final_results.extend(sorted(grouped["memory"], key=lambda x: x["score"], reverse=True)[:2])
        
        # Sort final results by score
        final_results.sort(key=lambda x: x["score"], reverse=True)
        
        return final_results
    
    async def retrieve_conversation_summaries(
        self, 
        user_id: str, 
        conversation_ids: List[str], 
        k: int = 3
    ) -> List[Dict[str, Any]]:
        """Retrieve summaries for specific conversations"""
        
        if not conversation_ids:
            return []
            
        async with get_db() as session:
            query = text("""
                SELECT 
                    cs.id,
                    cs.conversation_id,
                    cs.summary_text,
                    cs.created_at,
                    (
                        1 - (cs.summary_embedding <=> :query_embedding)
                    ) as similarity_score
                FROM conversation_summaries cs
                WHERE cs.conversation_id = ANY(:conversation_ids)
                ORDER BY similarity_score DESC
                LIMIT :k
            """)
            
            # Use a generic query embedding or the most recent conversation summary
            # For now, we'll just order by created_at
            query = text("""
                SELECT 
                    cs.id,
                    cs.conversation_id,
                    cs.summary_text,
                    cs.created_at
                FROM conversation_summaries cs
                WHERE cs.conversation_id = ANY(:conversation_ids)
                ORDER BY cs.created_at DESC
                LIMIT :k
            """)
            
            result = await session.execute(query, {
                "conversation_ids": conversation_ids,
                "k": k
            })
            
            rows = result.fetchall()
            
            return [{
                "id": row.id,
                "conversation_id": row.conversation_id,
                "summary_text": row.summary_text,
                "created_at": row.created_at,
                "source_type": "summary"
            } for row in rows]
    
    async def retrieve_memory_facts(
        self, 
        user_id: str, 
        query: str, 
        categories: Optional[List[str]] = None,
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant memory facts"""
        
        if not query:
            return []
            
        try:
            try:
                query_embedding = await self.embedding_service.embed_text(query)
            except EmbeddingProviderUnavailableError as embed_err:
                self._set_degraded(str(embed_err))
                return []
            except Exception as embed_err:
                self._set_degraded(str(embed_err))
                return []

            if not query_embedding:
                return []
                
            async with get_db() as session:
                # Build WHERE clause for categories
                where_clauses = ["mf.user_id = :user_id"]
                params = {
                    "user_id": user_id,
                    "query_embedding": query_embedding,
                    "k": k
                }
                
                if categories:
                    where_clauses.append("mf.category = ANY(:categories)")
                    params["categories"] = categories
                
                where_clause = " AND ".join(where_clauses)
                
                query = text(f"""
                    SELECT 
                        mf.id,
                        mf.fact_text,
                        mf.category,
                        mf.metadata,
                        mf.created_at,
                        (1 - (mf.fact_embedding <=> :query_embedding)) as similarity_score
                    FROM memory_facts mf
                    WHERE {where_clause}
                    ORDER BY similarity_score DESC
                    LIMIT :k
                """)
                
                result = await session.execute(query, params)
                rows = result.fetchall()
                
                return [{
                    "id": row.id,
                    "fact_text": row.fact_text,
                    "category": row.category,
                    "metadata": row.metadata,
                    "created_at": row.created_at,
                    "score": float(row.similarity_score) if row.similarity_score else 0.0,
                    "source_type": "memory"
                } for row in rows]
                
        except Exception as e:
            logger.error(
                "error retrieving memory facts",
                error=str(e),
                user_id=user_id,
                categories=categories,
            )
            return []
    
    async def get_context_bundle(
        self, 
        query: str, 
        user_id: str, 
        conversation_id: Optional[str] = None,
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """
        Get a complete context bundle for a query
        
        Returns a structured bundle with different types of context
        """
        context_bundle = {
            "query": query,
            "user_id": user_id,
            "conversation_id": conversation_id,
            "retrieved_at": datetime.utcnow().isoformat(),
            "summaries": [],
            "messages": [],
            "tasks": [],
            "memory_facts": [],
            "total_tokens": 0,
            "metadata": {}
        }
        
        # Retrieve different types of context
        all_context = await self.retrieve_context(
            query=query,
            user_id=user_id,
            conversation_id=conversation_id,
            k=10
        )
        
        # Group by source type
        for item in all_context:
            if item["source_type"] == "summary":
                context_bundle["summaries"].append(item)
            elif item["source_type"] == "message":
                context_bundle["messages"].append(item)
            elif item["source_type"] == "task":
                context_bundle["tasks"].append(item)
            elif item["source_type"] == "memory":
                context_bundle["memory_facts"].append(item)
        
        # Estimate token usage
        total_tokens = 0
        for source_type in ["summaries", "messages", "tasks", "memory_facts"]:
            for item in context_bundle[source_type]:
                # Rough token estimation (4 chars per token)
                total_tokens += len(item["content"]) // 4
        
        context_bundle["total_tokens"] = total_tokens
        context_bundle["metadata"]["context_count"] = len(all_context)
        context_bundle["metadata"].update(self.get_degraded_status())
        
        return context_bundle


class ContextBuilder:
    """Helper class to build contextual prompts"""
    
    @staticmethod
    def build_contextual_prompt(
        user_message: str,
        context_bundle: Dict[str, Any],
        conversation_history: List[Dict[str, str]],
        max_context_tokens: int = 1500
    ) -> List[Dict[str, str]]:
        """
        Build a prompt with relevant context
        
        Args:
            user_message: Current user message
            context_bundle: Retrieved context bundle
            conversation_history: Recent conversation history
            max_context_tokens: Maximum tokens for context
        
        Returns:
            List of messages for the LLM prompt
        """
        # Build context text
        context_parts = []
        
        # Add summaries first (highest priority)
        for summary in context_bundle.get("summaries", []):
            context_parts.append(f"[SUMMARY] {summary['content']}")
        
        # Add tasks
        for task in context_bundle.get("tasks", []):
            context_parts.append(f"[TASK] {task['content']}")
        
        # Add memory facts
        for fact in context_bundle.get("memory_facts", []):
            context_parts.append(f"[MEMORY] {fact['content']}")
        
        # Add recent messages
        for message in context_bundle.get("messages", []):
            context_parts.append(f"[MESSAGE] {message['content']}")
        
        # Join context
        context_text = "\n\n".join(context_parts)
        
        # Truncate if too long (rough token estimation)
        max_chars = max_context_tokens * 4
        if len(context_text) > max_chars:
            context_text = context_text[:max_chars]
        
        # Build system prompt
        system_prompt = f"""You are Goblin Assistant — a sharp, resourceful AI helper. Use the following context to inform your responses:

{context_text}

Conversation history:
"""
        
        # Add recent conversation history
        recent_history = conversation_history[-5:]  # Last 5 messages
        for msg in recent_history:
            system_prompt += f"{msg['role']}: {msg['content']}\n"
        
        # Add current user message
        system_prompt += f"user: {user_message}"
        
        return [{"role": "system", "content": system_prompt}]


# Module-level singleton — reuse across imports
retrieval_service = RetrievalService()