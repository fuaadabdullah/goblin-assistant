"""
Async background worker for embedding generation.

Extracted from embedding_service.py to keep EmbeddingService focused on
synchronous embed/store operations. AsyncEmbeddingWorker queues tasks and
dispatches them to EmbeddingService without blocking the request path.
"""

import asyncio
from typing import Any, Dict, Optional


class AsyncEmbeddingWorker:
    """Background worker for async embedding generation"""

    def __init__(self):
        self.service = None
        self.queue = asyncio.Queue()
        self.running = False

    def _get_service(self):
        if self.service is None:
            # Lazy import to avoid circular dependency with embedding_service
            from .embedding_service import EmbeddingService

            self.service = EmbeddingService()
        return self.service

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
                task = await self.queue.get()
                if task is None:
                    break
                await self._process_task(task)
            except Exception as e:
                import logging

                logging.getLogger(__name__).error("Error in embedding worker: %s", e)

    async def _process_task(self, task: Dict[str, Any]):
        """Process a single embedding task"""
        task_type = task.get("type")
        service = self._get_service()

        if task_type == "message":
            await service.store_message_embedding(
                user_id=task["user_id"],
                conversation_id=task["conversation_id"],
                message_id=task["message_id"],
                content=task["content"],
                metadata=task.get("metadata"),
            )
        elif task_type == "summary":
            await service.store_conversation_summary(
                conversation_id=task["conversation_id"],
                summary_text=task["summary_text"],
            )
        elif task_type == "memory":
            await service.store_memory_fact(
                user_id=task["user_id"],
                fact_text=task["fact_text"],
                category=task.get("category"),
                metadata=task.get("metadata"),
            )
        elif task_type == "document":
            await service.store_document_embedding(
                user_id=task["user_id"],
                file_id=task["file_id"],
                chunk_id=task["chunk_id"],
                content=task["content"],
                metadata=task.get("metadata"),
            )
        elif task_type == "index":
            await service.store_index_item(
                user_id=task["user_id"],
                source_type=task["source_type"],
                source_id=task["source_id"],
                content=task["content"],
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

    async def queue_document_embedding(
        self,
        user_id: str,
        file_id: str,
        chunk_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Queue a document chunk embedding task."""
        await self.queue.put(
            {
                "type": "document",
                "user_id": user_id,
                "file_id": file_id,
                "chunk_id": chunk_id,
                "content": content,
                "metadata": metadata,
            }
        )

    async def queue_index_item(
        self,
        user_id: str,
        source_type: str,
        source_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Queue a generic index item for embedding.

        Use this for code, research, task, or any custom source_type.
        """
        await self.queue.put(
            {
                "type": "index",
                "user_id": user_id,
                "source_type": source_type,
                "source_id": source_id,
                "content": content,
                "metadata": metadata,
            }
        )


# Module-level singleton
embedding_worker = AsyncEmbeddingWorker()
