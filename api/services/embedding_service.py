"""
Embedding service for generating and managing semantic embeddings
"""

import os
import asyncio
from typing import List, Optional, Dict, Any
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from sqlalchemy.orm import selectinload

from ..storage.vector_models import (
    EmbeddingModel,
    ConversationSummaryModel,
    MemoryFactModel,
)
from ..storage.database import get_db
from ..providers.openai import OpenAIProvider


class EmbeddingService:
    """Service for generating and managing embeddings"""

    def __init__(self):
        self.client = OpenAIProvider(
            {
                "api_key_env": "OPENAI_API_KEY",
                "endpoint": os.getenv("OPENAI_BASE_URL", "https://api.openai.com"),
                "invoke_path": "/v1/embeddings",
            }
        )
        self.model = "text-embedding-3-small"
        self.dimension = 1536

    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        if not text or not text.strip():
            return []

        # Truncate text if too long (OpenAI has 8191 token limit)
        max_tokens = 8000
        if len(text) > max_tokens:
            text = text[:max_tokens]

        try:
            # Use the OpenAI provider's embed method
            embedding = await self.client.embed(texts=text, model=self.model)
            return embedding if isinstance(embedding, list) else []

        except Exception as e:
            print(f"Error generating embedding: {e}")
            return []

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts efficiently"""
        if not texts:
            return []

        # Filter out empty texts
        texts = [text for text in texts if text and text.strip()]
        if not texts:
            return []

        try:
            # Use the OpenAI provider's embed method for batching
            embeddings = await self.client.embed(texts=texts, model=self.model)
            return embeddings if isinstance(embeddings, list) else []

        except Exception as e:
            print(f"Error generating batch embeddings: {e}")
            # Fallback to sequential processing
            embeddings = []
            for text in texts:
                embedding = await self.embed_text(text)
                embeddings.append(embedding)
            return embeddings

    async def store_message_embedding(
        self,
        user_id: str,
        conversation_id: str,
        message_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Store embedding for a message"""
        try:
            embedding = await self.embed_text(content)
            if not embedding:
                return False

            async with get_db() as session:
                embedding_model = EmbeddingModel(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    source_type="message",
                    source_id=message_id,
                    embedding=embedding,
                    content=content,
                    metadata_=metadata or {},
                )
                session.add(embedding_model)
                await session.commit()
                return True

        except Exception as e:
            print(f"Error storing message embedding: {e}")
            return False

    async def store_conversation_summary(
        self, conversation_id: str, summary_text: str
    ) -> bool:
        """Store embedding for a conversation summary"""
        try:
            embedding = await self.embed_text(summary_text)
            if not embedding:
                return False

            async with get_db() as session:
                # Check if summary already exists
                existing = await session.execute(
                    text(
                        "SELECT id FROM conversation_summaries WHERE conversation_id = :conv_id"
                    ),
                    {"conv_id": conversation_id},
                )
                existing_summary = existing.fetchone()

                if existing_summary:
                    # Update existing summary
                    await session.execute(
                        text("""
                            UPDATE conversation_summaries 
                            SET summary_text = :summary, summary_embedding = :embedding, updated_at = NOW()
                            WHERE conversation_id = :conv_id
                        """),
                        {
                            "summary": summary_text,
                            "embedding": embedding,
                            "conv_id": conversation_id,
                        },
                    )
                else:
                    # Create new summary
                    summary_model = ConversationSummaryModel(
                        conversation_id=conversation_id,
                        summary_text=summary_text,
                        summary_embedding=embedding,
                    )
                    session.add(summary_model)

                await session.commit()
                return True

        except Exception as e:
            print(f"Error storing conversation summary: {e}")
            return False

    async def store_memory_fact(
        self,
        user_id: str,
        fact_text: str,
        category: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Store embedding for a memory fact"""
        try:
            embedding = await self.embed_text(fact_text)
            if not embedding:
                return False

            async with get_db() as session:
                fact_model = MemoryFactModel(
                    user_id=user_id,
                    fact_text=fact_text,
                    fact_embedding=embedding,
                    category=category,
                    metadata_=metadata or {},
                )
                session.add(fact_model)
                await session.commit()
                return True

        except Exception as e:
            print(f"Error storing memory fact: {e}")
            return False


class AsyncEmbeddingWorker:
    """Background worker for async embedding generation"""

    def __init__(self):
        self.service = EmbeddingService()
        self.queue = asyncio.Queue()
        self.running = False

    async def start(self):
        """Start the embedding worker"""
        self.running = True
        asyncio.create_task(self._worker_loop())

    async def stop(self):
        """Stop the embedding worker"""
        self.running = False

    async def _worker_loop(self):
        """Main worker loop"""
        while self.running:
            try:
                # Get next embedding task
                task = await self.queue.get()
                if task is None:
                    break

                # Process task
                await self._process_task(task)

            except Exception as e:
                print(f"Error in embedding worker: {e}")

    async def _process_task(self, task: Dict[str, Any]):
        """Process a single embedding task"""
        task_type = task.get("type")

        if task_type == "message":
            await self.service.store_message_embedding(
                user_id=task["user_id"],
                conversation_id=task["conversation_id"],
                message_id=task["message_id"],
                content=task["content"],
                metadata=task.get("metadata"),
            )
        elif task_type == "summary":
            await self.service.store_conversation_summary(
                conversation_id=task["conversation_id"],
                summary_text=task["summary_text"],
            )
        elif task_type == "memory":
            await self.service.store_memory_fact(
                user_id=task["user_id"],
                fact_text=task["fact_text"],
                category=task.get("category"),
                metadata=task.get("metadata"),
            )

    async def queue_message_embedding(
        self,
        user_id: str,
        conversation_id: str,
        message_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Queue a message embedding task"""
        await self.queue.put(
            {
                "type": "message",
                "user_id": user_id,
                "conversation_id": conversation_id,
                "message_id": message_id,
                "content": content,
                "metadata": metadata,
            }
        )

    async def queue_summary_embedding(self, conversation_id: str, summary_text: str):
        """Queue a conversation summary embedding task"""
        await self.queue.put(
            {
                "type": "summary",
                "conversation_id": conversation_id,
                "summary_text": summary_text,
            }
        )

    async def queue_memory_embedding(
        self,
        user_id: str,
        fact_text: str,
        category: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Queue a memory fact embedding task"""
        await self.queue.put(
            {
                "type": "memory",
                "user_id": user_id,
                "fact_text": fact_text,
                "category": category,
                "metadata": metadata,
            }
        )


# Global embedding worker instance
embedding_worker = AsyncEmbeddingWorker()
