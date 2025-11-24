"""
RAG (Retrieval-Augmented Generation) system for Goblin Assistant.
Handles context retrieval, prompt building, and provider orchestration.
"""

import re
from typing import Dict, Any, List, AsyncGenerator, Optional
from dataclasses import dataclass

from .router import ProviderRouter, TaskType
from ..indexer.indexer import VectorIndexer


@dataclass
class RAGContext:
    """Retrieved context for RAG."""

    content: str
    file_path: str
    start_line: int
    end_line: int
    commit_sha: Optional[str] = None
    score: float = 0.0


@dataclass
class RAGResponse:
    """Complete RAG response."""

    answer: str
    contexts: List[RAGContext]
    usage: Dict[str, int]
    hit_rate: float
    provider: str
    model: str


class RAGSystem:
    """RAG system with retrieval, reranking, and prompt building."""

    SYSTEM_PROMPT = """You are Goblin Assistant. Use ONLY the CONTEXT below. If necessary information is not present, reply: "I don't know — check {file_path}" and propose exact next steps.

CONTEXT 1: file: {file_path}, lines {start_line}-{end_line}
---CODE---
{content}
---END---

{additional_context}

User: {query}"""

    def __init__(self, indexer: VectorIndexer, router: ProviderRouter):
        self.indexer = indexer
        self.router = router
        self.max_contexts = 3
        self.chunk_overlap = 50
        self.max_tokens_per_chunk = 600

    async def query(
        self,
        query: str,
        user_id: str = "anonymous",
        task_type: TaskType = TaskType.CHAT,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Perform RAG query and return complete response.
        """
        # Retrieve relevant contexts
        contexts = await self._retrieve_contexts(query, top_k=20)

        # Rerank and select top contexts
        selected_contexts = self._rerank_contexts(contexts, query)[: self.max_contexts]

        # Build prompt
        prompt = self._build_prompt(query, selected_contexts)

        # Get provider and generate response
        provider = await self.router.get_provider(task_type, user_id)
        response = provider.generate(prompt)

        # Calculate hit rate
        hit_rate = len(selected_contexts) / max(len(contexts), 1) if contexts else 0

        return {
            "answer": response.content,
            "contexts": [
                {
                    "file_path": ctx.file_path,
                    "start_line": ctx.start_line,
                    "end_line": ctx.end_line,
                    "commit_sha": ctx.commit_sha,
                    "score": ctx.score,
                }
                for ctx in selected_contexts
            ],
            "usage": response.usage,
            "hit_rate": hit_rate,
            "provider": provider.name,
            "model": response.model,
        }

    async def stream_query(
        self,
        query: str,
        user_id: str = "anonymous",
        task_type: TaskType = TaskType.CHAT,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream RAG query response.
        """
        # Retrieve and prepare contexts
        contexts = await self._retrieve_contexts(query, top_k=20)
        selected_contexts = self._rerank_contexts(contexts, query)[: self.max_contexts]
        prompt = self._build_prompt(query, selected_contexts)

        # Get provider and stream response
        provider = await self.router.get_provider(task_type, user_id)

        async for chunk in provider.stream(prompt):
            yield {
                "content": chunk.content,
                "finish_reason": chunk.finish_reason,
                "usage": chunk.usage,
            }

    async def execute_workflow(
        self, workflow: Dict[str, Any], user_id: str
    ) -> Dict[str, Any]:
        """
        Execute a workflow (for Continue integration).
        """
        # This is a placeholder for workflow execution
        # In production, this would handle complex multi-step workflows
        action = workflow.get("action", "")
        params = workflow.get("params", {})

        if action == "analyze_code":
            return await self.query(
                f"Analyze this code: {params.get('code', '')}",
                user_id=user_id,
                task_type=TaskType.CODE,
            )
        elif action == "suggest_fix":
            return await self.query(
                f"Suggest a fix for: {params.get('issue', '')}",
                user_id=user_id,
                task_type=TaskType.CODE,
            )
        else:
            return {"error": f"Unknown workflow action: {action}"}

    async def _retrieve_contexts(self, query: str, top_k: int = 20) -> List[RAGContext]:
        """Retrieve relevant contexts from the index."""
        try:
            # Get embeddings for query
            query_embedding = await self._get_query_embedding(query)

            # Search index
            results = await self.indexer.search(query_embedding, top_k=top_k)

            contexts = []
            for result in results:
                contexts.append(
                    RAGContext(
                        content=result.get("content", ""),
                        file_path=result.get("file_path", ""),
                        start_line=result.get("start_line", 0),
                        end_line=result.get("end_line", 0),
                        commit_sha=result.get("commit_sha"),
                        score=result.get("score", 0.0),
                    )
                )

            return contexts

        except Exception as e:
            print(f"RAG retrieval error: {e}")
            return []

    async def _get_query_embedding(self, query: str) -> List[float]:
        """Get embedding for query using available provider."""
        try:
            provider = await self.router.get_provider(TaskType.EMBEDDING)
            embeddings = provider.embeddings([query])
            return embeddings[0] if embeddings else []
        except Exception:
            # Fallback to simple keyword matching if embeddings fail
            return []

    def _rerank_contexts(
        self, contexts: List[RAGContext], query: str
    ) -> List[RAGContext]:
        """Rerank contexts based on relevance to query."""
        if not contexts:
            return []

        # Simple reranking based on keyword matches and recency
        query_lower = query.lower()

        for ctx in contexts:
            score = ctx.score  # Base score from vector search

            # Keyword matching bonus
            content_lower = ctx.content.lower()
            keywords = re.findall(r"\b\w+\b", query_lower)
            keyword_matches = sum(1 for keyword in keywords if keyword in content_lower)
            score += keyword_matches * 0.1

            # Function/class name matching bonus
            if any(word in ctx.content for word in ["def ", "class ", "function"]):
                score += 0.2

            ctx.score = score

        # Sort by score descending
        return sorted(contexts, key=lambda x: x.score, reverse=True)

    def _build_prompt(self, query: str, contexts: List[RAGContext]) -> str:
        """Build RAG prompt with retrieved contexts."""
        if not contexts:
            return f"User: {query}"

        # Build context sections
        context_sections = []
        for i, ctx in enumerate(contexts, 1):
            section = f"""CONTEXT {i}: file: {ctx.file_path}, lines {ctx.start_line}-{ctx.end_line}
---CODE---
{ctx.content}
---END---"""
            context_sections.append(section)

        additional_context = (
            "\n\n".join(context_sections[1:]) if len(context_sections) > 1 else ""
        )

        return self.SYSTEM_PROMPT.format(
            file_path=contexts[0].file_path if contexts else "unknown",
            start_line=contexts[0].start_line if contexts else 0,
            end_line=contexts[0].end_line if contexts else 0,
            content=contexts[0].content if contexts else "",
            additional_context=additional_context,
            query=query,
        )
